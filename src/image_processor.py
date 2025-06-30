from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
import logging
import os

class ImageProcessor:
    def __init__(self, target_resolution=(3840, 2160), quality=85):
        """
        Initialize the image processor for Frame TV optimization.
        
        Args:
            target_resolution (tuple): Target resolution (width, height) for Frame TV
            quality (int): JPEG compression quality (1-100)
        """
        self.target_width, self.target_height = target_resolution
        self.quality = quality
        self.aspect_ratio = self.target_width / self.target_height
    
    def process_image(self, input_path, output_path=None, enhance=True):
        """
        Process a single image for Frame TV display.
        
        Args:
            input_path (str): Path to input image
            output_path (str): Path for output image (optional)
            enhance (bool): Whether to apply Frame TV optimizations
        
        Returns:
            str: Path to processed image
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input image not found: {input_path}")
        
        # Generate output path if not provided
        if output_path is None:
            # Check if input is in a monthly subfolder (e.g., images/generated/june/)
            if input_path.parent.name in ['january', 'february', 'march', 'april', 'may', 'june', 
                                         'july', 'august', 'september', 'october', 'november', 'december']:
                # Create corresponding monthly folder in processed directory
                month_folder = input_path.parent.name
                output_dir = input_path.parent.parent.parent / "processed" / month_folder
            else:
                # Default behavior for images not in monthly folders
                output_dir = input_path.parent.parent / "processed"
            
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"processed_{input_path.name}"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"Processing image: {input_path.name}")
        
        try:
            # Open and process the image
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to target resolution with proper aspect ratio handling
                processed_img = self._resize_with_aspect_ratio(img)
                
                # Apply Frame TV optimizations if requested
                if enhance:
                    processed_img = self._enhance_for_frame_tv(processed_img)
                
                # Save the processed image
                processed_img.save(
                    output_path,
                    'JPEG',
                    quality=self.quality,
                    optimize=True,
                    progressive=True
                )
                
                logging.info(f"Processed image saved: {output_path}")
                return str(output_path)
                
        except Exception as e:
            logging.error(f"Error processing image {input_path}: {e}")
            raise
    
    def _resize_with_aspect_ratio(self, img):
        """
        Resize image to target resolution while maintaining quality.
        Uses smart cropping to fill the Frame TV screen optimally.
        """
        original_width, original_height = img.size
        original_aspect = original_width / original_height
        
        if abs(original_aspect - self.aspect_ratio) < 0.01:
            # Aspect ratios are very close, just resize
            return img.resize((self.target_width, self.target_height), Image.Resampling.LANCZOS)
        
        # Calculate scaling to fill the target resolution
        scale_width = self.target_width / original_width
        scale_height = self.target_height / original_height
        scale = max(scale_width, scale_height)  # Scale to fill, not fit
        
        # Calculate new dimensions after scaling
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # Resize with high-quality resampling
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Center crop to exact target resolution
        left = (new_width - self.target_width) // 2
        top = (new_height - self.target_height) // 2
        right = left + self.target_width
        bottom = top + self.target_height
        
        return img_resized.crop((left, top, right, bottom))
    
    def _enhance_for_frame_tv(self, img):
        """
        Apply enhancements optimized for Frame TV display.
        """
        # Slight saturation boost for TV display
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.1)
        
        # Mild contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.05)
        
        # Subtle sharpening for large screen viewing
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        
        return img
    
    def process_batch(self, input_dir, output_dir=None, file_pattern="*.jpg"):
        """
        Process multiple images in a directory.
        
        Args:
            input_dir (str): Directory containing input images
            output_dir (str): Directory for processed images (optional)
            file_pattern (str): Pattern to match input files
        
        Returns:
            list: Paths to processed images
        """
        input_path = Path(input_dir)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_path}")
        
        # Set up output directory
        if output_dir is None:
            output_path = input_path.parent / "processed"
        else:
            output_path = Path(output_dir)
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all matching files
        input_files = list(input_path.glob(file_pattern))
        if not input_files:
            logging.warning(f"No files found matching pattern: {file_pattern}")
            return []
        
        processed_files = []
        for input_file in input_files:
            try:
                output_file = output_path / f"processed_{input_file.name}"
                processed_path = self.process_image(input_file, output_file)
                processed_files.append(processed_path)
            except Exception as e:
                logging.error(f"Failed to process {input_file}: {e}")
                continue
        
        logging.info(f"Processed {len(processed_files)} out of {len(input_files)} images")
        return processed_files
    
    def get_image_info(self, image_path):
        """
        Get information about an image file.
        
        Args:
            image_path (str): Path to image file
        
        Returns:
            dict: Image information
        """
        try:
            with Image.open(image_path) as img:
                return {
                    'path': str(image_path),
                    'size': img.size,
                    'mode': img.mode,
                    'format': img.format,
                    'file_size': os.path.getsize(image_path),
                    'aspect_ratio': img.size[0] / img.size[1]
                }
        except Exception as e:
            logging.error(f"Error getting image info for {image_path}: {e}")
            return None

if __name__ == "__main__":
    # Test the image processor
    logging.basicConfig(level=logging.INFO)
    
    processor = ImageProcessor()
    
    print(f"Target resolution: {processor.target_width}x{processor.target_height}")
    print(f"Target aspect ratio: {processor.aspect_ratio:.3f}")
    
    # Example usage (uncomment to test with actual images)
    # processed = processor.process_batch("../images/generated")
    # print(f"Processed images: {processed}")
