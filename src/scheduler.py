import logging
import json
import datetime
from pathlib import Path
import shutil
import time
from typing import List, Dict, Any

from prompt_builder import PromptBuilder
from bing_generator import BingImageCreator
from image_processor import ImageProcessor
from frame_tv_api import SamsungFrameTVAPI

class FrameTVArtScheduler:
    def __init__(self, config_dir="../config", working_dir="../"):
        """
        Initialize the Frame TV Art Scheduler.
        
        Args:
            config_dir (str): Path to configuration directory
            working_dir (str): Working directory for the application
        """
        self.config_dir = Path(config_dir)
        self.working_dir = Path(working_dir)
        self.images_dir = self.working_dir / "images"
        self.logs_dir = self.working_dir / "logs"
        
        # Create directories if they don't exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self._setup_logging()
        
        # Initialize components
        self.prompt_builder = PromptBuilder(config_dir)
        self.image_processor = ImageProcessor()
        
        # These will be initialized when needed (require credentials)
        self.bing_generator = None
        self.frame_tv_api = None
        
        logging.info("Frame TV Art Scheduler initialized")
    
    def _setup_logging(self):
        """Set up logging configuration."""
        log_file = self.logs_dir / f"art_generation_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def run_monthly_generation(self, num_images=5, bing_cookie=None, test_mode=False):
        """
        Run the complete monthly art generation process.
        
        Args:
            num_images (int): Number of images to generate
            bing_cookie (str): Bing authentication cookie
            test_mode (bool): If True, skip Frame TV upload
        
        Returns:
            dict: Generation results
        """
        start_time = datetime.datetime.now()
        current_month = self.prompt_builder.get_current_month_key()
        
        logging.info(f"Starting monthly art generation for {current_month}")
        logging.info(f"Target: {num_images} images, Test mode: {test_mode}")
        
        results = {
            'start_time': start_time.isoformat(),
            'month': current_month,
            'num_images_requested': num_images,
            'test_mode': test_mode,
            'steps': {}
        }
        
        try:
            # Step 1: Generate prompts
            logging.info("Step 1: Generating prompts...")
            prompts = self.prompt_builder.generate_multiple_prompts(num_images, current_month)
            results['steps']['prompts'] = {
                'success': True,
                'count': len(prompts),
                'prompts': prompts
            }
            logging.info(f"Generated {len(prompts)} prompts")
            
            # Step 2: Generate images with Bing
            logging.info("Step 2: Generating images...")
            if not bing_cookie:
                raise ValueError("Bing authentication cookie is required")
            
            self.bing_generator = BingImageCreator(auth_cookie=bing_cookie)
            generated_images = []
            
            for i, prompt in enumerate(prompts):
                try:
                    logging.info(f"Generating image {i+1}/{len(prompts)}")
                    logging.info(f"Full prompt: {prompt}")
                    # Create monthly subdirectory for organization
                    monthly_output_dir = self.images_dir / "generated" / current_month
                    images = self.bing_generator.create_images(
                        prompt,
                        output_dir=str(monthly_output_dir),
                        num_images=1
                    )
                    generated_images.extend(images)
                    time.sleep(2)  # Be nice to Bing's servers
                except Exception as e:
                    logging.error(f"Failed to generate image {i+1}: {e}")
                    continue
            
            results['steps']['generation'] = {
                'success': len(generated_images) > 0,
                'images_generated': len(generated_images),
                'images_requested': num_images,
                'image_paths': generated_images
            }
            logging.info(f"Generated {len(generated_images)} images")
            
            if not generated_images:
                raise Exception("No images were generated successfully")
            
            # Step 3: Process images for Frame TV
            logging.info("Step 3: Processing images for Frame TV...")
            processed_images = []
            
            for image_path in generated_images:
                try:
                    processed_path = self.image_processor.process_image(
                        image_path,
                        output_path=None,
                        enhance=True
                    )
                    processed_images.append(processed_path)
                except Exception as e:
                    logging.error(f"Failed to process image {image_path}: {e}")
                    continue
            
            results['steps']['processing'] = {
                'success': len(processed_images) > 0,
                'images_processed': len(processed_images),
                'processed_paths': processed_images
            }
            logging.info(f"Processed {len(processed_images)} images")
            
            # Step 4: Upload to Frame TV (unless in test mode)
            if not test_mode and processed_images:
                logging.info("Step 4: Uploading to Frame TV...")
                try:
                    self.frame_tv_api = SamsungFrameTVAPI(
                        str(self.config_dir / "samsung_config.json")
                    )
                    
                    # Test connection first
                    connection_test = self.frame_tv_api.test_connection()
                    if not connection_test['success']:
                        raise Exception(f"Frame TV connection failed: {connection_test['error']}")
                    
                    # Upload images
                    upload_result = self.frame_tv_api.upload_batch(
                        processed_images,
                        name_prefix=f"Monthly_{current_month.title()}"
                    )
                    
                    results['steps']['upload'] = {
                        'success': upload_result['successful_uploads'] > 0,
                        'uploads_successful': upload_result['successful_uploads'],
                        'uploads_total': upload_result['total_images'],
                        'upload_details': upload_result
                    }
                    
                    # Enable art mode
                    if upload_result['successful_uploads'] > 0:
                        art_mode_result = self.frame_tv_api.set_art_mode(True)
                        results['steps']['art_mode'] = art_mode_result
                    
                    logging.info(f"Uploaded {upload_result['successful_uploads']} images to Frame TV")
                    
                except Exception as e:
                    logging.error(f"Frame TV upload failed: {e}")
                    results['steps']['upload'] = {
                        'success': False,
                        'error': str(e)
                    }
            else:
                logging.info("Step 4: Skipped (test mode or no processed images)")
                results['steps']['upload'] = {
                    'success': True,
                    'skipped': True,
                    'reason': 'test_mode' if test_mode else 'no_processed_images'
                }
            
            # Step 5: Archive old images
            logging.info("Step 5: Archiving old images...")
            archive_result = self._archive_old_images()
            results['steps']['archive'] = archive_result
            
            # Final results
            end_time = datetime.datetime.now()
            duration = end_time - start_time
            
            results.update({
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'overall_success': all(
                    step.get('success', False) 
                    for step in results['steps'].values()
                ),
                'final_image_count': len(processed_images)
            })
            
            logging.info(f"Monthly generation completed in {duration}")
            logging.info(f"Final result: {results['overall_success']}")
            
            return results
            
        except Exception as e:
            logging.error(f"Monthly generation failed: {e}")
            results['error'] = str(e)
            results['overall_success'] = False
            return results
    
    def _archive_old_images(self):
        """Archive old generated and processed images, respecting monthly folder structure."""
        try:
            archive_dir = self.images_dir / "archive" / datetime.datetime.now().strftime("%Y-%m")
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            archived_count = 0
            
            # Archive generated images older than 2 days (check both root and monthly folders)
            generated_dir = self.images_dir / "generated"
            if generated_dir.exists():
                cutoff_time = datetime.datetime.now() - datetime.timedelta(days=2)
                
                # Archive from root generated folder (legacy images)
                for image_file in generated_dir.glob("*.jpg"):
                    if datetime.datetime.fromtimestamp(image_file.stat().st_mtime) < cutoff_time:
                        archive_path = archive_dir / f"generated_{image_file.name}"
                        shutil.move(str(image_file), str(archive_path))
                        archived_count += 1
                
                # Archive from monthly subfolders (new structure)
                for month_dir in generated_dir.iterdir():
                    if month_dir.is_dir() and month_dir.name in [
                        'january', 'february', 'march', 'april', 'may', 'june',
                        'july', 'august', 'september', 'october', 'november', 'december'
                    ]:
                        for image_file in month_dir.glob("*.jpg"):
                            if datetime.datetime.fromtimestamp(image_file.stat().st_mtime) < cutoff_time:
                                # Create month-specific archive subdirectory
                                month_archive_dir = archive_dir / f"generated_{month_dir.name}"
                                month_archive_dir.mkdir(parents=True, exist_ok=True)
                                archive_path = month_archive_dir / image_file.name
                                shutil.move(str(image_file), str(archive_path))
                                archived_count += 1
            
            # Archive processed images older than 7 days (check both root and monthly folders)
            processed_dir = self.images_dir / "processed"
            if processed_dir.exists():
                cutoff_time = datetime.datetime.now() - datetime.timedelta(days=7)
                
                # Archive from root processed folder (legacy images)
                for image_file in processed_dir.glob("*.jpg"):
                    if datetime.datetime.fromtimestamp(image_file.stat().st_mtime) < cutoff_time:
                        archive_path = archive_dir / f"processed_{image_file.name}"
                        shutil.move(str(image_file), str(archive_path))
                        archived_count += 1
                
                # Archive from monthly subfolders (new structure)
                for month_dir in processed_dir.iterdir():
                    if month_dir.is_dir() and month_dir.name in [
                        'january', 'february', 'march', 'april', 'may', 'june',
                        'july', 'august', 'september', 'october', 'november', 'december'
                    ]:
                        for image_file in month_dir.glob("*.jpg"):
                            if datetime.datetime.fromtimestamp(image_file.stat().st_mtime) < cutoff_time:
                                # Create month-specific archive subdirectory
                                month_archive_dir = archive_dir / f"processed_{month_dir.name}"
                                month_archive_dir.mkdir(parents=True, exist_ok=True)
                                archive_path = month_archive_dir / image_file.name
                                shutil.move(str(image_file), str(archive_path))
                                archived_count += 1
            
            logging.info(f"Archived {archived_count} old images")
            
            return {
                'success': True,
                'archived_count': archived_count,
                'archive_location': str(archive_dir)
            }
            
        except Exception as e:
            logging.error(f"Archiving failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_components(self, bing_cookie=None):
        """
        Test all components of the system.
        
        Args:
            bing_cookie (str): Bing authentication cookie for testing
        
        Returns:
            dict: Test results for each component
        """
        logging.info("Running component tests...")
        
        test_results = {}
        
        # Test 1: Prompt Builder
        try:
            test_prompt = self.prompt_builder.build_prompt()
            test_results['prompt_builder'] = {
                'success': True,
                'sample_prompt': test_prompt[:100] + "..."
            }
        except Exception as e:
            test_results['prompt_builder'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 2: Bing Generator (if cookie provided)
        if bing_cookie:
            try:
                self.bing_generator = BingImageCreator(auth_cookie=bing_cookie)
                test_results['bing_generator'] = {
                    'success': True,
                    'message': 'Authentication configured'
                }
            except Exception as e:
                test_results['bing_generator'] = {
                    'success': False,
                    'error': str(e)
                }
        else:
            test_results['bing_generator'] = {
                'success': False,
                'error': 'No authentication cookie provided'
            }
        
        # Test 3: Frame TV API
        try:
            self.frame_tv_api = SamsungFrameTVAPI(str(self.config_dir / "samsung_config.json"))
            connection_result = self.frame_tv_api.test_connection()
            test_results['frame_tv_api'] = connection_result
        except Exception as e:
            test_results['frame_tv_api'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 4: Image Processor
        try:
            processor_info = {
                'target_resolution': f"{self.image_processor.target_width}x{self.image_processor.target_height}",
                'quality': self.image_processor.quality
            }
            test_results['image_processor'] = {
                'success': True,
                'info': processor_info
            }
        except Exception as e:
            test_results['image_processor'] = {
                'success': False,
                'error': str(e)
            }
        
        overall_success = all(result.get('success', False) for result in test_results.values())
        
        logging.info(f"Component tests completed. Overall success: {overall_success}")
        
        return {
            'overall_success': overall_success,
            'individual_results': test_results
        }

if __name__ == "__main__":
    # Test the scheduler
    logging.basicConfig(level=logging.INFO)
    
    scheduler = FrameTVArtScheduler()
    
    print("Testing components...")
    test_results = scheduler.test_components()
    
    for component, result in test_results['individual_results'].items():
        status = "✓" if result['success'] else "✗"
        print(f"{status} {component}: {result.get('message', result.get('error', 'OK'))}")
    
    print(f"\nOverall system ready: {test_results['overall_success']}")
    
    if not test_results['overall_success']:
        print("\nTo run the full generation process, you'll need to:")
        print("1. Set up Bing authentication cookie")
        print("2. Configure Samsung Frame TV API credentials")
        print("3. Run: scheduler.run_monthly_generation(bing_cookie='YOUR_COOKIE')")
