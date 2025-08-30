#!/usr/bin/env python3

def test_word_filtering():
    """Test why job-related words are getting through the filter"""
    
    test_words = ["Engineer", "Developer", "Analytics", "Architect", "Growth", "Nokia", "GPTZero"]
    
    job_title_filter = ['remote', 'hybrid', 'onsite', 'canada', 'engineer', 'developer', 
                       'architect', 'analyst', 'manager', 'specialist', 'coordinator',
                       'assistant', 'associate', 'director', 'lead', 'principal',
                       'analytics', 'systems', 'solutions', 'technologies']
    
    print("🧪 Testing word filtering...")
    for word in test_words:
        is_filtered = word.lower() in job_title_filter
        print(f"Word: '{word}' -> Filtered: {is_filtered}")

if __name__ == "__main__":
    test_word_filtering()
