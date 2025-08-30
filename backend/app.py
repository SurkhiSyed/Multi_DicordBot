from flask import Flask, jsonify, request
from rag.rag_model import run_rag
import os
import asyncio
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from jobs.main_nodriver import NoDriverLinkedInScraper

app = Flask(__name__)

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "rag", "chroma")

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

async def scrape_linkedin_jobs_async(linkedin_username: str, linkedin_password: str, num_jobs: int = 56):
    """Async wrapper for the LinkedIn scraper"""
    scraper = NoDriverLinkedInScraper()
    jobs_data = []  # Initialize outside try block
    
    try:
        # Setup browser
        await scraper.setup_browser()
        
        # Login to LinkedIn
        login_success = await scraper.login_to_linkedin(linkedin_username, linkedin_password)
        
        if not login_success:
            return {"success": False, "error": "Failed to login to LinkedIn", "jobs": []}
        
        # Calculate max_pages based on num_jobs (7 jobs per page)
        max_pages = max(1, (num_jobs + 6) // 7)  # Round up division
        
        # Scrape jobs
        jobs = await scraper.scrape_jobs(keywords="intern", max_pages=max_pages)
        
        # Convert jobs to dict format for JSON response
        for job in jobs:
            job_dict = job.model_dump()
            jobs_data.append(job_dict)
        
        print(f"✅ Successfully scraped {len(jobs_data)} jobs before cleanup")
        
    except Exception as e:
        print(f"❌ Error during scraping: {str(e)}")
        # Don't return here - we want to try cleanup and return whatever we got
        
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
            "message": f"Successfully scraped {len(jobs_data)} jobs",
            "total_jobs": len(jobs_data),
            "jobs": jobs_data
        }
    else:
        return {
            "success": False,
            "error": "No jobs were scraped",
            "jobs": []
        }

@app.route('/api/jobs', methods=['POST'])
def get_jobs():
    try:
        data = request.json
        linkedin_username = data.get('linkedin_username', '')
        linkedin_password = data.get('linkedin_password', '')
        num_jobs = data.get('num_jobs', 56)  # Default to 56 jobs (8 pages)

        # Validate inputs
        if not linkedin_username or not linkedin_password:
            return jsonify({
                "error": "LinkedIn username and password are required",
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
        
        print(f"🔍 Scraping request: {num_jobs} jobs for user: {linkedin_username}")
        
        # Run the async scraper in the Flask context
        result = asyncio.run(scrape_linkedin_jobs_async(linkedin_username, linkedin_password, num_jobs))
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in /api/jobs endpoint: {e}")
        return jsonify({
            "error": f"Server error: {str(e)}",
            "jobs": []
        }), 500

@app.route('/api/indeed-jobs', methods=['POST'])
def get_indeed_jobs():
    """Scrape Indeed jobs using Google OAuth login"""
    try:
        data = request.get_json()
        
        # Extract parameters
        gmail_email = data.get('gmail_email')
        gmail_password = data.get('gmail_password')
        keywords = data.get('keywords', 'intern')
        location = data.get('location', '')
        num_jobs = data.get('num_jobs', 56)
        
        # Validate required fields
        if not gmail_email or not gmail_password:
            return jsonify({
                "success": False,
                "error": "Gmail email and password are required",
                "jobs": []
            }), 400
        
        # Calculate pages (Indeed typically shows 10 jobs per page)
        max_pages = max(1, min(20, (num_jobs + 9) // 10))  # Round up, max 20 pages
        
        # Import and run the Indeed scraper
        from jobs.main2_nodriver import main as indeed_main
        
        # Run the async scraper
        scraped_jobs = asyncio.run(indeed_main(
            gmail_email=gmail_email,
            gmail_password=gmail_password,
            keywords=keywords,
            location=location
        ))
        
        # Convert Pydantic models to dicts for JSON response
        jobs_data = [job.model_dump() for job in scraped_jobs]
        
        return jsonify({
            "success": True,
            "message": f"Successfully scraped {len(jobs_data)} Indeed jobs",
            "total_jobs": len(jobs_data),
            "jobs": jobs_data
        })
        
    except Exception as e:
        print(f"❌ Error in /api/indeed-jobs endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "jobs": []
        }), 500


if __name__ == '__main__':
    # For testing without starting the server
    # with app.app_context():
    #     result = get_jobs()
    #     print(result)

    # Start the Flask server
    app.run(port=8000, debug=True)

