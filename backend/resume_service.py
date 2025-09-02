# resume_service.py
import os
import io
import uuid
import re
from typing import List, Tuple, Optional, Dict

from flask import Blueprint, request, jsonify, send_file
from dotenv import load_dotenv

# DB
from supabase import create_client, Client

# DOCX
from docx import Document
from docx.text.paragraph import Paragraph

# Similarity
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Optional embeddings (better ranking if available)
try:
    from sentence_transformers import SentenceTransformer
    _EMBED = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
except Exception:
    _EMBED = None

import requests

load_dotenv()
resume_bp = Blueprint("resume_bp", __name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

DOWNLOAD_DIR = os.path.join(os.getcwd(), "generated_resumes")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ----------------------------
# Utilities
# ----------------------------
BULLET_STYLES = {"List Paragraph", "List Bullet", "List Bullet 2", "List Bullet 3", "List Continue"}

def _is_bullet(p: Paragraph) -> bool:
    """Detect bullets by style, numbering, or literal bullet/dash prefix."""
    try:
        if p.style and p.style.name in BULLET_STYLES:
            return True
        # numbering/bullets via XML
        if p._p is not None and getattr(p._p, "pPr", None) is not None and getattr(p._p.pPr, "numPr", None) is not None:
            return True
    except Exception:
        pass
    # literal bullets/dashes (common after PDF conversions)
    txt = (p.text or "").lstrip()
    if txt.startswith(("•", "-", "–", "—")) and len(txt) > 2:
        return True
    return False

def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    # trim common suffix artifacts like "— on-site"
    s = re.sub(r"\s*[—-]\s*on-?site\s*$", "", s, flags=re.I)
    return s

def _shorten_to_words(s: str, max_words: int = 24) -> str:
    words = (s or "").split()
    return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")

def _delete_paragraph(p: Paragraph):
    p._element.getparent().remove(p._element)
    p._p = p._element = None

def _get_all_paragraph_text(doc: Document) -> List[str]:
    return [p.text for p in doc.paragraphs]

def _extract_bullets(doc: Document) -> List[Tuple[int, Paragraph]]:
    bullets: List[Tuple[int, Paragraph]] = []
    for idx, p in enumerate(doc.paragraphs):
        if _is_bullet(p):
            bullets.append((idx, p))
    return bullets

def _embed(texts: List[str]) -> np.ndarray:
    """Return embeddings (MiniLM if available; TF-IDF fallback is only used when both sides share the same vectorizer).
    IMPORTANT: Do not use TF-IDF embeddings for cross-set cosine unless fitted jointly."""
    if _EMBED:
        return np.array(_EMBED.encode(texts, normalize_embeddings=True))
    # If no SentenceTransformer, caller should avoid using this channel across different corpora.
    # We still return a TF-IDF embedding for same-corpus cosine, but cross-corpus is handled elsewhere.
    vec = TfidfVectorizer().fit(texts)
    mat = vec.transform(texts).astype(float).toarray()
    # L2 normalize
    mat = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
    return mat

def _cos_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a @ b.T

def _extract_keywords(text: str, topk: int = 30) -> List[str]:
    vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", max_features=2000)
    X = vec.fit_transform([text or ""])
    row = X.toarray()[0]
    terms = np.array(vec.get_feature_names_out())
    inds = np.argsort(-row)
    kws = [terms[i] for i in inds[:topk] if row[i] > 0]
    kws = [k for k in kws if 2 <= len(k) <= 30][:topk]
    return kws

def _rewrite_with_ollama(bullet: str, jd_text: str, allowed_terms: List[str]) -> str:
    system = (
        "You are rewriting resume bullets to better match a job description.\n"
        "Rules:\n"
        "- Do NOT invent experience or tools the candidate never used.\n"
        "- Only emphasize terms that appear in BOTH the candidate's resume and allowed_terms.\n"
        "- Keep one sentence, punchy, <= 24 words, action-oriented.\n"
        "- Keep the original meaning; just align phrasing to JD terminology.\n"
        "- No emojis, no fluff."
    )
    prompt = (
        f"Job description (excerpt):\n{jd_text[:1200]}\n\n"
        f"Allowed terms (safe to mention): {', '.join(sorted(set(allowed_terms)))}\n\n"
        f"Original bullet:\n\"{bullet}\"\n\n"
        "Rewrite now:"
    )
    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": f"System:\n{system}\n\nUser:\n{prompt}\n"},
            timeout=60,
        )
        r.raise_for_status()
        out = (r.json() or {}).get("response", "").strip()
        out = out.replace("\n", " ")
        return _shorten_to_words(_clean(out), 24) or bullet
    except Exception:
        # fallback: just return a shortened original
        return _shorten_to_words(bullet, 24)

