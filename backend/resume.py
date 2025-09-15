import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from app import supabase, ALLOWED_EXT, UPLOAD_DIR  # Import shared variables
from resume_service import process_resume  # Assuming process_resume is in resume_service.py

# Create a Blueprint for resume-related routes
resume_bp = Blueprint("resume_bp", __name__)

@resume_bp.route('/api/resume/tailor', methods=['POST'])
def resume_tailor():
    try:
        if 'resume' not in request.files:
            return jsonify({"success": False, "error": "No resume file provided"}), 400

        resume = request.files['resume']
        user_id = request.form.get('user_id', '')
        job_id = request.form.get('job_id', '')

        if not user_id or not job_id:
            return jsonify({"success": False, "error": "user_id and job_id are required"}), 400

        # Validate user_id
        try:
            uuid.UUID(user_id)
        except ValueError:
            return jsonify({"success": False, "error": "Invalid user_id"}), 400

        # Get job description from DB (and ensure it belongs to this user)
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        job_q = supabase.table("user_jobs").select("*").eq("id", job_id).eq("user_id", user_id).limit(1).execute()
        if not job_q.data:
            return jsonify({"success": False, "error": "Job not found for this user"}), 404

        job = job_q.data[0]
        job_text = job.get("description") or ""

        # Save upload
        fname = secure_filename(resume.filename or f"resume-{uuid.uuid4().hex}.docx")
        ext = os.path.splitext(fname)[1].lower()
        if ext not in ALLOWED_EXT:
            return jsonify({"success": False, "error": "Only .docx or .pdf files are supported"}), 400

        upload_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
        resume.save(upload_path)

        # Process
        out_path, summary = process_resume(upload_path, job_text)

        # We return a JSON with a download url + change summary
        dl_name = os.path.basename(out_path)
        return jsonify({
            "success": True,
            "download_url": f"/api/resume/download/{dl_name}",
            "change_summary": summary
        })
    except Exception as e:
        print("❌ resume_tailor error:", e)
        return jsonify({"success": False, "error": f"{e}"}), 500


@resume_bp.route('/api/resume/download/<path:fname>', methods=['GET'])
def resume_download(fname):
    try:
        return send_from_directory(UPLOAD_DIR, fname, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "error": "File not found"}), 404