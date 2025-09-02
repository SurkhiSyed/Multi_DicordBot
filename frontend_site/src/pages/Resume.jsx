// src/pages/Resume.jsx
import React, { useEffect, useState } from "react";
import supabase from "../helper/supabaseClient";

const Sparkles = (props) => (
  <svg viewBox="0 0 24 24" className={props.className || "w-4 h-4"}>
    <path fill="currentColor" d="M5 3l1.5 3L10 7.5 6.5 9 5 12 3.5 9 0 7.5 3.5 6 5 3zm14 2l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2zM9 14l2 4 4 2-4 2-2 4-2-4-4-2 4-2 2-4z"/>
  </svg>
);

export default function Resume() {
  const [user, setUser] = useState(null);
  const [userJobs, setUserJobs] = useState([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);

  const [resumeFile, setResumeFile] = useState(null);
  const [useLLM, setUseLLM] = useState(false);
  const [isTuning, setIsTuning] = useState(false);

  const [result, setResult] = useState(null); // { download_url, changed_bullets, removed_bullets }
  const [activeJob, setActiveJob] = useState(null);

  useEffect(() => {
    const init = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) setUser(session.user);
    };
    init();
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, s) => {
      setUser(s?.user || null);
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!user?.id) return;
    (async () => {
      setIsLoadingJobs(true);
      try {
        const res = await fetch(`http://localhost:8000/api/user-jobs/${user.id}?page=1&limit=100`);
        const data = await res.json();
        if (data.success) setUserJobs(data.jobs || []);
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoadingJobs(false);
      }
    })();
  }, [user]);

  const handleTune = async (job) => {
    if (!resumeFile) {
      alert("Upload your master resume (.docx) first.");
      return;
    }
    setActiveJob(job);
    setResult(null);
    setIsTuning(true);

    try {
      const fd = new FormData();
      fd.append("file", resumeFile);
      fd.append("user_id", user.id);
      fd.append("job_id", job.id);
      fd.append("use_llm", useLLM ? "true" : "false");

      const r = await fetch("http://localhost:8000/api/resume/tune", {
        method: "POST",
        body: fd,
      });
      const data = await r.json();
      if (data.success) {
        setResult(data);
      } else {
        alert(data.error || "Failed to tune resume");
      }
    } catch (e) {
      console.error(e);
      alert("Error tuning resume");
    } finally {
      setIsTuning(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Resume Tuner ✨</h1>
            <p className="text-gray-600">Keep your format, tailor your bullets to the selected job.</p>
          </div>
          {user && (
            <div className="text-sm text-gray-600">
              {user.email} • <span className="text-gray-400">ID {user.id.slice(0,8)}…</span>
            </div>
          )}
        </header>

        <section className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="font-semibold">1) Upload your master resume (.docx)</h2>
          <input
            type="file"
            accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
            className="block w-full"
          />
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={useLLM}
              onChange={(e) => setUseLLM(e.target.checked)}
            />
            <span className="inline-flex items-center gap-1">
              <Sparkles /> Use local LLM via Ollama (optional)
            </span>
          </label>
          {!useLLM && (
            <p className="text-xs text-gray-500">
              No-LLM mode will still tailor bullets by weaving overlapping keywords and shortening long lines.
            </p>
          )}
        </section>

        <section className="bg-white border rounded-lg">
          <div className="p-5 flex items-center justify-between">
            <h2 className="font-semibold">2) Choose a saved job</h2>
            <div className="text-sm text-gray-500">{userJobs.length} jobs</div>
          </div>
          <div className="max-h-96 overflow-auto divide-y">
            {isLoadingJobs ? (
              <div className="p-5 text-gray-500">Loading your jobs…</div>
            ) : userJobs.length === 0 ? (
              <div className="p-5 text-gray-500">No saved jobs yet.</div>
            ) : userJobs.map(job => (
              <div key={job.id} className="p-5 flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium">{job.job_name}</div>
                  <div className="text-sm text-gray-600">{job.company}</div>
                  <div className="text-xs text-gray-500">{job.location} • {job.source}</div>
                </div>
                <button
                  onClick={() => handleTune(job)}
                  disabled={isTuning}
                  className="px-3 py-2 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {isTuning && activeJob?.id === job.id ? "Tuning…" : "Tune resume for this job"}
                </button>
              </div>
            ))}
          </div>
        </section>

        {result && (
          <section className="bg-white border rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">3) Review & Download</h2>
              <a
                href={`http://localhost:8000${result.download_url}`}
                className="px-3 py-2 rounded-md bg-green-600 text-white text-sm hover:bg-green-700"
              >
                Download tailored .docx
              </a>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <h3 className="text-sm font-semibold mb-2">Changed bullets ({result.changed_bullets.length})</h3>
                <div className="space-y-3">
                  {result.changed_bullets.map((c, i) => (
                    <div key={i} className="text-sm bg-green-50 border border-green-200 rounded p-3">
                      <div className="text-[11px] text-green-700 mb-1">relevance: {c.relevance}</div>
                      <div className="line-through text-gray-500">{c.before}</div>
                      <div className="font-medium mt-1">{c.after}</div>
                    </div>
                  ))}
                  {result.changed_bullets.length === 0 && <div className="text-gray-500 text-sm">No textual changes.</div>}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold mb-2">Removed (to fit one page)</h3>
                <div className="text-sm text-gray-600">
                  {result.removed_bullets.length > 0
                    ? `Removed ${result.removed_bullets.length} low-relevance bullets.`
                    : "No bullets removed."}
                </div>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
