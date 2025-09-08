from flask import Flask, jsonify, request
from flask_cors import CORS
from rag.rag_model import run_rag
import os
import asyncio
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from jobs.main_nodriver import NoDriverLinkedInScraper
from supabase import create_client, Client
import sys
from dotenv import load_dotenv
import uuid
# app.py (top)
from flask import send_from_directory
from werkzeug.utils import secure_filename
from resume_service import resume_bp


# Load environment variables
load_dotenv()

app = Flask(__name__)

#FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "https://applicationhelper.onrender.com")

# CORS: match exact origins (no trailing slash)
CORS(app,
     resources={r"/api/*": {"origins": [FRONTEND_ORIGIN, "http://localhost:3000", "http://localhost:5173"]}},
     supports_credentials=True)

# Health + root ping (Render health check)
@app.route("/", methods=["GET"])
def root():
    return "OK", 200

@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200

# Optional: debug your env quickly
@app.route("/api/debug/env", methods=["GET"])
def debug():
    return jsonify({
        "python": sys.version,
        "port": os.getenv("PORT"),
        "supabase_url_set": bool(os.getenv("SUPABASE_URL")),
        "has_service_key": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "frontend_origin": FRONTEND_ORIGIN,
    }), 200



CHROMA_PATH = os.path.join(os.path.dirname(__file__), "rag", "chroma")
app.register_blueprint(resume_bp)

# Initialize Supabase client with Service Role Key (bypasses RLS)
supabase_url = os.getenv("SUPABASE_URL")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use service role key
supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")  # Keep for fallback

ALLOWED_EXT = {'.docx', '.pdf'}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


if not supabase_url:
    print("⚠️ Warning: SUPABASE_URL not found in environment variables")
    supabase: Client = None
elif supabase_service_key:
    try:
        # Use service role key for backend operations (bypasses RLS)
        supabase: Client = create_client(supabase_url, supabase_service_key)
        print("✅ Supabase client initialized with Service Role Key (RLS bypassed)")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client with service key: {e}")
        supabase = None
elif supabase_anon_key:
    try:
        # Fallback to anon key (will have RLS issues)
        supabase: Client = create_client(supabase_url, supabase_anon_key)
        print("⚠️ Supabase client initialized with Anon Key (RLS may block operations)")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client: {e}")
        supabase = None
else:
    print("❌ No Supabase keys found in environment variables")
    supabase = None

def get_existing_job_links(user_id: str) -> set:
    """Get all existing job application links for a user"""
    if not supabase or not user_id:
        return set()
    
    try:
        result = supabase.table("user_jobs").select("application_link").eq("user_id", user_id).execute()
        existing_links = {job['application_link'] for job in result.data if job.get('application_link')}
        print(f"📋 Found {len(existing_links)} existing job links for user")
        return existing_links
    except Exception as e:
        print(f"❌ Error fetching existing job links: {e}")
        return set()

def save_jobs_to_supabase(user_id: str, jobs_data: list, source: str = 'linkedin'):
    """
    Save jobs to Supabase database, avoiding duplicates
    """
    if not supabase:
        print("⚠️ Supabase client not available, skipping database save")
        return {"saved": 0, "duplicates": 0, "errors": 0}
    
    if not user_id:
        print("❌ No user_id provided, cannot save jobs")
        return {"saved": 0, "duplicates": 0, "errors": 0}
    
    saved_count = 0
    duplicate_count = 0
    error_count = 0
    
    print(f"💾 Attempting to save {len(jobs_data)} jobs to Supabase for user {user_id[:8]}...")
    
    # Get existing job links to avoid duplicates
    existing_links = get_existing_job_links(user_id)
    
    for job in jobs_data:
        try:
            application_link = job.get("application_link", "")
            
            # Check if job already exists
            if application_link in existing_links:
                print(f"🔄 Job already exists: {job.get('name', 'Unknown')} at {job.get('company', 'Unknown')}")
                duplicate_count += 1
                continue
            
            # Prepare job data for database
            job_record = {
                "user_id": user_id,
                "job_name": job.get("name", "")[:500],  # Truncate to match VARCHAR(500)
                "company": job.get("company", "")[:200],  # Truncate to match VARCHAR(200)
                "location": job.get("location", "")[:200] if job.get("location") else None,
                "location_type": job.get("location_type", "")[:50] if job.get("location_type") else None,
                "job_type": job.get("job_type", "")[:100] if job.get("job_type") else None,
                "posting_date": job.get("posting_date", "")[:100] if job.get("posting_date") else None,
                "application_link": application_link,
                "description": job.get("description", "") if job.get("description") else None,
                "source": source
            }
            
            # Insert the job
            result = supabase.table("user_jobs").insert(job_record).execute()
            
            if result.data:
                print(f"✅ Saved job: {job_record['job_name']} at {job_record['company']}")
                saved_count += 1
                # Add to existing links set to prevent duplicates in the same batch
                existing_links.add(application_link)
            else:
                print(f"❌ Failed to save job: {job_record['job_name']} at {job_record['company']}")
                error_count += 1
                
        except Exception as e:
            print(f"❌ Error saving job '{job.get('name', 'Unknown')}': {str(e)}")
            error_count += 1
            continue
    
    print(f"📊 Database save summary: {saved_count} saved, {duplicate_count} duplicates, {error_count} errors")
    
    return {
        "saved": saved_count,
        "duplicates": duplicate_count,
        "errors": error_count
    }

