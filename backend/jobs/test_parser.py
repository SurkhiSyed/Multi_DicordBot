"""
Test the improved LinkedIn parser on debug HTML files
"""
from linkedin_parser import LinkedInJobParser
import os

def test_parser_on_file(filename):
    """Test the parser on a specific HTML file"""
    if not os.path.exists(filename):
        print(f"❌ File {filename} not found")
        return
    
    print(f"🧪 Testing parser on {filename}")
    
    with open(filename, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    jobs = LinkedInJobParser.extract_jobs_from_html(html_content)
    
    print(f"✅ Extracted {len(jobs)} jobs")
    
    # Show first few jobs
    for i, job in enumerate(jobs[:5]):
        print(f"\n📋 Job {i+1}:")
        print(f"   Title: {job.name}")
        print(f"   Company: {job.company}")
        print(f"   Location: {job.location}")
        print(f"   Type: {job.job_type}")
        print(f"   Link: {job.application_link[:80]}...")

def main():
    """Test parser on all debug files"""
    debug_files = [
        'nodriver_debug_page_1.html',
        'nodriver_debug_page_2.html'
    ]
    
    for filename in debug_files:
        test_parser_on_file(filename)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
