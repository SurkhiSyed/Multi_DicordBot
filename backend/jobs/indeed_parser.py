from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re
from model.indeed import Indeed  # Fixed import path

class IndeedJobParser:
    """Parser for Indeed job listings HTML"""
    
    @staticmethod
    def extract_jobs_from_html(html_content: str) -> List[Indeed]:
        """Extract job data from Indeed HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        jobs = []
        
        print(f"🔍 Parsing HTML content (length: {len(html_content)})")
        
        # Try multiple selectors for Indeed job cards
        job_cards = []
        
        # Primary selector - Indeed's main job card selector
        job_cards = soup.select('[data-testid="slider_item"], .slider_container .slider_item')
        
        if not job_cards:
            # Fallback selector - table-based layout
            job_cards = soup.select('table[role="table"] tr, .jobsearch-SerpJobCard')
            
        if not job_cards:
            # Alternative selector - job result items
            job_cards = soup.select('[data-jk], .job_seen_beacon')
            
        if not job_cards:
            print("❌ No job cards found with any selector")
            return jobs
            
        print(f"✅ Found {len(job_cards)} job cards")
        
        # Filter valid job cards
        filtered_cards = []
        for card in job_cards:
            if IndeedJobParser._is_valid_job_card(card):
                filtered_cards.append(card)
        
        print(f"📝 After filtering: {len(filtered_cards)} cards remain")
        
        # Extract job data from each card
        for i, card in enumerate(filtered_cards):
            try:
                job_data = IndeedJobParser._extract_job_from_card(card)
                if job_data:
                    job = Indeed(**job_data)
                    jobs.append(job)
                    print(f"✅ Extracted job {i + 1}: {job.name} at {job.company}")
                else:
                    print(f"⚠️ Could not extract data from job card {i + 1}")
            except Exception as e:
                print(f"❌ Error extracting job {i + 1}: {e}")
                continue
        
        print(f"✅ Extracted {len(jobs)} jobs")
        return jobs
    
    @staticmethod
    def _is_valid_job_card(card) -> bool:
        """Check if a job card contains valid job data"""
        # Check for minimum content
        text_content = card.get_text(strip=True)
        if len(text_content) < 20:
            return False
        
        # Check for Indeed ads or sponsored content that we want to skip
        if any(indicator in card.get('class', []) for indicator in ['sponsored', 'ad-slot']):
            return False
        
        # Check if it has job-like content
        has_title = card.select('[data-testid="job-title"], .jobTitle, [data-testid="job-title-link"]')
        has_company = card.select('[data-testid="company-name"], .companyName')
        
        return bool(has_title or has_company or 'job' in text_content.lower())
    
    @staticmethod
    def _extract_job_from_card(card) -> Dict[str, Any]:
        """Extract job information from a single job card"""
        
        # Extract job title
        title_elem = card.select_one('[data-testid="job-title"] a, [data-testid="job-title-link"], .jobTitle a, [data-testid="job-title"] span')
        title = IndeedJobParser._clean_text(title_elem.get_text(strip=True)) if title_elem else "Unknown Title"
        
        # Extract company name
        company_elem = card.select_one('[data-testid="company-name"], .companyName a, [data-testid="company-name"] span')
        company = IndeedJobParser._clean_text(company_elem.get_text(strip=True)) if company_elem else "Unknown Company"
        
        # Extract location
        location_elem = card.select_one('[data-testid="job-location"], .companyLocation, [data-testid="remote-job-location"]')
        location = IndeedJobParser._clean_text(location_elem.get_text(strip=True)) if location_elem else "Unknown Location"
        
        # Determine location type
        location_type = IndeedJobParser._determine_location_type(location)
        
        # Extract job type (full-time, part-time, etc.)
        job_type_elem = card.select_one('[data-testid="job-type"], .jobMetadata, .metadata')
        job_type_text = job_type_elem.get_text(strip=True) if job_type_elem else ""
        job_type = IndeedJobParser._determine_job_type(job_type_text, title)
        
        # Extract application link
        link_elem = card.select_one('[data-testid="job-title"] a, [data-testid="job-title-link"], .jobTitle a')
        if link_elem and link_elem.get('href'):
            link = link_elem.get('href')
            if link.startswith('/'):
                link = f"https://www.indeed.com{link}"
        else:
            # Try to find data-jk attribute for job ID
            job_id = card.get('data-jk')
            if job_id:
                link = f"https://www.indeed.com/viewjob?jk={job_id}"
            else:
                link = "https://www.indeed.com"
        
        # Extract description (often limited on Indeed job cards)
        description_elem = card.select_one('.summary, [data-testid="job-snippet"], .jobDescription')
        description = IndeedJobParser._clean_text(description_elem.get_text(strip=True)) if description_elem else ""
        
        # If no description found, use the full card text as fallback
        if not description:
            description = IndeedJobParser._clean_text(card.get_text(strip=True)[:200] + "...")
        
        job_data = {
            "name": title,
            "company": company,
            "location": location,
            "location_type": location_type,
            "job_type": job_type,
            "application_link": link,
            "description": description
        }
        
        print(f"🔍 Extracted: '{title}' at '{company}' in '{location}'")
        return job_data
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common Indeed artifacts
        cleaned = re.sub(r'new\s*job', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'posted.*?ago', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    @staticmethod
    def _determine_location_type(location: str) -> str:
        """Determine if job is remote, hybrid, or on-site"""
        location_lower = location.lower()
        
        if any(keyword in location_lower for keyword in ['remote', 'work from home', 'telecommute']):
            return 'Remote'
        elif any(keyword in location_lower for keyword in ['hybrid', 'flexible']):
            return 'Hybrid'
        else:
            return 'On-site'
    
    @staticmethod
    def _determine_job_type(job_type_text: str, title: str) -> str:
        """Determine job type from metadata or title"""
        text = (job_type_text + " " + title).lower()
        
        if any(keyword in text for keyword in ['intern', 'internship']):
            return 'Internship'
        elif any(keyword in text for keyword in ['part-time', 'part time', 'pt']):
            return 'Part-time'
        elif any(keyword in text for keyword in ['contract', 'contractor', 'freelance']):
            return 'Contract'
        elif any(keyword in text for keyword in ['temp', 'temporary']):
            return 'Temporary'
        else:
            return 'Full-time'