# Add explicit OPTIONS handler for /api/jobs
@app.route('/api/jobs', methods=['OPTIONS'])
def handle_jobs_options():
    """Handle preflight OPTIONS request for /api/jobs"""
    response = jsonify({})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
    return response

@app.route('/api/echo', methods=['POST'])
def echo():
    data = request.json
    message = data.get('message', '')
    return jsonify({'response': f'Python says: {message}'})

@app.route('/api/rag', methods=['POST'])
def rag():
    data = request.json
    message = data.get('message', '')
    print(f"RAG endpoint called with: {message}")
    result = run_rag(message)
    print(f"RAG result: {result}")
    return jsonify(result)

'''
@app.route('/api/debug', methods=['GET'])
def debug():
    print("CWD:", os.getcwd())
    print("CHROMA_PATH:", CHROMA_PATH)
    print("GOOGLE_API_KEY:", os.getenv("GOOGLE_API_KEY"))
    return jsonify({
        "cwd": os.getcwd(),
        "chroma_path": CHROMA_PATH,
        "google_api_key": os.getenv("GOOGLE_API_KEY")
    })
'''

async def scrape_linkedin_jobs_async(linkedin_username: str, linkedin_password: str, num_jobs: int = 56, search_title: str = "intern", location: str = "", user_id: str = None):
    """Async wrapper for the LinkedIn scraper with smart duplicate detection"""
    scraper = NoDriverLinkedInScraper()
    jobs_data = []  # Initialize outside try block
    
    try:
        # Setup browser
        await scraper.setup_browser()
        
        # Login to LinkedIn
        login_success = await scraper.login_to_linkedin(linkedin_username, linkedin_password)
        
        if not login_success:
            return {"success": False, "error": "Failed to login to LinkedIn", "jobs": []}
        
        # Calculate initial max_pages based on num_jobs (7 jobs per page)
        initial_max_pages = max(1, (num_jobs + 6) // 7)  # Round up division
        
        # Get existing job links to check for duplicates
        existing_links = get_existing_job_links(user_id) if user_id else set()
        
        max_pages = initial_max_pages
        total_new_jobs = 0
        page_attempts = 0
        max_attempts = initial_max_pages * 3  # Don't search forever
        
        print(f"🎯 Target: {num_jobs} jobs, Initial pages: {initial_max_pages}, Existing jobs: {len(existing_links)}")
        
        while total_new_jobs < num_jobs and page_attempts < max_attempts:
            print(f"🔍 Scraping attempt with {max_pages} pages (attempt {page_attempts + 1})")
            
            # Clear previous jobs for this attempt
            scraper.jobs = []
            
            # Scrape jobs with location support
            jobs = await scraper.scrape_jobs(keywords=search_title, location=location, max_pages=max_pages)
            
            # Count new jobs (not in existing database)
            new_jobs = []
            duplicate_count = 0
            
            for job in jobs:
                job_dict = job.model_dump()
                application_link = job_dict.get("application_link", "")
                
                if application_link not in existing_links:
                    new_jobs.append(job_dict)
                    existing_links.add(application_link)  # Add to set to prevent duplicates in same batch
                else:
                    duplicate_count += 1
            
            total_new_jobs = len(new_jobs)
            
            print(f"📊 Found {len(jobs)} total jobs, {total_new_jobs} new jobs, {duplicate_count} duplicates")
            
            # If we have enough new jobs, we're done
            if total_new_jobs >= num_jobs:
                jobs_data = new_jobs[:num_jobs]  # Take only the requested number
                break
            
            # If we found mostly duplicates and not enough new jobs, increase search scope
            duplicate_ratio = duplicate_count / max(len(jobs), 1)
            
            if duplicate_ratio > 0.7 and total_new_jobs < num_jobs * 0.5:  # More than 70% duplicates
                max_pages = min(max_pages + 3, 20)  # Increase pages but cap at 20
                print(f"🔄 High duplicate ratio ({duplicate_ratio:.1%}), increasing search to {max_pages} pages")
            else:
                # Not enough jobs found, but not due to duplicates
                jobs_data = new_jobs
                break
            
            page_attempts += 1
        
        if not jobs_data:
            jobs_data = []
        
        print(f"✅ Successfully scraped {len(jobs_data)} new jobs after {page_attempts + 1} attempts")
        
    except Exception as e:
        print(f"❌ Error during scraping: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up browser (this might fail, but we still want to return any jobs we got)
        try:
            await scraper.close()
        except Exception as cleanup_error:
            print(f"⚠️ Browser cleanup failed (ignoring): {cleanup_error}")
    
    # Always return the jobs we managed to scrape, even if cleanup failed
    if jobs_data:
        return {
            "success": True,
            "message": f"Successfully scraped {len(jobs_data)} new jobs",
            "total_jobs": len(jobs_data),
            "jobs": jobs_data
        }
    else:
        return {
            "success": False,
            "error": "No new jobs were found",
            "jobs": []
        }

@app.route('/api/jobs', methods=['POST'])
def get_jobs():
    try:
        print(f"🔍 /api/jobs POST endpoint called")
        
        data = request.json
        if not data:
            print("❌ No JSON data received")
            return jsonify({
                "success": False,
                "error": "No data received",
                "jobs": []
            }), 400
        
        linkedin_username = data.get('linkedin_username', '')
        linkedin_password = data.get('linkedin_password', '')
        num_jobs = data.get('num_jobs', 56)  # Default to 56 jobs (8 pages)
        search_title = data.get('searchTitle', 'intern')  # Get search title from frontend
        location = data.get('location', '')  # Get location from frontend
        user_id = data.get('user_id', '')  # Get user_id from request

        print(f"📝 Request data: username={linkedin_username}, num_jobs={num_jobs}, search_title={search_title}, location={location}, user_id={user_id[:8] if user_id else 'None'}...")

        # Validate inputs
        if not linkedin_username or not linkedin_password:
            print("❌ Missing LinkedIn credentials")
            return jsonify({
                "success": False,
                "error": "LinkedIn username and password are required",
                "jobs": []
            }), 400
        
        if not user_id:
            print("❌ Missing user_id")
            return jsonify({
                "success": False,
                "error": "user_id is required for saving jobs to database",
                "jobs": []
            }), 400
        
        # Validate user_id format (should be UUID)
        try:
            uuid.UUID(user_id)
        except ValueError:
            print(f"❌ Invalid user_id format: {user_id}")
            return jsonify({
                "success": False,
                "error": "user_id must be a valid UUID",
                "jobs": []
            }), 400
        
        # Validate num_jobs
        try:
            num_jobs = int(num_jobs)
            if num_jobs <= 0:
                num_jobs = 7  # Default to 1 page
            elif num_jobs > 140:  # Reasonable upper limit (20 pages)
                num_jobs = 140
        except (ValueError, TypeError):
            num_jobs = 56  # Default value
        
        print(f"🔍 Starting scraping: {num_jobs} jobs for '{search_title}' in '{location or 'Any location'}' for user: {user_id[:8]}...")
        
        # Run the async scraper with all parameters
        scraper_result = asyncio.run(scrape_linkedin_jobs_async(
            linkedin_username=linkedin_username, 
            linkedin_password=linkedin_password, 
            num_jobs=num_jobs,
            search_title=search_title,
            location=location,
            user_id=user_id
        ))
        
        if not scraper_result.get("success"):
            print(f"❌ Scraper failed: {scraper_result.get('error', 'Unknown error')}")
            return jsonify(scraper_result), 500
        
        jobs_data = scraper_result.get("jobs", [])
        print(f"✅ Scraper returned {len(jobs_data)} jobs")
        
        # Save jobs to Supabase database
        db_result = save_jobs_to_supabase(user_id, jobs_data, source='linkedin')
        
        # Prepare response with both scraping and database results
        response = {
            "success": True,
            "message": f"Successfully scraped {len(jobs_data)} new jobs",
            "total_jobs": len(jobs_data),
            "jobs": jobs_data,
            "database": {
                "saved": db_result["saved"],
                "duplicates": db_result["duplicates"],
                "errors": db_result["errors"],
                "message": f"Saved {db_result['saved']} new jobs, {db_result['duplicates']} were duplicates"
            }
        }
        
        print(f"✅ Returning successful response with {len(jobs_data)} jobs")
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error in /api/jobs endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "jobs": []
        }), 500

