#!/usr/bin/env python3

from bs4 import BeautifulSoup

def debug_page2_filtering():
    """Debug why Page 2 is filtering out 18 out of 25 jobs"""
    
    try:
        # Read the newest debug file from page 2
        with open('nodriver_debug_page_2.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        job_cards = soup.select('li[data-occludable-job-id]')
        print(f"🔍 Found {len(job_cards)} job cards on page 2")
        
        valid_count = 0
        invalid_count = 0
        
        for i, card in enumerate(job_cards, 1):
            card_classes = card.get('class', []) if hasattr(card, 'get') else []
            card_text = card.get_text() if hasattr(card, 'get_text') else str(card)
            
            # Check the same filtering criteria as in the parser
            skip_indicators = ['ad', 'promoted', 'sponsor', 'advertisement']
            
            # Check if this looks like an ad or promotion
            is_ad = any(indicator in ' '.join(card_classes).lower() for indicator in skip_indicators)
            
            # Check if card is too small
            is_too_small = len(card_text.strip()) < 20
            
            # Check if card has minimal job-related content
            job_indicators = ['job', 'position', 'role', 'intern', 'engineer', 'developer', 'analyst']
            has_job_content = any(indicator in card_text.lower() for indicator in job_indicators)
            
            # Determine if this card would be filtered
            should_skip = is_ad or is_too_small or not has_job_content
            
            if should_skip:
                invalid_count += 1
                print(f"❌ Card {i}: FILTERED")
                print(f"   - Is ad: {is_ad}")
                print(f"   - Too small: {is_too_small} (length: {len(card_text.strip())})")
                print(f"   - No job content: {not has_job_content}")
                print(f"   - Classes: {card_classes}")
                print(f"   - Text preview: {card_text.strip()[:100]}...")
                print()
            else:
                valid_count += 1
                print(f"✅ Card {i}: VALID")
                # Show first line of text to identify the job
                first_line = card_text.strip().split('\n')[0] if card_text.strip() else "No text"
                print(f"   - Preview: {first_line}")
                print()
        
        print(f"📊 Summary:")
        print(f"   Total cards: {len(job_cards)}")
        print(f"   Valid cards: {valid_count}")
        print(f"   Filtered cards: {invalid_count}")
        
    except FileNotFoundError:
        print("❌ Debug file 'nodriver_debug_page_2.html' not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_page2_filtering()