def _rewrite_no_llm(bullet: str, jd_text: str, resume_terms: List[str]) -> str:
    jd_kws = set(_extract_keywords(jd_text, topk=25))
    res_kws = set(_extract_keywords(" ".join(resume_terms), topk=25))
    overlap = [k for k in jd_kws if k in res_kws and len(k) > 2]
    candidate = bullet
    if overlap:
        add = [k for k in overlap if k.lower() not in candidate.lower()][:2]
        if add:
            candidate = re.sub(r"[.;:,\s]+$", "", candidate) + f" using {', '.join(add)}."
    return _shorten_to_words(_clean(candidate), 24)

def _collect_resume_terms(doc: Document) -> List[str]:
    # super-light skills collector: grab tokens across resume
    text = " ".join(_get_all_paragraph_text(doc))
    terms = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{1,32}", text)
    return terms[:300]

def _fit_to_one_page(doc: Document, keep_order: bool = True, max_bullets: int = 18):
    """Heuristic page fit: cap total bullet count, removing lowest relevance first."""
    bullets = _extract_bullets(doc)
    if len(bullets) <= max_bullets:
        return
    bullets_sorted = sorted(bullets, key=lambda t: getattr(t[1], "_relevance", 0.0), reverse=True)
    to_keep = set(idx for idx, _ in bullets_sorted[:max_bullets])
    for idx, p in bullets:
        if idx not in to_keep:
            _delete_paragraph(p)

def _sentences(text: str) -> List[str]:
    # Coarse sentence split: terminals, newlines, semicolons
    raw = re.split(r'(?<=[.!?])\s+|\n{1,}|\s*;\s*', text or "")
    sents = [_clean(s) for s in raw if 5 <= len(s.split()) <= 60]
    if not sents:
        sents = [_clean(s) for s in raw if _clean(s)]
    return sents[:120]  # cap for speed

def _scale_01(arr: np.ndarray) -> np.ndarray:
    if arr.size == 0:
        return arr
    lo = float(np.percentile(arr, 10))
    hi = float(np.percentile(arr, 90))
    if hi <= lo + 1e-8:
        return np.clip((arr - lo), 0, 1)  # all same → zeros
    return np.clip((arr - lo) / (hi - lo), 0, 1)

def _semantic_maxsim_per_bullet(bullets: List[str], jd_text: str) -> np.ndarray:
    """Max cosine similarity per bullet vs JD sentences using SentenceTransformer if available.
    If ST is not available, return zeros and let the lexical channel handle it."""
    jd_sents = _sentences(jd_text)
    if not jd_sents or not bullets:
        return np.zeros(len(bullets), dtype=float)
    if _EMBED is None:
        # Without a shared embedding space, skip semantic channel
        return np.zeros(len(bullets), dtype=float)
    em_bul = _embed(bullets)
    em_jd = _embed(jd_sents)
    sims = _cos_sim(em_bul, em_jd)
    return sims.max(axis=1) if sims.size else np.zeros(len(bullets), dtype=float)

def _lexical_maxsim_per_bullet(bullets: List[str], jd_text: str) -> np.ndarray:
    """TF-IDF (1,2-gram) cosine vs JD sentences; take max per bullet."""
    jd_sents = _sentences(jd_text)
    if not jd_sents or not bullets:
        return np.zeros(len(bullets), dtype=float)
    corpus = bullets + jd_sents
    vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", min_df=1)
    X = vec.fit_transform(corpus)  # l2-normalized rows by default
    B = X[:len(bullets), :]
    J = X[len(bullets):, :]
    sims = (B @ J.T).toarray()  # cosine for l2-normalized tfidf
    return sims.max(axis=1) if sims.size else np.zeros(len(bullets), dtype=float)

def _hybrid_scores(bullets: List[str], jd_text: str, w_sem: float = 0.7) -> Tuple[np.ndarray, Dict]:
    """Blend semantic and lexical max-sim (both scaled 0–1)."""
    sem = _semantic_maxsim_per_bullet(bullets, jd_text)  # 0..1 (zeros if no ST)
    lex = _lexical_maxsim_per_bullet(bullets, jd_text)   # ~0..1
    sem_n = _scale_01(sem)
    lex_n = _scale_01(lex)
    combo = w_sem * sem_n + (1.0 - w_sem) * lex_n
    meta = {
        "semantic_backend": "sentence-transformers" if _EMBED else "lexical-only",
        "semantic_raw_min": float(sem.min()) if sem.size else 0.0,
        "semantic_raw_max": float(sem.max()) if sem.size else 0.0,
    }
    return combo, meta

