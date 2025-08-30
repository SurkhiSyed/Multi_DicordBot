"""
Test company extraction from mixed LinkedIn text
"""
from linkedin_parser import LinkedInJobParser
import re

def test_company_extraction():
    """Test company extraction from problematic mixed text"""
    test_cases = [
        {
            "text": "Software Engineering InternSoftware Engineering Intern GPTZero Toronto, ON (Remote)",
            "expected": "GPTZero"
        },
        {
            "text": "Software Engineer Co-op Student Software Engineer Co-op Student with verification Foresters Financial Toronto, ON (Hybrid)",
            "expected": "Foresters Financial"
        },
        {
            "text": "Backend Engineer (Co-op) - Fall Term Backend Engineer (Co-op) - Fall Term with verification League Toronto, ON (On-site)",
            "expected": "League"
        },
        {
            "text": "Software Developer (Co-op) Software Developer (Co-op) with verification Corpay Vancouver, BC",
            "expected": "Corpay"
        },
        {
            "text": "ArchitectArchitect Lanescape | Architecture + Construction Toronto, ON (On-site)",
            "expected": "Lanescape"
        }
    ]
    
    print("🧪 Testing company extraction...")
    
    for test_case in test_cases:
        text = test_case["text"]
        expected = test_case["expected"]
        
        # Try different regex patterns
        print(f"\nText: {text}")
        print(f"Expected: {expected}")
        
        # Pattern 1: Between duplicate job title and location
        # Remove duplicated parts first
        words = text.split()
        if len(words) >= 4:
            mid_point = len(words) // 2
            first_half = words[:mid_point]
            second_half = words[mid_point:]
            if first_half == second_half:
                remaining_text = text[len(' '.join(first_half)):].strip()
                print(f"After removing duplicate: {remaining_text}")
        
        # Pattern 2: Find known companies
        known_companies = ['GPTZero', 'Foresters Financial', 'League', 'Corpay', 'Lanescape', 'Intact', 'Feroot Security']
        for company in known_companies:
            if company.lower() in text.lower():
                print(f"Found known company: {company}")
                break
        
        # Pattern 3: Regex for verification pattern
        verification_match = re.search(r'verification\s+([^,\(]+?)(?:\s+[A-Z][a-z]+,|\s+\()', text, re.IGNORECASE)
        if verification_match:
            print(f"Verification pattern found: {verification_match.group(1).strip()}")
        
        # Pattern 4: Look for capitalized words between title and location
        # Remove job title duplicates, then find capitalized words
        title_removed = re.sub(r'(Software|Engineer|Backend|Developer|Co-op|Student|Intern|Architect|Data|Science|JavaScript|Development|Fall|Term)\s*', '', text, flags=re.IGNORECASE)
        title_removed = re.sub(r'\s+', ' ', title_removed).strip()
        print(f"After removing job words: {title_removed}")
        
        location_words = ['Toronto', 'Vancouver', 'Montreal', 'Remote', 'Hybrid', 'On-site', 'BC', 'ON', 'QC']
        words = title_removed.split()
        for word in words:
            if (len(word) > 2 and 
                word[0].isupper() and 
                word not in location_words and 
                'verification' not in word.lower()):
                print(f"Potential company: {word}")
                break
        
        print("-" * 80)

if __name__ == "__main__":
    test_company_extraction()
