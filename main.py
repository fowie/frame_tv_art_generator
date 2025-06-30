#!/usr/bin/env python3
"""
Frame TV Art Generator - Main Application
Automatically generates seasonal art for Samsung Frame TV using Bing Image Creator
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scheduler import FrameTVArtScheduler

def main():
    parser = argparse.ArgumentParser(
        description="Generate and upload seasonal art to Samsung Frame TV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --test                     # Test all components
  python main.py --run --cookie "COOKIE"   # Run full generation
  python main.py --run --test-mode         # Run without uploading to TV
  python main.py --setup                   # Show setup instructions
        """
    )
    
    parser.add_argument(
        '--run', 
        action='store_true',
        help='Run the monthly art generation process'
    )
    
    parser.add_argument(
        '--test', 
        action='store_true',
        help='Test all system components'
    )
    
    parser.add_argument(
        '--setup', 
        action='store_true',
        help='Show setup instructions'
    )
    
    parser.add_argument(
        '--cookie',
        type=str,
        help='Bing authentication cookie (_U value)'
    )
    
    parser.add_argument(
        '--num-images',
        type=int,
        default=5,
        help='Number of images to generate (default: 5)'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run generation but skip Frame TV upload'
    )
    
    parser.add_argument(
        '--config-dir',
        type=str,
        default='config',
        help='Path to configuration directory (default: config)'
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any([args.run, args.test, args.setup]):
        parser.print_help()
        return
    
    try:
        # Initialize scheduler
        scheduler = FrameTVArtScheduler(
            config_dir=args.config_dir,
            working_dir="."
        )
        
        if args.setup:
            show_setup_instructions()
            return
        
        if args.test:
            print("🧪 Testing system components...")
            test_results = scheduler.test_components(bing_cookie=args.cookie)
            print_test_results(test_results)
            return
        
        if args.run:
            if not args.cookie and not args.test_mode:
                print("❌ Error: Bing authentication cookie is required for image generation")
                print("   Use --cookie option or --test-mode to skip generation")
                return
            
            print(f"🎨 Starting art generation...")
            print(f"   Images to generate: {args.num_images}")
            print(f"   Test mode: {args.test_mode}")
            
            results = scheduler.run_monthly_generation(
                num_images=args.num_images,
                bing_cookie=args.cookie,
                test_mode=args.test_mode
            )
            
            print_generation_results(results)
    
    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

def show_setup_instructions():
    """Display detailed setup instructions."""
    print("""
🖼️  Samsung Frame TV Art Generator Setup
==========================================

This application requires configuration for two services:

1️⃣  BING IMAGE CREATOR SETUP
-----------------------------
• Go to https://www.bing.com/create
• Sign in with your Microsoft account
• Open browser Developer Tools (F12)
• Go to Application/Storage → Cookies → bing.com
• Find cookie named '_U' and copy its value
• Use this value with --cookie option

2️⃣  SAMSUNG FRAME TV API SETUP
-------------------------------
• Go to https://smartthings.developer.samsung.com/
• Create developer account with Samsung
• Go to https://account.smartthings.com/tokens
• Generate token with scopes: r:devices:*, w:devices:*, x:devices:*
• Install SmartThings app and connect your Frame TV
• Find your Frame TV device ID

• Edit config/samsung_config.json:
  - Replace "YOUR_SMARTTHINGS_TOKEN_HERE" with your token
  - Replace "YOUR_FRAME_TV_DEVICE_ID_HERE" with device ID

3️⃣  OPTIONAL: CUSTOMIZE PREFERENCES
------------------------------------
• Edit config/base_prompt.txt for your art style preferences
• Modify config/seasonal_themes.json for custom monthly themes

4️⃣  TEST YOUR SETUP
--------------------
python main.py --test --cookie "YOUR_BING_COOKIE"

5️⃣  RUN GENERATION
-------------------
python main.py --run --cookie "YOUR_BING_COOKIE"

For questions or issues, check the logs/ directory for detailed error messages.
    """)

def print_test_results(test_results):
    """Print formatted test results."""
    print(f"\n📊 Component Test Results")
    print("=" * 40)
    
    for component, result in test_results['individual_results'].items():
        status = "✅" if result['success'] else "❌"
        component_name = component.replace('_', ' ').title()
        
        print(f"{status} {component_name}")
        
        if result['success']:
            if 'message' in result:
                print(f"   {result['message']}")
            elif 'info' in result:
                for key, value in result['info'].items():
                    print(f"   {key}: {value}")
            elif 'sample_prompt' in result:
                print(f"   Sample: {result['sample_prompt']}")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
        print()
    
    overall_status = "🎉 READY" if test_results['overall_success'] else "⚠️  NEEDS SETUP"
    print(f"Overall Status: {overall_status}")
    
    if not test_results['overall_success']:
        print("\n💡 Run 'python main.py --setup' for configuration help")

def print_generation_results(results):
    """Print formatted generation results."""
    print(f"\n🎨 Art Generation Results")
    print("=" * 40)
    print(f"Month: {results['month'].title()}")
    print(f"Duration: {results.get('duration_seconds', 0):.1f} seconds")
    print(f"Test Mode: {results['test_mode']}")
    
    if results.get('overall_success'):
        print(f"✅ SUCCESS - Generated {results.get('final_image_count', 0)} images")
    else:
        print(f"❌ FAILED - {results.get('error', 'Unknown error')}")
    
    print(f"\n📝 Step Details:")
    for step_name, step_result in results.get('steps', {}).items():
        status = "✅" if step_result.get('success') else "❌"
        step_display = step_name.replace('_', ' ').title()
        print(f"  {status} {step_display}")
        
        if step_name == 'generation' and 'images_generated' in step_result:
            print(f"      Generated: {step_result['images_generated']}/{step_result['images_requested']} images")
        elif step_name == 'upload' and 'uploads_successful' in step_result:
            print(f"      Uploaded: {step_result['uploads_successful']}/{step_result['uploads_total']} images")
        elif step_name == 'archive' and 'archived_count' in step_result:
            print(f"      Archived: {step_result['archived_count']} old images")
        
        if not step_result.get('success') and 'error' in step_result:
            print(f"      Error: {step_result['error']}")
    
    print(f"\n📁 Check these directories:")
    print(f"   📸 Generated images: images/generated/")
    print(f"   🖼️  Processed images: images/processed/")
    print(f"   📋 Logs: logs/")

if __name__ == "__main__":
    exit_code = main()
    if exit_code:
        sys.exit(exit_code)
