#!/usr/bin/env python3
"""
Debug script to test Bing Image Creator and see what's in the responses
"""

import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bing_generator import BingImageCreator

def debug_bing_response(cookie_value, prompt="A simple test image"):
    """Debug what Bing is actually returning."""
    
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    
    generator = BingImageCreator(auth_cookie=cookie_value)
    
    # Test the initial request
    create_url = "https://www.bing.com/images/create"
    data = {
        'q': prompt,
        'rt': '3',
        'FORM': 'GENCRE'
    }
    
    print("🔍 Testing Bing Image Creator...")
    print(f"Prompt: {prompt}")
    print(f"Cookie length: {len(cookie_value)}")
    
    response = generator.session.post(create_url, data=data, allow_redirects=True)
    print(f"\n📡 Response status: {response.status_code}")
    print(f"Final URL: {response.url}")
    
    # Extract request ID
    request_id = generator._extract_request_id(response.text)
    print(f"🆔 Request ID: {request_id}")
    
    if request_id:
        # Try polling once to see what we get
        poll_url = f"https://www.bing.com/images/create/async/results/{request_id}?q="
        print(f"\n🔄 Polling URL: {poll_url}")
        
        poll_response = generator.session.get(poll_url)
        print(f"Poll status: {poll_response.status_code}")
        
        # Look for any image URLs
        image_urls = generator._extract_image_urls(poll_response.text)
        print(f"🖼️  Found {len(image_urls)} image URLs")
        
        if image_urls:
            for i, url in enumerate(image_urls[:3]):
                print(f"  {i+1}. {url}")
        else:
            # Save response to file for inspection
            debug_file = Path("debug_response.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(poll_response.text)
            print(f"💾 Saved response to {debug_file} for inspection")
            
            # Show a snippet of the response
            response_snippet = poll_response.text[:500]
            print(f"📄 Response snippet: {response_snippet}...")
    
    return request_id is not None

if __name__ == "__main__":
    # Read the cookie
    try:
        with open("bing_cookie.txt", 'r') as f:
            cookie = f.read().strip()
        
        success = debug_bing_response(cookie)
        print(f"\n✅ Debug completed. Request ID found: {success}")
        
    except FileNotFoundError:
        print("❌ bing_cookie.txt not found")
    except Exception as e:
        print(f"❌ Error: {e}")
