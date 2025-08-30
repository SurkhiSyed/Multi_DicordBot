"""
Quick test for title cleaning function
"""
from linkedin_parser import LinkedInJobParser

def test_title_cleaning():
    """Test the title cleaning function with various problematic titles"""
    test_cases = [
        "Software Engineering InternSoftware Engineering Intern",
        "Backend Engineer (Co-op) - Fall TermBackend Engineer (Co-op) - Fall Term",
        "Data Science – 4 months Internship/CoopData Science – 4 months Internship/Coop",
        "Software Engineer Co-op Student with verification",
        "ArchitectArchitect",
        "JavaScript Development Co-op"
    ]
    
    print("🧪 Testing title cleaning...")
    for original in test_cases:
        cleaned = LinkedInJobParser._clean_title(original)
        print(f"Original: {original}")
        print(f"Cleaned:  {cleaned}")
        print("-" * 50)

if __name__ == "__main__":
    test_title_cleaning()
