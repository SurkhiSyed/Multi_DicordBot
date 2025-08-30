#!/usr/bin/env python3

from linkedin_parser import LinkedInJobParser

def test_extraction():
    print("🧪 Testing improved company extraction...")
    
    test_cases = [
        ("Senior FPGA/DSP Engineer", "Senior FPGA/DSP Engineer Senior FPGA/DSP Engineer Richmond, BC (On-site)", ""),
        ("Embedded Systems Developer", "Embedded Systems Developer Embedded Systems Developer Pickering, ON (On-site)", ""),
        ("Software Developer Intern - Growth", "Software Developer Intern - Growth - WINTER 2026 Growth Montreal, QC (On-site)", "Growth"),
        ("Data Analytics Internship", "Data Analytics Internship Analytics Vancouver, BC (Remote)", ""),
        ("Software Architect", "ArchitectSoftware Architect Toronto, ON (Hybrid)", ""),
        ("GPTZero job", "Software Engineering Intern GPTZero Toronto, ON (Remote)", "GPTZero"),
        ("Nokia job", "Data Science Co-op/Intern Nokia Kanata, ON (Hybrid)", "Nokia"),
    ]
    
    for title, mixed_text, expected in test_cases:
        result = LinkedInJobParser._extract_company_from_mixed_text(mixed_text, title)
        print(f"\nTitle: {title}")
        print(f"Mixed text: {mixed_text}")
        print(f"Expected: {expected}")
        print(f"Got: {result}")
        status = "✅" if result == expected or (expected == "" and result == "") else "❌"
        print(f"Status: {status}")
        print("-" * 80)

if __name__ == "__main__":
    test_extraction()
