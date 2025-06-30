import requests
import re
import time
import os
from pathlib import Path
from urllib.parse import urljoin
import logging

class BingImageCreator:
    def __init__(self, auth_cookie=None):
        """
        Initialize Bing Image Creator.
        
        Args:
            auth_cookie (str): Your _U cookie value from bing.com (required for authentication)
        """
        self.auth_cookie = auth_cookie
        self.session = requests.Session()
        
        # Set up headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        if self.auth_cookie:
            self.session.cookies.set('_U', self.auth_cookie, domain='.bing.com')
    
    def create_images(self, prompt, output_dir="images/generated", num_images=4):
        """
        Generate images using Bing Image Creator.
        
        Args:
            prompt (str): Text prompt for image generation
            output_dir (str): Directory to save generated images
            num_images (int): Number of images to generate (max 4 per request)
        
        Returns:
            list: Paths to downloaded images
        """
        if not self.auth_cookie:
            raise ValueError("Authentication cookie (_U) is required. Please set it in the constructor.")
        
        logging.info(f"Generating images for prompt: {prompt[:100]}...")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Try the modern approach first
            return self._create_images_modern(prompt, output_path, num_images)
        except Exception as e:
            logging.warning(f"Modern approach failed: {e}. Trying legacy approach...")
            try:
                return self._create_images_legacy(prompt, output_path, num_images)
            except Exception as e2:
                logging.error(f"Both approaches failed. Modern: {e}, Legacy: {e2}")
                raise Exception(f"Failed to generate images with both methods. Last error: {e2}")
    
    def _create_images_modern(self, prompt, output_path, num_images):
        """Modern approach using direct API calls."""
        # First, get the page to extract any necessary tokens
        create_url = "https://www.bing.com/images/create"
        response = self.session.get(create_url)
        response.raise_for_status()
        
        # Submit the prompt with modern parameters
        data = {
            'q': prompt,
            'rt': '3',  # Updated request type
            'FORM': 'GENCRE'
        }
        
        response = self.session.post(create_url, data=data, allow_redirects=True)
        response.raise_for_status()
        
        # Check if we're redirected to a results page
        if 'images/create/async/results/' in response.url:
            request_id = response.url.split('/')[-1].split('?')[0]
            logging.info(f"Request submitted with ID from redirect: {request_id}")
        else:
            # Extract request ID from response
            request_id = self._extract_request_id(response.text)
            if not request_id:
                # Try to find it in current URL or response headers
                if hasattr(response, 'history') and response.history:
                    for hist_resp in response.history:
                        if 'images/create/async/results/' in hist_resp.url:
                            request_id = hist_resp.url.split('/')[-1].split('?')[0]
                            break
                
                if not request_id:
                    raise Exception("Failed to extract request ID from Bing response")
            
            logging.info(f"Request submitted with ID: {request_id}")
        
        # Poll for completion
        image_urls = self._poll_for_completion(request_id)
        
        # Download the images
        downloaded_files = []
        for i, url in enumerate(image_urls[:num_images]):
            filename = f"bing_generated_{int(time.time())}_{i+1}.jpg"
            filepath = output_path / filename
            
            if self._download_image(url, filepath):
                downloaded_files.append(str(filepath))
                logging.info(f"Downloaded image {i+1}: {filename}")
        
        return downloaded_files
    
    def _create_images_legacy(self, prompt, output_path, num_images):
        """Legacy approach for older Bing interface."""
        # Step 1: Submit the prompt
        create_url = "https://www.bing.com/images/create"
        data = {
            'q': prompt,
            'rt': '4',  # Request type
            'FORM': 'GENILP'
        }
        
        response = self.session.post(create_url, data=data, allow_redirects=True)
        response.raise_for_status()
        
        # Extract the request ID from the response
        request_id = self._extract_request_id(response.text)
        if not request_id:
            raise Exception("Failed to extract request ID from Bing response")
        
        logging.info(f"Request submitted with ID: {request_id}")
        
        # Step 2: Poll for completion
        image_urls = self._poll_for_completion(request_id)
        
        # Step 3: Download the images
        downloaded_files = []
        for i, url in enumerate(image_urls[:num_images]):
            filename = f"bing_generated_{int(time.time())}_{i+1}.jpg"
            filepath = output_path / filename
            
            if self._download_image(url, filepath):
                downloaded_files.append(str(filepath))
                logging.info(f"Downloaded image {i+1}: {filename}")
        
        return downloaded_files
    
    def _extract_request_id(self, html_content):
        """Extract the request ID from the HTML response."""
        # Try multiple patterns to find the request ID
        patterns = [
            r'id="([a-f0-9-]{36})"',  # Original pattern
            r'"id":"([a-f0-9-]{36})"',  # JSON format
            r'requestId["\']?\s*[:=]\s*["\']?([a-f0-9-]{36})["\']?',  # Request ID variable
            r'data-rid="([a-f0-9-]{36})"',  # Data attribute
            r'rid=([a-f0-9-]{36})',  # URL parameter
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                return matches[0]
        
        # If no UUID found, try to extract from URL redirects
        if '/images/create/' in html_content:
            url_patterns = [
                r'/images/create/async/results/([a-f0-9-]{36})',
                r'images/create.*?([a-f0-9-]{36})',
            ]
            for pattern in url_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    return matches[0]
        
        return None
    
    def _poll_for_completion(self, request_id, max_attempts=30, delay=2):
        """Poll Bing for image generation completion."""
        poll_url = f"https://www.bing.com/images/create/async/results/{request_id}?q="
        
        for attempt in range(max_attempts):
            logging.info(f"Polling attempt {attempt + 1}/{max_attempts}")
            
            response = self.session.get(poll_url)
            
            if response.status_code == 200:
                # Check if images are ready
                image_urls = self._extract_image_urls(response.text)
                if image_urls:
                    logging.info(f"Images ready! Found {len(image_urls)} URLs")
                    return image_urls
            
            time.sleep(delay)
        
        raise Exception("Timeout waiting for image generation to complete")
    
    def _extract_image_urls(self, html_content):
        """Extract image URLs from the HTML response."""
        # Try multiple patterns to find image URLs
        patterns = [
            r'src="([^"]*th\?id=[^"]*)"',  # Original pattern
            r'data-src="([^"]*th\?id=[^"]*)"',  # Lazy loading
            r'"murl":"([^"]*)"',  # Media URL in JSON
            r'"turl":"([^"]*)"',  # Thumbnail URL in JSON
            r'https://th\.bing\.com/th/id/[^"\\]*',  # Direct Bing image URLs
        ]
        
        all_urls = []
        for pattern in patterns:
            urls = re.findall(pattern, html_content)
            all_urls.extend(urls)
        
        # Clean up URLs and get full resolution versions
        clean_urls = []
        seen_urls = set()
        
        for url in all_urls:
            if 'th.bing.com' in url or 'th?id=' in url:
                # Clean up the URL
                clean_url = url.replace('\\/', '/').replace('\\', '')
                
                # Ensure it starts with https://
                if not clean_url.startswith('http'):
                    if clean_url.startswith('//'):
                        clean_url = 'https:' + clean_url
                    elif clean_url.startswith('/'):
                        clean_url = 'https://th.bing.com' + clean_url
                
                # Convert to full resolution
                if '&w=' in clean_url:
                    clean_url = re.sub(r'&w=\d+', '&w=1024', clean_url)
                if '&h=' in clean_url:
                    clean_url = re.sub(r'&h=\d+', '&h=1024', clean_url)
                
                # Add resolution parameters if not present
                if 'th?id=' in clean_url and '&w=' not in clean_url:
                    clean_url += '&w=1024&h=1024'
                
                # Avoid duplicates
                if clean_url not in seen_urls:
                    clean_urls.append(clean_url)
                    seen_urls.add(clean_url)
        
        return clean_urls
    
    def _download_image(self, url, filepath):
        """Download an image from a URL to a local file."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            logging.error(f"Failed to download image from {url}: {e}")
            return False
    
    def get_auth_instructions(self):
        """Return instructions for getting the authentication cookie."""
        return """
        To use Bing Image Creator, you need to get your authentication cookie:
        
        1. Go to https://www.bing.com/create in your browser
        2. Sign in with your Microsoft account
        3. Open Developer Tools (F12)
        4. Go to Application/Storage tab -> Cookies -> https://www.bing.com
        5. Find the cookie named '_U' and copy its value
        6. Use this value when initializing BingImageCreator
        
        Example:
        generator = BingImageCreator(auth_cookie="YOUR_U_COOKIE_VALUE_HERE")
        """

if __name__ == "__main__":
    # Test the Bing Image Creator
    logging.basicConfig(level=logging.INFO)
    
    generator = BingImageCreator()
    print(generator.get_auth_instructions())
    
    # Uncomment below to test with actual cookie
    # generator = BingImageCreator(auth_cookie="YOUR_COOKIE_HERE")
    # images = generator.create_images("A beautiful sunset landscape", num_images=2)
    # print(f"Generated images: {images}")