# ----------------------------
# Core route
# ----------------------------
@resume_bp.route("/api/resume/tune", methods=["POST"])
def tune_resume():
    """
    Multipart form:
      - file: .docx
      - user_id: UUID
      - job_id: (optional) user_jobs.id
      - job_url: (optional) application_link to find row
      - jd_text: (optional) raw JD text, if you don’t want DB lookup
      - use_llm: "true"/"false"  (defaults false)
    Returns: { success, download_url, changed_bullets[], removed_bullets[], scoring_backend }
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No resume file uploaded"}), 400

    f = request.files["file"]
    if not f.filename.lower().endswith(".docx"):
        return jsonify({"success": False, "error": "Please upload a .docx file"}), 400

    user_id = request.form.get("user_id", "")
    job_id = request.form.get("job_id")
    job_url = request.form.get("job_url")
    jd_text = request.form.get("jd_text", "")
    use_llm = (request.form.get("use_llm", "false").lower() == "true")

    # Load job description from DB if not provided
    if not jd_text:
        if not supabase:
            return jsonify({"success": False, "error": "DB not available and no jd_text provided"}), 500
        q = supabase.table("user_jobs").select("id, description, job_name, company, application_link")
        if job_id:
            q = q.eq("id", job_id)
        elif job_url:
            q = q.eq("application_link", job_url)
        else:
            return jsonify({"success": False, "error": "Provide job_id, job_url or jd_text"}), 400
        row = q.limit(1).execute()
        if not row.data:
            return jsonify({"success": False, "error": "Job not found in DB or no description saved"}), 404
        jd_text = row.data[0].get("description") or ""

    jd_text = _clean(jd_text)
    if not jd_text:
        return jsonify({"success": False, "error": "Empty job description"}), 400

    # Load doc
    resume_bytes = io.BytesIO(f.read())
    doc = Document(resume_bytes)

    # Collect bullets & score relevance
    bullets = _extract_bullets(doc)
    if not bullets:
        return jsonify({"success": False, "error": "No bullets detected in resume"}), 400

    bullet_texts = [_clean(p.text) for _, p in bullets]

    # Hybrid (semantic + lexical) max similarity vs JD sentences → 0..1
    scores01, debug_meta = _hybrid_scores(bullet_texts, jd_text, w_sem=0.7)

    # Store relevance (0..1) on Paragraphs for pruning & UI
    for (idx, p), s in zip(bullets, scores01):
        setattr(p, "_relevance", float(s))

    resume_terms = _collect_resume_terms(doc)
    changed: List[Dict] = []
    removed: List[int] = []

    # LLM rewrite policy: top 75% by relevance get rewritten (if use_llm), others get shortened/keyword-aligned
    TOP_REWRITE_FRAC = 0.75
    cut = np.percentile(scores01, 100 * (1 - TOP_REWRITE_FRAC)) if len(scores01) else 0.0

    for (idx, p), score01 in zip(bullets, scores01):
        before = _clean(p.text)
        if not before:
            continue

        if use_llm and score01 >= cut:
            candidate = _rewrite_with_ollama(before, jd_text, resume_terms)
        else:
            candidate = _rewrite_no_llm(before, jd_text, resume_terms)

        candidate = _shorten_to_words(candidate, 24)

        if candidate != before:
            p.text = candidate
            changed.append({
                "index": idx,
                "before": before,
                "after": candidate,
                "relevance": int(round(100 * float(score01)))  # 0..100 for UI
            })
        else:
            # still enforce brevity
            short = _shorten_to_words(before, 24)
            if short != before:
                p.text = short
                changed.append({
                    "index": idx,
                    "before": before,
                    "after": short,
                    "relevance": int(round(100 * float(score01)))
                })

    # Prune to one pager by capping total bullets (lowest relevance go first)
    _fit_to_one_page(doc, max_bullets=18)

    # Collect removed bullets (those that no longer exist)
    existing_idxs = {i for i, _ in _extract_bullets(doc)}
    for idx, p in bullets:
        if (getattr(p, "_p", None) is None) or (idx not in existing_idxs):
            removed.append(idx)

    # Save tailored file
    out_id = str(uuid.uuid4())[:8]
    out_name = f"tailored-{out_id}.docx"
    out_path = os.path.join(DOWNLOAD_DIR, out_name)
    doc.save(out_path)

    return jsonify({
        "success": True,
        "download_url": f"/api/resume/download/{out_name}",
        "changed_bullets": changed,
        "removed_bullets": removed,
        "scoring_backend": debug_meta.get("semantic_backend", "lexical-only")
    })

@resume_bp.route("/api/resume/download/<fname>", methods=["GET"])
def download(fname: str):
    path = os.path.join(DOWNLOAD_DIR, fname)
    if not os.path.exists(path):
        return jsonify({"success": False, "error": "Not found"}), 404
    return send_file(
        path,
        as_attachment=True,
        download_name=fname,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
