#!/usr/bin/env python3

from bs4 import BeautifulSoup

def debug_card_filtering():
    """Debug why cards are being filtered out"""
    
    # Load the saved HTML file
    try:
        with open('nodriver_debug_page_2.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print("❌ Debug HTML file not found")
        return
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find cards using the same selector
    cards = soup.select('li[data-occludable-job-id]')
    print(f"🔍 Found {len(cards)} total cards")
    
    filtered_cards = []
    for i, card in enumerate(cards):
        card_classes = ' '.join(card.get('class', [])).lower()
        card_text = card.get_text().strip()
        
        print(f"\n📋 Card {i+1}:")
        print(f"   Classes: {card_classes[:100]}...")
        print(f"   Text length: {len(card_text)}")
        print(f"   Text preview: {card_text[:150]}...")
        
        # Check filtering criteria
        skip_indicators = ['ad-banner', 'promoted-job']
        has_skip_indicator = any(indicator in card_classes for indicator in skip_indicators)
        too_short = len(card_text) < 15
        
        print(f"   Has skip indicator: {has_skip_indicator}")
        print(f"   Too short: {too_short}")
        
        if has_skip_indicator:
            print(f"   ❌ SKIPPED: Contains skip indicator")
            continue
        
        if too_short:
            print(f"   ❌ SKIPPED: Too short ({len(card_text)} < 15)")
            continue
        
        print(f"   ✅ KEPT")
        filtered_cards.append(card)
    
    print(f"\n📊 Summary: {len(filtered_cards)}/{len(cards)} cards kept")

if __name__ == "__main__":
    debug_card_filtering()