@app.route('/api/user-jobs/<user_id>/status', methods=['PUT'])
def update_job_status(user_id):
    """Update the application status of a specific job"""
    try:
        print(f"🔄 /api/user-jobs/{user_id[:8]}/status endpoint called")
        
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received"
            }), 400
        
        job_id = data.get('job_id')
        new_status = data.get('status')
        
        if not job_id or not new_status:
            return jsonify({
                "success": False,
                "error": "job_id and status are required"
            }), 400
        
        # Validate status
        valid_statuses = ['not_applied', 'applied', 'rejected', 'interview', 'offer']
        if new_status not in valid_statuses:
            return jsonify({
                "success": False,
                "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }), 400
        
        if not supabase:
            return jsonify({
                "success": False,
                "error": "Database not available"
            }), 500
        
        # Update the job status
        result = supabase.table("user_jobs").update({
            "application_status": new_status,
            "status_updated_at": "now()"
        }).eq("id", job_id).eq("user_id", user_id).execute()
        
        if result.data:
            print(f"✅ Updated job {job_id} status to {new_status}")
            return jsonify({
                "success": True,
                "message": f"Job status updated to {new_status}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to update job status"
            }), 500
        
    except Exception as e:
        print(f"❌ Error updating job status: {e}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/api/user-jobs/<user_id>', methods=['GET'])
def get_user_jobs(user_id):
    """Get all jobs for a specific user from the database"""
    try:
        print(f"📚 /api/user-jobs endpoint called for user: {user_id[:8]}...")
        
        if not supabase:
            print("❌ Supabase client not available")
            return jsonify({
                "success": False,
                "error": "Database not available",
                "jobs": []
            }), 500
        
        # Validate user_id format
        try:
            uuid.UUID(user_id)
        except ValueError:
            print(f"❌ Invalid user_id format: {user_id}")
            return jsonify({
                "success": False,
                "error": "Invalid user_id format",
                "jobs": []
            }), 400
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 100))  # Increased default limit
        offset = (page - 1) * limit
        
        # Get jobs from database
        result = supabase.table("user_jobs").select("*").eq("user_id", user_id).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        # Get total count
        count_result = supabase.table("user_jobs").select("id", count="exact").eq("user_id", user_id).execute()
        total_jobs = count_result.count
        
        print(f"✅ Found {len(result.data)} jobs for user (page {page}, total: {total_jobs})")
        
        return jsonify({
            "success": True,
            "jobs": result.data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_jobs,
                "total_pages": (total_jobs + limit - 1) // limit
            }
        })
        
    except Exception as e:
        print(f"❌ Error in /api/user-jobs endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "jobs": []
        }), 500

# app.py

@app.route('/api/resume/tailor', methods=['POST'])
def resume_tailor():
    try:
      if 'resume' not in request.files:
          return jsonify({"success": False, "error": "No resume file provided"}), 400

      resume = request.files['resume']
      user_id = request.form.get('user_id', '')
      job_id = request.form.get('job_id', '')
      # mode = request.form.get('mode', 'auto')  # reserved if you want to override LLM/lite

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


@app.route('/api/resume/download/<path:fname>', methods=['GET'])
def resume_download(fname):
    try:
        return send_from_directory(SAFE_OUTPUT_DIR, fname, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "error": "File not found"}), 404


if __name__ == '__main__':
    port = int(os.getenv('PORT', '8000'))  # Render sets PORT
    # turn off debug in prod
    app.run(host='0.0.0.0', port=port, debug=False)
