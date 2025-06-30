import requests
import json
import base64
from pathlib import Path
import logging
import mimetypes

class SamsungFrameTVAPI:
    def __init__(self, config_file="config/samsung_config.json"):
        """
        Initialize Samsung Frame TV API client.
        
        Args:
            config_file (str): Path to Samsung configuration file
        """
        self.config = self._load_config(config_file)
        self.base_url = self.config["smartthings_api_url"]
        self.token = self.config["personal_access_token"]
        self.device_id = self.config["device_id"]
        
        # Set up session with authentication
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _load_config(self, config_file):
        """Load configuration from JSON file."""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Samsung configuration file not found: {config_file}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ["personal_access_token", "device_id"]
        for field in required_fields:
            if not config.get(field) or config[field] == f"YOUR_{field.upper()}_HERE":
                raise ValueError(f"Please set '{field}' in {config_file}")
        
        return config
    
    def test_connection(self):
        """
        Test connection to Samsung SmartThings API and Frame TV device.
        
        Returns:
            dict: Connection status and device information
        """
        try:
            # Test basic API connectivity
            devices_url = f"{self.base_url}/devices"
            response = self.session.get(devices_url)
            response.raise_for_status()
            
            # Check if our specific device exists
            devices = response.json().get('items', [])
            frame_tv = None
            
            for device in devices:
                if device['deviceId'] == self.device_id:
                    frame_tv = device
                    break
            
            if not frame_tv:
                return {
                    'success': False,
                    'error': f'Frame TV device not found: {self.device_id}',
                    'available_devices': [d['deviceId'] for d in devices]
                }
            
            # Get device status
            status_url = f"{self.base_url}/devices/{self.device_id}/status"
            status_response = self.session.get(status_url)
            status_response.raise_for_status()
            
            return {
                'success': True,
                'device_info': {
                    'name': frame_tv.get('label', 'Unknown'),
                    'type': frame_tv.get('deviceTypeName', 'Unknown'),
                    'online': frame_tv.get('online', False)
                },
                'status': status_response.json()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API request failed: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {e}'
            }
    
    def upload_art(self, image_path, art_name=None):
        """
        Copy processed art to shared folder for Frame TV.
        
        Note: Samsung Frame TVs don't support direct API uploads of custom art.
        Instead, this method copies images to a designated folder that can be
        accessed through Samsung's SmartView app or other methods.
        
        Args:
            image_path (str): Path to image file
            art_name (str): Optional name for the art piece
        
        Returns:
            dict: Copy result
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if art_name is None:
            art_name = image_path.stem
        
        logging.info(f"Preparing art for Frame TV: {art_name}")
        
        try:
            # Create Frame TV ready folder
            frame_tv_folder = Path("frame_tv_ready")
            frame_tv_folder.mkdir(exist_ok=True)
            
            # Copy the processed image to Frame TV ready folder
            import shutil
            destination = frame_tv_folder / f"{art_name}.jpg"
            shutil.copy2(image_path, destination)
            
            logging.info(f"Art copied to Frame TV ready folder: {destination}")
            
            # Try to enable art mode on the TV
            art_mode_result = self.set_art_mode(True)
            
            return {
                'success': True,
                'art_name': art_name,
                'file_path': str(destination),
                'art_mode_enabled': art_mode_result.get('success', False),
                'note': 'Image copied to frame_tv_ready/ folder. Use Samsung SmartView app to upload to TV.'
            }
            
        except Exception as e:
            logging.error(f"Failed to prepare art: {e}")
            return {
                'success': False,
                'error': f'Art preparation failed: {e}'
            }
    
    def set_art_mode(self, enabled=True):
        """
        Enable or disable Art Mode on the Frame TV.
        
        Args:
            enabled (bool): Whether to enable Art Mode
        
        Returns:
            dict: Command result
        """
        try:
            command_url = f"{self.base_url}/devices/{self.device_id}/commands"
            
            payload = {
                "commands": [{
                    "component": "main",
                    "capability": "custom.artMode",
                    "command": "setArtMode",
                    "arguments": [{"enabled": enabled}]
                }]
            }
            
            response = self.session.post(command_url, json=payload)
            response.raise_for_status()
            
            logging.info(f"Art Mode {'enabled' if enabled else 'disabled'}")
            return {
                'success': True,
                'art_mode_enabled': enabled,
                'response': response.json()
            }
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to set art mode: {e}")
            return {
                'success': False,
                'error': f'Art mode command failed: {e}'
            }
    
    def get_art_list(self):
        """
        Get list of art currently on the Frame TV.
        
        Returns:
            dict: List of art pieces
        """
        try:
            status_url = f"{self.base_url}/devices/{self.device_id}/status"
            response = self.session.get(status_url)
            response.raise_for_status()
            
            status = response.json()
            
            # Extract art-related information from device status
            # Note: The exact structure may vary depending on Frame TV model
            art_info = {}
            components = status.get('components', {})
            
            if 'main' in components:
                main_component = components['main']
                # Look for art-related capabilities
                for capability_name, capability_data in main_component.items():
                    if 'art' in capability_name.lower():
                        art_info[capability_name] = capability_data
            
            return {
                'success': True,
                'art_info': art_info,
                'full_status': status
            }
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to get art list: {e}")
            return {
                'success': False,
                'error': f'Get art list failed: {e}'
            }
    
    def upload_batch(self, image_paths, name_prefix="GeneratedArt"):
        """
        Upload multiple images to Frame TV.
        
        Args:
            image_paths (list): List of image file paths
            name_prefix (str): Prefix for art names
        
        Returns:
            dict: Batch upload results
        """
        results = []
        successful_uploads = 0
        
        for i, image_path in enumerate(image_paths):
            art_name = f"{name_prefix}_{i+1:02d}"
            
            try:
                result = self.upload_art(image_path, art_name)
                results.append(result)
                
                if result['success']:
                    successful_uploads += 1
                
            except Exception as e:
                logging.error(f"Failed to upload {image_path}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'image_path': str(image_path)
                })
        
        logging.info(f"Batch upload completed: {successful_uploads}/{len(image_paths)} successful")
        
        return {
            'total_images': len(image_paths),
            'successful_uploads': successful_uploads,
            'results': results
        }
    
    def get_setup_instructions(self):
        """
        Return instructions for setting up Samsung Frame TV API access.
        
        Returns:
            str: Setup instructions
        """
        return """
        Samsung Frame TV API Setup Instructions:
        
        1. Create Samsung Developer Account:
           - Go to https://smartthings.developer.samsung.com/
           - Sign up or log in with your Samsung account
           - Accept the developer terms
        
        2. Generate Personal Access Token:
           - Go to https://account.smartthings.com/tokens
           - Click "Generate new token"
           - Select these scopes: r:devices:*, w:devices:*, x:devices:*
           - Copy the generated token
        
        3. Find Your Frame TV Device ID:
           - Install SmartThings app on your phone
           - Ensure your Frame TV is connected and visible
           - Use the API to list devices or check the app
        
        4. Update Configuration:
           - Edit config/samsung_config.json
           - Replace "YOUR_SMARTTHINGS_TOKEN_HERE" with your token
           - Replace "YOUR_FRAME_TV_DEVICE_ID_HERE" with your device ID
        
        5. Test Connection:
           - Run frame_tv_api.test_connection() to verify setup
        
        Note: Make sure your Frame TV is connected to the same network
        and SmartThings account as your developer account.
        """

if __name__ == "__main__":
    # Test the Frame TV API
    logging.basicConfig(level=logging.INFO)
    
    try:
        api = SamsungFrameTVAPI("../config/samsung_config.json")
        
        # Test connection
        result = api.test_connection()
        if result['success']:
            print("✓ Frame TV connection successful!")
            print(f"Device: {result['device_info']['name']}")
            print(f"Online: {result['device_info']['online']}")
        else:
            print("✗ Frame TV connection failed:")
            print(result['error'])
            
    except Exception as e:
        print(f"Setup required: {e}")
        api = SamsungFrameTVAPI.__new__(SamsungFrameTVAPI)
        print(api.get_setup_instructions())
