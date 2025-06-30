import requests
import re
import time
import json
from pathlib import Path
import logging

class BingImageCreatorV2:
    def __init__(self, auth_cookie=None):
        """
        Improved Bing Image Creator with better error handling and multiple approaches.
        
        Args:
            auth_cookie (str): Your _U cookie value from bing.com
        """
        self.auth_cookie = auth_cookie
        self.session = requests.Session()
        
        # Enhanced headers to better mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        
        if self.auth_cookie:
            self.session.cookies.set('_U', self.auth_cookie, domain='.bing.com')
            self.session.cookies.set('MUID', 'dummy_muid', domain='.bing.com')
    
    def create_images(self, prompt, output_dir="images/generated", num_images=4, timeout_minutes=5):
        """
        Generate images using Bing Image Creator with improved reliability.
        
        Args:
            prompt (str): Text prompt for image generation
            output_dir (str): Directory to save generated images
            num_images (int): Number of images to generate
            timeout_minutes (int): Maximum time to wait for generation
        
        Returns:
            list: Paths to downloaded images
        """
        if not self.auth_cookie:
            raise ValueError("Authentication cookie (_U) is required.")
        
        logging.info(f"Generating {num_images} images for prompt: {prompt[:100]}...")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Try approach 1: Direct creation
            return self._create_images_direct(prompt, output_path, num_images, timeout_minutes)
        except Exception as e1:
            logging.warning(f"Direct approach failed: {e1}")
            try:
                # Try approach 2: Browser simulation
                return self._create_images_browser_sim(prompt, output_path, num_images, timeout_minutes)
            except Exception as e2:
                logging.warning(f"Browser simulation failed: {e2}")
                try:
                    # Try approach 3: Simplified polling
                    return self._create_images_simple(prompt, output_path, num_images)
                except Exception as e3:
                    logging.error(f"All approaches failed: Direct={e1}, Browser={e2}, Simple={e3}")
                    raise Exception(f"Image generation failed with all methods. Last error: {e3}")
    
    def _create_images_direct(self, prompt, output_path, num_images, timeout_minutes):
        """Direct approach with improved request handling."""
        # First visit the create page to get any necessary tokens
        logging.info("Visiting Bing Create page...")
        create_page = self.session.get("https://www.bing.com/images/create", timeout=30)
        create_page.raise_for_status()
        
        # Submit the generation request
        logging.info("Submitting generation request...")
        form_data = {
            'q': prompt,
            'rt': '3',
            'FORM': 'GENCRE'
        }
        
        # Add any CSRF tokens if found
        csrf_match = re.search(r'name="[^"]*token[^"]*"\s+value="([^"]+)"', create_page.text, re.IGNORECASE)
        if csrf_match:
            form_data['token'] = csrf_match.group(1)
            logging.info("Added CSRF token to request")
        
        response = self.session.post("https://www.bing.com/images/create", 
                                   data=form_data, 
                                   allow_redirects=True,
                                   timeout=30)
        response.raise_for_status()
        
        # Try to extract request ID from multiple sources
        request_id = self._extract_request_id_enhanced(response)
        if not request_id:
            raise Exception("Could not extract request ID from response")
        
        logging.info(f"Got request ID: {request_id}")
        
        # Enhanced polling with multiple URL formats
        return self._poll_with_fallbacks(request_id, output_path, num_images, timeout_minutes)
    
    def _create_images_browser_sim(self, prompt, output_path, num_images, timeout_minutes):
        """Browser simulation approach with step-by-step navigation."""
        # Step 1: Visit main Bing page
        self.session.get("https://www.bing.com", timeout=30)
        
        # Step 2: Visit create page and wait
        time.sleep(1)
        create_response = self.session.get("https://www.bing.com/images/create", timeout=30)
        
        # Step 3: Submit with enhanced form data
        form_data = {
            'q': prompt,
            'qs': 'n',
            'form': 'GENCRE',
            'rt': '3'
        }
        
        # Add referrer header
        headers = {
            'Referer': 'https://www.bing.com/images/create',
            'Origin': 'https://www.bing.com'
        }
        
        response = self.session.post("https://www.bing.com/images/create",
                                   data=form_data,
                                   headers=headers,
                                   allow_redirects=True,
                                   timeout=30)
        
        request_id = self._extract_request_id_enhanced(response)
        if not request_id:
            raise Exception("Browser simulation: Could not extract request ID")
        
        return self._poll_with_fallbacks(request_id, output_path, num_images, timeout_minutes)
    
    def _create_images_simple(self, prompt, output_path, num_images):
        """Simplified approach that looks for immediate results."""
        # Try a simple search-like approach
        search_url = f"https://www.bing.com/images/create?q={requests.utils.quote(prompt)}&rt=3&FORM=GENCRE"
        
        response = self.session.get(search_url, timeout=30)
        response.raise_for_status()
        
        # Look for images directly in the response
        image_urls = self._extract_image_urls_enhanced(response.text)
        
        if not image_urls:
            # Try to find a request ID and poll briefly
            request_id = self._extract_request_id_enhanced(response)
            if request_id:
                return self._poll_with_fallbacks(request_id, output_path, num_images, 2)  # 2 minute timeout
            else:
                raise Exception("Simple approach: No images found and no request ID")
        
        # Download found images
        return self._download_images(image_urls[:num_images], output_path)
    
    def _extract_request_id_enhanced(self, response):
        """Enhanced request ID extraction with multiple patterns."""
        html = response.text
        url = response.url
        
        # Check URL first
        if '/async/results/' in url:
            match = re.search(r'/async/results/([a-f0-9-]{36})', url)
            if match:
                return match.group(1)
        
        # Multiple regex patterns for HTML content
        patterns = [
            r'id="([a-f0-9-]{36})"',
            r'"id":"([a-f0-9-]{36})"',
            r'requestId["\']?\s*[:=]\s*["\']?([a-f0-9-]{36})["\']?',
            r'data-rid="([a-f0-9-]{36})"',
            r'rid=([a-f0-9-]{36})',
            r'/async/results/([a-f0-9-]{36})',
            r'polling[^"]*([a-f0-9-]{36})',
            r'create[^"]*([a-f0-9-]{36})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
    
    def _poll_with_fallbacks(self, request_id, output_path, num_images, timeout_minutes):
        """Enhanced polling with multiple URL formats and better timeout handling."""
        max_attempts = (timeout_minutes * 60) // 3  # Poll every 3 seconds
        
        # Multiple polling URL formats to try
        poll_urls = [
            f"https://www.bing.com/images/create/async/results/{request_id}?q=",
            f"https://www.bing.com/images/create/async/results/{request_id}",
            f"https://www.bing.com/images/create/{request_id}",
        ]
        
        for attempt in range(max_attempts):
            for poll_url in poll_urls:
                try:
                    response = self.session.get(poll_url, timeout=10)
                    if response.status_code == 200:
                        image_urls = self._extract_image_urls_enhanced(response.text)
                        if image_urls:
                            logging.info(f"Found {len(image_urls)} images after {attempt + 1} attempts")
                            return self._download_images(image_urls[:num_images], output_path)
                except Exception as e:
                    logging.debug(f"Polling attempt {attempt + 1} failed for {poll_url}: {e}")
                    continue
            
            if attempt % 10 == 0:  # Log every 30 seconds
                logging.info(f"Still polling... attempt {attempt + 1}/{max_attempts}")
            
            time.sleep(3)
        
        raise Exception(f"Timeout after {timeout_minutes} minutes waiting for images")
    
    def _extract_image_urls_enhanced(self, html_content):
        """Enhanced image URL extraction with multiple patterns."""
        patterns = [
            # Standard image tags
            r'src="([^"]*th\.bing\.com[^"]*)"',
            r'data-src="([^"]*th\.bing\.com[^"]*)"',
            
            # JSON embedded URLs
            r'"murl":"([^"]*)"',
            r'"turl":"([^"]*)"',
            r'"imageUrl":"([^"]*)"',
            
            # Direct Bing image URLs
            r'https://th\.bing\.com/th/id/[^"\s]*',
            r'https://tse\d*\.mm\.bing\.net/[^"\s]*',
            
            # Generated image specific patterns
            r'src="([^"]*OIG\.[^"]*)"',
            r'data-src="([^"]*OIG\.[^"]*)"',
        ]
        
        all_urls = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Clean up the URL
                url = match.replace('\\/', '/').replace('\\', '')
                
                # Ensure it's a valid image URL
                if any(domain in url for domain in ['th.bing.com', 'tse', 'mm.bing.net']) or 'OIG.' in url:
                    # Ensure HTTPS
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif not url.startswith('http'):
                        url = 'https://' + url.lstrip('/')
                    
                    # Convert to high resolution
                    url = self._enhance_image_url(url)
                    all_urls.add(url)
        
        return list(all_urls)
    
    def _enhance_image_url(self, url):
        """Convert image URL to higher resolution."""
        # Replace resolution parameters
        url = re.sub(r'&w=\d+', '&w=1024', url)
        url = re.sub(r'&h=\d+', '&h=1024', url)
        
        # Add resolution if not present
        if 'th?id=' in url and '&w=' not in url:
            url += '&w=1024&h=1024'
        
        return url
    
    def _download_images(self, urls, output_path):
        """Download images from URLs."""
        downloaded_files = []
        
        for i, url in enumerate(urls):
            try:
                filename = f"bing_generated_{int(time.time())}_{i+1}.jpg"
                filepath = output_path / filename
                
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                downloaded_files.append(str(filepath))
                logging.info(f"Downloaded image {i+1}: {filename}")
                
            except Exception as e:
                logging.error(f"Failed to download image from {url}: {e}")
                continue
        
        return downloaded_files
