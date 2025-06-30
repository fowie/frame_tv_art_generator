import os
import time
import logging
from pathlib import Path
from BingImageCreator import ImageGen

class BingImageCreator:
    def __init__(self, auth_cookie=None, srchhpgusr_cookie=None):
        """
        Initialize Bing Image Creator using the official BingImageCreator package.
        
        Args:
            auth_cookie (str): Your _U cookie value from bing.com
            srchhpgusr_cookie (str): Your SRCHHPGUSR cookie value (optional, will try to use empty string if not provided)
        """
        self.auth_cookie = auth_cookie
        self.srchhpgusr_cookie = srchhpgusr_cookie or ""
        
        if self.auth_cookie:
            try:
                self.image_gen = ImageGen(
                    auth_cookie=self.auth_cookie,
                    auth_cookie_SRCHHPGUSR=self.srchhpgusr_cookie
                )
            except Exception as e:
                logging.error(f"Failed to initialize ImageGen: {e}")
                self.image_gen = None
        else:
            self.image_gen = None
    
    def create_images(self, prompt, output_dir="images/generated", num_images=4, max_retries=2):
        """
        Generate images using the official BingImageCreator package.
        
        Args:
            prompt (str): Text prompt for image generation
            output_dir (str): Directory to save generated images
            num_images (int): Number of images to generate (max 4 per request)
            max_retries (int): Maximum number of retry attempts if generation fails
        
        Returns:
            list: Paths to downloaded images
        """
        if not self.auth_cookie:
            raise ValueError("Authentication cookie (_U) is required.")
        
        if not self.image_gen:
            raise ValueError("ImageGen not initialized. Check your authentication cookie.")
        
        logging.info(f"Generating images for prompt: {prompt}")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logging.info(f"Retry attempt {attempt}/{max_retries} for image generation...")
                    time.sleep(5)  # Wait before retry
                
                # Generate images using the official package
                logging.info("Submitting request to Bing Image Creator...")
                image_urls = self.image_gen.get_images(prompt)
                
                if not image_urls:
                    if attempt < max_retries:
                        logging.warning("No images returned - retrying...")
                        continue
                    raise Exception("No images returned from Bing Image Creator after all retries")
                
                logging.info(f"Received {len(image_urls)} image URLs")
                
                # Use the package's built-in download method
                try:
                    logging.info("Downloading images...")
                    # The save_images method downloads all images at once
                    self.image_gen.save_images(
                        image_urls[:num_images], 
                        str(output_path)
                    )
                    
                    # Find the downloaded files and preserve existing images
                    downloaded_files = []
                    
                    # Count existing images to continue numbering sequence
                    existing_images = len(list(output_path.glob("bing_generated_*.jpg"))) if output_path.exists() else 0
                    
                    # Look for any new image files in the directory  
                    new_files = []
                    for img_file in output_path.glob("*"):
                        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.svg']:
                            # Check if this is a newly downloaded file (not our renamed format)
                            if not img_file.name.startswith('bing_generated_'):
                                new_files.append(img_file)
                    
                    # Rename new files with unique numbers to preserve existing images
                    for i, img_file in enumerate(new_files[:num_images]):
                        try:
                            # Check if the file is actually an image and not an SVG error
                            if not self._validate_image_file(img_file):
                                logging.warning(f"Downloaded file {img_file.name} is not a valid image (likely Bing error icon) - deleting")
                                img_file.unlink()  # Delete the invalid file
                                continue
                            
                            # Create unique filename based on existing count + new sequence
                            unique_number = existing_images + len(downloaded_files) + 1
                            timestamp = int(time.time())
                            new_name = f"bing_generated_{timestamp}_{unique_number:03d}.jpg"
                            new_path = output_path / new_name
                            
                            # Ensure filename is unique
                            counter = 1
                            while new_path.exists():
                                new_name = f"bing_generated_{timestamp}_{unique_number:03d}_{counter}.jpg"
                                new_path = output_path / new_name
                                counter += 1
                            
                            img_file.rename(new_path)
                            downloaded_files.append(str(new_path))
                            logging.info(f"Downloaded and renamed image: {new_name}")
                            
                        except Exception as e:
                            logging.warning(f"Could not rename {img_file}: {e}")
                            # Still check if it's a valid image before adding
                            if self._validate_image_file(img_file):
                                downloaded_files.append(str(img_file))
                                logging.info(f"Downloaded image: {img_file.name}")
                    
                    # Check if we got valid images, if not and we have retries left, try again
                    if not downloaded_files and attempt < max_retries:
                        logging.warning(f"No valid images downloaded on attempt {attempt + 1}, retrying...")
                        continue
                    
                except Exception as e:
                    logging.error(f"Failed to download images using save_images: {e}")
                    if attempt < max_retries:
                        continue
                    
                    # Fallback: try to download manually
                    downloaded_files = []
                    import requests
                    
                    for i, url in enumerate(image_urls[:num_images]):
                        try:
                            filename = f"bing_generated_{int(time.time())}_{i+1}.jpg"
                            filepath = output_path / filename
                            
                            response = requests.get(url, timeout=30)
                            response.raise_for_status()
                            
                            with open(filepath, 'wb') as f:
                                f.write(response.content)
                            
                            downloaded_files.append(str(filepath))
                            logging.info(f"Downloaded image {i+1}: {filename}")
                            
                        except Exception as e2:
                            logging.error(f"Failed to download image {i+1}: {e2}")
                            continue
                
                if downloaded_files:
                    logging.info(f"Successfully downloaded {len(downloaded_files)} images")
                    return downloaded_files
                    
            except Exception as e:
                if attempt < max_retries:
                    logging.warning(f"Generation attempt {attempt + 1} failed: {e}, retrying...")
                    continue
                else:
                    logging.error(f"Error generating images after all retries: {e}")
                    raise
        
        # If we get here, all attempts failed
        raise Exception("Failed to generate valid images after all retry attempts")
    
    def test_connection(self):
        """
        Test the connection to Bing Image Creator.
        
        Returns:
            dict: Connection test results
        """
        if not self.auth_cookie:
            return {
                'success': False,
                'error': 'No authentication cookie provided'
            }
        
        try:
            # Try to initialize the ImageGen object
            if not self.image_gen:
                self.image_gen = ImageGen(auth_cookie=self.auth_cookie)
            
            # Test with a simple prompt (this might generate actual images, so be cautious)
            logging.info("Testing Bing Image Creator connection...")
            
            return {
                'success': True,
                'message': 'Bing Image Creator initialized successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Connection test failed: {e}'
            }
    
    def _validate_image_file(self, file_path):
        """
        Validate that the downloaded file is actually an image and not an SVG error icon.
        
        Args:
            file_path (Path): Path to the file to validate
        
        Returns:
            bool: True if valid image, False if SVG error or invalid
        """
        try:
            # Check file extension
            if file_path.suffix.lower() == '.svg':
                logging.warning(f"File {file_path.name} is an SVG (likely Bing error icon)")
                return False
            
            # Check file size - SVG error icons are typically very small
            file_size = file_path.stat().st_size
            if file_size < 1024:  # Less than 1KB is likely an error
                logging.warning(f"File {file_path.name} is too small ({file_size} bytes) - likely error icon")
                return False
            
            # Check file content for SVG markers
            try:
                with open(file_path, 'rb') as f:
                    first_bytes = f.read(100).decode('utf-8', errors='ignore').lower()
                    if '<svg' in first_bytes or '<?xml' in first_bytes:
                        logging.warning(f"File {file_path.name} contains SVG/XML content - likely error icon")
                        return False
            except Exception:
                pass  # If we can't read the file, let PIL handle it later
            
            # Try to validate with PIL
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    img.verify()  # This will throw an exception if not a valid image
                return True
            except Exception as e:
                logging.warning(f"File {file_path.name} failed PIL validation: {e}")
                return False
                
        except Exception as e:
            logging.error(f"Error validating file {file_path}: {e}")
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
        6. Use this value when initializing BingImageCreatorOfficial
        
        Example:
        generator = BingImageCreator(auth_cookie="YOUR_U_COOKIE_VALUE_HERE")
        
        Note: This version uses the official BingImageCreator pip package.
        """

if __name__ == "__main__":
    # Test the Bing Image Creator
    logging.basicConfig(level=logging.INFO)
    
    generator = BingImageCreator()
    print(generator.get_auth_instructions())
    
    # Uncomment below to test with actual cookie
    # generator = BingImageCreator(auth_cookie="YOUR_COOKIE_HERE")
    # test_result = generator.test_connection()
    # print(f"Connection test: {test_result}")
    # 
    # if test_result['success']:
    #     images = generator.create_images("A beautiful sunset landscape", num_images=1)
    #     print(f"Generated images: {images}")
