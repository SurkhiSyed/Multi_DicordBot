#!/usr/bin/env python3

import re

def debug_extract_company_from_mixed_text(mixed_text: str, job_title: str = "") -> str:
    """Debug version to show which strategy is being used"""
    import re
    
    print(f"🔍 Debugging extraction for: '{mixed_text}'")
    
    # Strategy 1: First try to find known companies in the text
    known_companies = ['GPTZero', 'Foresters Financial', 'League', 'Corpay', 'Intact', 'Feroot Security', 'Lanescape']
    
    mixed_text_lower = mixed_text.lower()
    for known_company in known_companies:
        if known_company.lower() in mixed_text_lower:
            print(f"✅ Strategy 1 (Known companies): Found '{known_company}'")
            return known_company
    
    # Strategy 2: Look for text between "verification" and location indicators
    verification_match = re.search(r'verification\s+([^,\(]+?)(?:\s+[A-Z][a-z]+,|\s+\()', mixed_text, re.IGNORECASE)
    if verification_match:
        potential_company = verification_match.group(1).strip()
        # Clean up the potential company name
        potential_company = re.sub(r'\s+', ' ', potential_company)
        if len(potential_company) > 1 and not any(word in potential_company.lower() for word in ['remote', 'hybrid', 'on-site']):
            print(f"✅ Strategy 2 (Verification pattern): Found '{potential_company}'")
            return potential_company
    
    # Strategy 2.5: Special patterns for specific cases we've seen
    # Pattern: "JobTitle - CompanyName - SEASON YEAR CompanyName Location"
    special_pattern = re.search(r'-\s+WINTER\s+\d{4}\s+([A-Z][a-z]+)\s+[A-Z]', mixed_text)
    if special_pattern:
        potential_company = special_pattern.group(1)
        if potential_company not in ['Montreal', 'Toronto', 'Vancouver', 'Calgary', 'Ottawa']:
            print(f"✅ Strategy 2.5 (Special winter pattern): Found '{potential_company}'")
            return potential_company
            
    # Pattern: "CompanyName Location, Province"  
    location_before_pattern = re.search(r'\b([A-Z][a-z]+)\s+(?:Montreal|Toronto|Vancouver|Calgary|Ottawa|Richmond|Pickering|Kanata),?\s+(?:QC|ON|BC|AB)', mixed_text)
    if location_before_pattern:
        potential_company = location_before_pattern.group(1)
        job_titles = ['software', 'data', 'senior', 'junior', 'embedded', 'engineer', 'developer', 
                     'architect', 'analyst', 'manager', 'specialist', 'coordinator',
                     'assistant', 'associate', 'director', 'lead', 'principal',
                     'analytics', 'systems', 'solutions', 'technologies']
        if potential_company.lower() not in job_titles:
            print(f"✅ Strategy 2.6 (Location pattern): Found '{potential_company}'")
            return potential_company
        else:
            print(f"❌ Strategy 2.6 (Location pattern): Filtered out job title '{potential_company}'")
    
    print("❌ No strategies matched, returning empty string")
    return ""

# Test the problematic cases
test_cases = [
    ("Senior FPGA/DSP Engineer", "Senior FPGA/DSP Engineer Senior FPGA/DSP Engineer Richmond, BC (On-site)"),
    ("Embedded Systems Developer", "Embedded Systems Developer Embedded Systems Developer Pickering, ON (On-site)"),
    ("Software Developer Intern - Growth", "Software Developer Intern - Growth - WINTER 2026 Growth Montreal, QC (On-site)"),
    ("Data Analytics Internship", "Data Analytics Internship Analytics Vancouver, BC (Remote)"),
    ("Software Architect", "ArchitectSoftware Architect Toronto, ON (Hybrid)"),
]

print("🧪 Debug testing company extraction...\n")

for title, mixed_text in test_cases:
    print(f"Title: {title}")
    print(f"Mixed text: {mixed_text}")
    result = debug_extract_company_from_mixed_text(mixed_text, title)
    print(f"Result: '{result}'")
    print("-" * 80)
