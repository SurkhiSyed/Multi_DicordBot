"""
Debug script to analyze LinkedIn HTML and understand card extraction issues
"""
from bs4 import BeautifulSoup
import os

def analyze_html_file(filename):
    """Analyze an HTML file to understand the job card structure"""
    if not os.path.exists(filename):
        print(f"❌ File {filename} not found")
        return
    
    print(f"🔍 Analyzing {filename}...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all potential job cards
    selectors_to_test = [
        'li[data-occludable-job-id]',
        '.jobs-search-results__list-item',
        '.job-search-card',
        '.base-card',
        '.base-search-card',
        'li.result-card',
        'article'
    ]
    
    for selector in selectors_to_test:
        cards = soup.select(selector)
        if cards:
            print(f"\n✅ Found {len(cards)} cards with selector: {selector}")
            
            # Analyze first few cards
            for i, card in enumerate(cards[:5]):
                print(f"\n--- Card {i+1} Analysis ---")
                print(f"Classes: {card.get('class', [])}")
                print(f"Data attributes: {[attr for attr in card.attrs if attr.startswith('data-')]}")
                
                # Look for titles
                title_selectors = ['h3', 'h4', 'a[href*="jobs"]', '.job-title']
                for title_sel in title_selectors:
                    title_elem = card.select_one(title_sel)
                    if title_elem:
                        title_text = title_elem.get_text().strip()[:100]
                        print(f"Title ({title_sel}): {title_text}")
                        break
                else:
                    print("❌ No title found")
                
                # Look for company
                company_selectors = ['h4', '.company', '.subtitle']
                for comp_sel in company_selectors:
                    comp_elem = card.select_one(comp_sel)
                    if comp_elem:
                        comp_text = comp_elem.get_text().strip()[:50]
                        print(f"Company ({comp_sel}): {comp_text}")
                        break
                else:
                    print("❌ No company found")
                
                # Check card content length
                card_text = card.get_text()
                print(f"Content length: {len(card_text)} chars")
                print(f"Preview: {card_text[:150]}...")
            
            break
    else:
        print("❌ No job cards found with any selector")

def main():
    """Analyze recent debug files"""
    debug_files = [
        'nodriver_debug_page_1.html',
        'nodriver_debug_page_2.html',
        'debug_page_1.html',
        'debug_page_2.html'
    ]
    
    for filename in debug_files:
        if os.path.exists(filename):
            analyze_html_file(filename)
            print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
