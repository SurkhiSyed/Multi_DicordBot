"""
LinkedIn Job Parser - Extracts job data from LinkedIn HTML
"""

from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from jobs.model.linkedin import Linkedin
import re
from datetime import datetime

class LinkedInJobParser:
    """Parses LinkedIn job listings from HTML content"""
    
    @staticmethod
    def extract_jobs_from_html(html_content: str) -> List[Linkedin]:
        """
        Extract job listings from LinkedIn HTML content
        
        Args:
            html_content: Raw HTML from LinkedIn jobs page
            
        Returns:
            List of Linkedin job objects
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        jobs = []
        
        print(f"🔍 Parsing HTML content (length: {len(html_content)})")
        
        # Try multiple possible selectors for job cards
        job_selectors = [
            # Page 1 structure (authenticated, broader results)
            '.job-search-card',  # This finds 60 cards with good structure
            
            # Page 2 structure (specific job feed)
            'li[data-occludable-job-id]',  # This finds 25 cards, needs different extraction
            
            # Fallback selectors
            '.jobs-search-results__list-item',
            '.base-card',
            '.base-search-card',
            'li.result-card',
            'article',
            '[data-job-id]',
            '.job-card',
            
            # Broader selectors for different LinkedIn layouts
            'li:has(h3)',
            'div[data-entity-urn*="job"]',
        ]
        
        job_cards = []
        for selector in job_selectors:
            cards = soup.select(selector)
            if cards:
                print(f"✅ Found {len(cards)} job cards using selector: {selector}")
                # Filter out obvious non-job cards
                filtered_cards = []
                for card in cards:
                    card_classes = ' '.join(card.get('class', [])).lower()
                    card_text = card.get_text().lower()
                    
                    # Only skip cards that are clearly ads or promotions (be less aggressive)
                    skip_indicators = ['ad-banner', 'promoted-job']  # Removed job-alert and premium-insight
                    if any(indicator in card_classes for indicator in skip_indicators):
                        continue
                        
                    # Only skip cards with very little content (lowered threshold)
                    if len(card.get_text().strip()) < 15:  # Reduced from 30 to 15
                        continue
                        
                    filtered_cards.append(card)
                
                print(f"📝 After filtering: {len(filtered_cards)} cards remain")
                job_cards = filtered_cards
                break
            else:
                print(f"❌ No cards found with selector: {selector}")
        
        if not job_cards:
            print("⚠️ No job cards found with any selector. Trying broader search...")
            # Try to find any list items or articles that might contain job data
            job_cards = soup.find_all(['li', 'article', 'div'], class_=lambda x: x and 'job' in x.lower() if x else False)
            print(f"🔍 Found {len(job_cards)} potential job containers with broad search")
        
        for i, card in enumerate(job_cards):
            try:
                job_data = LinkedInJobParser._extract_single_job(card, i+1)  # Pass card number for debugging
                if job_data:
                    jobs.append(job_data)
                    print(f"✅ Extracted job {i+1}: {job_data.name} at {job_data.company}")
                else:
                    print(f"⚠️ Could not extract data from card {i+1} (likely ad or different structure)")
            except Exception as e:
                print(f"❌ Error parsing job card {i+1}: {e}")
                # Print more debug info for problematic cards
                try:
                    card_text = card.get_text()[:200] if hasattr(card, 'get_text') else str(card)[:200]
                    print(f"   Card preview: {card_text}...")
                except:
                    print(f"   Could not preview card content")
                continue
                
        return jobs
    
    @staticmethod
    def _extract_single_job(card, card_number: int = 0) -> Optional[Linkedin]:
        """Extract data from a single job card"""
        
        # First, let's check if this is actually a job card or an ad/promotion
        card_classes = card.get('class', []) if hasattr(card, 'get') else []
        card_text = card.get_text() if hasattr(card, 'get_text') else str(card)
        
        # Skip if this looks like an ad or promotion
        if any(indicator in ' '.join(card_classes).lower() for indicator in ['ad', 'promoted', 'sponsor']):
            print(f"   Card {card_number}: Skipping ad/promoted content")
            return None
            
        # Skip if card is too small (but be less strict for lazy-loaded content)
        if len(card_text.strip()) < 5:  # Reduced from 20 to 5 to allow lazy-loaded cards
            print(f"   Card {card_number}: Skipping - too little content ({len(card_text)} chars)")
            return None
        
        # Try multiple selectors for job title
        title_selectors = [
            # For page 1 structure (.job-search-card) - get the actual job title, not company
            'h3 a span[title]',  # Job title is often in a span with title attribute
            'h3 a',  # Job title link
            'h3 span',  # Job title span
            'h3',  # Direct h3 (but this might be company name in some cases)
            
            # For page 2 structure (li[data-occludable-job-id])
            'h4 a', 
            '.job-search-card__title a',
            '.jobs-unified-top-card__job-title a',
            
            # Public LinkedIn
            '.base-search-card__title a',
            '.result-card__title a',
            
            # General selectors
            'a[data-tracking-control-name*="job"]',
            'h4',
            '.job-title',
            '[data-job-title]',
            'a[href*="/jobs/view/"]',
            
            # Fallback selectors
            'a[href*="linkedin.com/jobs"]',
            '.job-card-container h3',
            '.job-card h3'
        ]
        
        title = ""
        title_elem = None
        for selector in title_selectors:
            title_elem = card.select_one(selector)
            if title_elem:
                raw_title = LinkedInJobParser._clean_text(title_elem.get_text())
                
                # Additional cleaning for titles to remove duplicates and artifacts
                title = LinkedInJobParser._clean_title(raw_title)
                if title:
                    break
        
        if not title:  # Skip if no title found
            print(f"   Card {card_number}: No title found, skipping")
            return None
        
        # Try multiple selectors for company
        company_selectors = [
            # For page 1 structure (.job-search-card)
            'h4',  # Direct h4 element (like "Nuro", "Twitch")
            '.base-search-card__subtitle a',
            '.job-search-card__subtitle-link',
            
            # For page 2 structure (li[data-occludable-job-id])  
            '.job-search-card__subtitle',  # Company name in subtitle
            'h4 a',
            '.jobs-unified-top-card__company-name a',
            
            # General selectors  
            '.company-name',
            '[data-company-name]',
            'a[data-tracking-control-name*="company"]',
            '.base-search-card__subtitle',
            
            # Fallback selectors - look for text patterns
            '*:contains("verified")',  # Company names often appear near verification badges
            
            # Very specific fallback for the structure we see
            'div:nth-child(2)',  # Sometimes company is second div
            'span:contains("verification")',  # Look near verification text
        ]
        
        company = ""
        raw_company_text = ""
        for selector in company_selectors:
            company_elem = card.select_one(selector)
            if company_elem:
                raw_company_text = LinkedInJobParser._clean_text(company_elem.get_text())
                if raw_company_text and len(raw_company_text) > 1:  # Make sure it's not just whitespace
                    # Apply smart company extraction to the raw text
                    company = LinkedInJobParser._extract_company_from_mixed_text(raw_company_text, title)
                    if company:
                        break
        
        # If still no company, try a different approach - parse the full card text
        if not company:
            full_text = card.get_text()
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # For the page 2 structure, company often appears in a specific pattern
            # Look for lines that contain company names (usually after job title)
            known_companies = ['GPTZero', 'Foresters Financial', 'League', 'Corpay', 'Intact', 'Feroot Security', 'Lanescape']
            
            # Strategy 1: First try to find known companies in the text
            full_text_lower = full_text.lower()
            for known_company in known_companies:
                if known_company.lower() in full_text_lower:
                    company = known_company
                    break
            
            # Strategy 2: If still no company found, try regex patterns
            if not company:
                import re
                
                # Pattern 1: look for text between "verification" and location indicators
                verification_match = re.search(r'verification\s+([^,\(]+?)(?:\s+[A-Z][a-z]+,|\s+\()', full_text, re.IGNORECASE)
                if verification_match:
                    potential_company = verification_match.group(1).strip()
                    # Clean up the potential company name
                    potential_company = re.sub(r'\s+', ' ', potential_company)
                    if len(potential_company) > 1 and not any(word in potential_company.lower() for word in ['remote', 'hybrid', 'on-site']):
                        company = potential_company
                
                # Pattern 2: Look for capitalized words that appear after removing job-related terms
                if not company:
                    # Remove job-related words to isolate company names
                    cleaned_text = re.sub(r'\b(Software|Engineer|Backend|Developer|Co-op|Student|Intern|Architect|Data|Science|JavaScript|Development|Fall|Term|months|Internship|Coop|Winter|with|verification)\b', '', full_text, flags=re.IGNORECASE)
                    cleaned_text = re.sub(r'[()|-]', ' ', cleaned_text)  # Remove punctuation
                    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
                    
                    # Look for capitalized words that could be company names
                    location_words = ['Toronto', 'Vancouver', 'Montreal', 'Remote', 'Hybrid', 'On-site', 'BC', 'ON', 'QC', 'Quebec']
                    words = cleaned_text.split()
                    
                    for word in words:
                        word = word.strip('.,()[]')  # Remove punctuation
                        if (len(word) > 2 and 
                            word[0].isupper() and 
                            word not in location_words and 
                            word.isalpha()):  # Only alphabetic words
                            company = word
                            break
                
                # Pattern 3: For multi-word companies, look for consecutive capitalized words
                if not company or len(company.split()) == 1:
                    # Look for multi-word company names like "Foresters Financial"
                    words = full_text.split()
                    for i, word in enumerate(words):
                        if (word in ['Foresters', 'Financial'] and 
                            i + 1 < len(words) and 
                            words[i + 1] in ['Financial', 'Security', 'Construction']):
                            company = f"{word} {words[i + 1]}"
                            break
            
            # If still no company found, use a more sophisticated approach
            if not company and len(lines) >= 3:
                # Pattern: Title, Company, Location
                # Skip lines that are clearly titles (duplicates) or locations
                for i, line in enumerate(lines[1:6], 1):  # Start from second line
                    line_clean = LinkedInJobParser._clean_text(line)
                    
                    # Skip if it's a duplicate of the title
                    if title and line_clean.lower() in title.lower():
                        continue
                    
                    # Skip if it looks like location
                    if any(loc_word in line_clean.lower() for loc_word in 
                          ['remote', 'on-site', 'hybrid', ', on', ', bc', ', ab', ', qc', 'toronto', 'vancouver', 'montreal']):
                        continue
                    
                    # Skip if it contains verification text
                    if 'verification' in line_clean.lower():
                        continue
                    
                    # Skip very short lines or lines with numbers (likely metadata)
                    if len(line_clean) < 3 or any(char.isdigit() for char in line_clean):
                        continue
                    
                    # This might be the company
                    if len(line_clean) > 2 and len(line_clean) < 50:  # Reasonable company name length
                        company = line_clean
                        break
        
        # Try multiple selectors for location
        location_selectors = [
            # Authenticated LinkedIn
            '.job-search-card__location',
            '.base-search-card__metadata',
            '.jobs-unified-top-card__bullet',
            
            # General selectors
            '.job-location',
            '[data-job-location]',
            '.job-search-card__metadata',
            '.base-search-card__metadata-item',
            
            # Fallback selectors
            '.location',
            '.job-card-container .location'
        ]
        
        location = ""
        for selector in location_selectors:
            location_elem = card.select_one(selector)
            if location_elem:
                location = LinkedInJobParser._clean_text(location_elem.get_text())
                if location and len(location) > 1:
                    break
        
        # If still no location, parse from card text
        if not location:
            full_text = card.get_text()
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # Location often appears after company name
            # Look for patterns with location indicators
            for line in lines:
                line = LinkedInJobParser._clean_text(line)
                if any(loc_indicator in line.lower() for loc_indicator in 
                      ['remote', 'on-site', 'hybrid', ', on', ', bc', ', ab', ', ca', 'toronto', 'vancouver', 'montreal']):
                    location = line
                    break
        
        # Extract application link
        application_link = ""
        link_elem = card.find('a', href=True)
        if link_elem and link_elem.get('href'):
            href = link_elem['href']
            if href.startswith('/'):
                application_link = f"https://www.linkedin.com{href}"
            elif href.startswith('http'):
                application_link = href
        
        # Extract posting date (if available)
        date_selectors = [
            'time',
            '.job-search-card__listdate',
            '.base-search-card__metadata time',
            '[data-job-posted]'
        ]
        
        posting_date = ""
        for selector in date_selectors:
            date_elem = card.select_one(selector)
            if date_elem:
                posting_date = LinkedInJobParser._clean_text(date_elem.get_text())
                if posting_date:
                    break
        
        if not posting_date:
            posting_date = datetime.now().strftime("%Y-%m-%d")
        
        # Extract job type and location type (often not available in search results)
        job_type = "Full-time"  # Default
        location_type = "On-site"  # Default
        
        # Try to infer from title or description
        title_lower = title.lower()
        if any(keyword in title_lower for keyword in ['intern', 'internship']):
            job_type = "Internship"
        elif any(keyword in title_lower for keyword in ['part-time', 'part time']):
            job_type = "Part-time"
        elif any(keyword in title_lower for keyword in ['contract', 'contractor']):
            job_type = "Contract"
            
        location_lower = location.lower()
        if any(keyword in location_lower for keyword in ['remote', 'work from home']):
            location_type = "Remote"
        elif any(keyword in location_lower for keyword in ['hybrid']):
            location_type = "Hybrid"
        
        # Extract description (usually not available in search results)
        description = f"Job at {company} in {location}" if company and location else title
        
        print(f"🔍 Extracted: '{title}' at '{company}' in '{location}'")
        
        return Linkedin(
            name=title,
            company=company or "Unknown Company",
            location_type=location_type,
            job_type=job_type,
            posting_date=posting_date,
            application_link=application_link,
            location=location or "Location not specified",
            description=description
        )
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common LinkedIn artifacts
        cleaned = re.sub(r'new\s*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'promoted\s*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'with verification\s*$', '', cleaned, flags=re.IGNORECASE)
        
        # Remove duplicate text (like "Title Title")
        words = cleaned.split()
        if len(words) >= 2:
            # Check if the text is just repeated (like "Engineer Engineer")
            half_len = len(words) // 2
            if len(words) % 2 == 0:  # Even number of words
                first_half = ' '.join(words[:half_len])
                second_half = ' '.join(words[half_len:])
                if first_half == second_half:
                    cleaned = first_half
        
        return cleaned.strip()

    @staticmethod
    def _clean_title(text: str) -> str:
        """Clean job title specifically, handling duplicates and artifacts"""
        if not text:
            return ""
        
        # First apply general cleaning
        cleaned = LinkedInJobParser._clean_text(text)
        
        # Handle the specific case where the entire title is repeated
        # Example: "Software Engineering InternSoftware Engineering Intern" -> "Software Engineering Intern"
        
        # Strategy 1: Check if the text is simply duplicated (no spaces between)
        if len(cleaned) > 6:  # Only for reasonably long titles
            mid_point = len(cleaned) // 2
            first_half = cleaned[:mid_point]
            second_half = cleaned[mid_point:]
            
            if first_half == second_half:
                cleaned = first_half
        
        # Strategy 2: Handle duplicates separated by spaces
        words = cleaned.split()
        if len(words) >= 4:  # Need at least 4 words to check for duplication
            mid_point = len(words) // 2
            first_half_words = words[:mid_point]
            second_half_words = words[mid_point:]
            
            # If the two halves are identical, keep only one
            if first_half_words == second_half_words:
                cleaned = ' '.join(first_half_words)
                words = cleaned.split()  # Update words for next step
        
        # Strategy 3: Handle adjacent word duplications (like "Engineer Engineer")
        if len(words) >= 2:
            deduped_words = []
            i = 0
            while i < len(words):
                current_word = words[i]
                # Check if next word is identical (case insensitive)
                if i + 1 < len(words) and words[i + 1].lower() == current_word.lower():
                    deduped_words.append(current_word)
                    i += 2  # Skip the duplicate
                else:
                    deduped_words.append(current_word)
                    i += 1
            cleaned = ' '.join(deduped_words)
        
        # Remove specific LinkedIn artifacts from titles
        cleaned = re.sub(r'\s*with verification\s*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*new grad\s*', ' New Grad ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
        
        return cleaned.strip()

    @staticmethod
    def _extract_company_from_mixed_text(mixed_text: str, job_title: str = "") -> str:
        """Extract clean company name from mixed text containing job titles, companies, and locations"""
        import re
        
        # Strategy 1: First try to find known companies in the text
        known_companies = [
            'GPTZero', 'Foresters Financial', 'League', 'Corpay', 'Intact', 'Feroot Security', 'Lanescape',
            'Nokia', 'Canadian Natural Resources Limited', 'Giatec', 'Exeevo Canada'
        ]
        
        mixed_text_lower = mixed_text.lower()
        for known_company in known_companies:
            if known_company.lower() in mixed_text_lower:
                return known_company
        
        # Strategy 2: Look for text between "verification" and location indicators
        verification_match = re.search(r'verification\s+([^,\(]+?)(?:\s+[A-Z][a-z]+,|\s+\()', mixed_text, re.IGNORECASE)
        if verification_match:
            potential_company = verification_match.group(1).strip()
            # Clean up the potential company name
            potential_company = re.sub(r'\s+', ' ', potential_company)
            if len(potential_company) > 1 and not any(word in potential_company.lower() for word in ['remote', 'hybrid', 'on-site']):
                return potential_company
        
        # Strategy 2.5: Special patterns for specific cases we've seen
        # Pattern: "JobTitle - CompanyName - SEASON YEAR CompanyName Location"
        special_pattern = re.search(r'-\s+WINTER\s+\d{4}\s+([A-Z][a-z]+)\s+[A-Z]', mixed_text)
        if special_pattern:
            potential_company = special_pattern.group(1)
            if potential_company not in ['Montreal', 'Toronto', 'Vancouver', 'Calgary', 'Ottawa']:
                return potential_company
                
        # Pattern: "CompanyName Location, Province"  
        location_before_pattern = re.search(r'\b([A-Z][a-z]+)\s+(?:Montreal|Toronto|Vancouver|Calgary|Ottawa|Richmond|Pickering|Kanata),?\s+(?:QC|ON|BC|AB)', mixed_text)
        if location_before_pattern:
            potential_company = location_before_pattern.group(1)
            # Use comprehensive job title filter
            job_titles = ['software', 'data', 'senior', 'junior', 'embedded', 'engineer', 'developer', 
                         'architect', 'analyst', 'manager', 'specialist', 'coordinator',
                         'assistant', 'associate', 'director', 'lead', 'principal',
                         'analytics', 'systems', 'solutions', 'technologies']
            if potential_company.lower() not in job_titles:
                return potential_company
        
        # Strategy 3: Look for multi-word company names that are likely real companies
        # Look for patterns like "Company Name Inc", "Company Ltd", etc.
        company_suffix_pattern = r'\b([A-Z][a-zA-Z\s&]+(?:Inc|Ltd|Limited|Corporation|Corp|Company|LLC|Group|Technologies|Solutions|Systems|Canada|International))\b'
        company_match = re.search(company_suffix_pattern, mixed_text)
        if company_match:
            potential_company = company_match.group(1).strip()
            # Make sure it's not just a job title
            if not any(title_word in potential_company.lower() for title_word in ['engineer', 'developer', 'intern', 'student', 'analyst', 'specialist']):
                return potential_company
        
        # Strategy 4: Look for capitalized words that appear after removing job-related terms
        # But be more selective to avoid picking up job title words
        job_related_words = [
            'Software', 'Engineer', 'Backend', 'Developer', 'Co-op', 'Student', 'Intern', 'Architect', 
            'Data', 'Science', 'JavaScript', 'Development', 'Fall', 'Term', 'months', 'Internship', 
            'Coop', 'Winter', 'with', 'verification', 'Senior', 'Junior', 'Lead', 'Principal', 
            'Analytics', 'Systems', 'Embedded', 'Growth', 'Machine', 'Learning', 'FPGA', 'DSP',
            'Automation', 'Aquatic', 'Informatics'
        ]
        
        # Remove job-related words to isolate company names
        cleaned_text = mixed_text
        for word in job_related_words:
            cleaned_text = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned_text, flags=re.IGNORECASE)
        
        cleaned_text = re.sub(r'[()|-]', ' ', cleaned_text)  # Remove punctuation
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        # Look for capitalized words that could be company names
        location_words = ['Toronto', 'Vancouver', 'Montreal', 'Calgary', 'Ottawa', 'Kanata', 'Pickering', 'Richmond', 'Remote', 'Hybrid', 'On-site', 'BC', 'ON', 'QC', 'AB', 'Quebec']
        words = cleaned_text.split()
        
        # Look for words that are likely company names (longer, not common words)
        for word in words:
            word = word.strip('.,()[]')  # Remove punctuation
            if (len(word) > 3 and  # Company names are usually longer than 3 characters
                word[0].isupper() and 
                word not in location_words and 
                word.isalpha() and  # Only alphabetic words
                word.lower() not in ['remote', 'hybrid', 'onsite', 'canada', 'engineer', 'developer', 
                                   'architect', 'analyst', 'manager', 'specialist', 'coordinator',
                                   'assistant', 'associate', 'director', 'lead', 'principal',
                                   'analytics', 'systems', 'solutions', 'technologies']):  # Comprehensive job title filter
                return word
        
        # Strategy 5: If nothing else works, return empty string instead of original text
        # This prevents showing mixed text as company name
        return ""
