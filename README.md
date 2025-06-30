# Samsung Frame TV Art Generator

Automatically generate and upload seasonal art to your Samsung Frame TV using AI image generation. This application creates beautiful, seasonally-themed artwork using Bing Image Creator and uploads it directly to your Frame TV via Samsung's SmartThings API.

## ✨ Features

- **🎨 AI-Generated Art**: Uses Bing Image Creator (DALL-E 3) for high-quality image generation
- **🌅 Seasonal Themes**: Automatically adjusts art themes based on current month
- **📺 Frame TV Integration**: Direct upload to Samsung Frame TV via SmartThings API
- **🖼️ Optimized Processing**: Resizes and enhances images for 4K Frame TV display
- **⏰ Scheduled Automation**: Monthly batch execution with Windows Task Scheduler
- **📁 Archive Management**: Automatically archives old images
- **🔧 Configurable**: Customizable prompts and themes

## 📋 Requirements

- **Python 3.8+**
- **Samsung Frame TV (2022+ models recommended)**
- **Microsoft Account** (for Bing Image Creator)
- **Samsung SmartThings Account**
- **Windows 10/11** (for batch scheduling)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frame_tv_art_generator
pip install -r requirements.txt
```

### 2. Get Setup Instructions

```bash
python main.py --setup
```

### 3. Configure Authentication

#### Bing Image Creator Cookie:
1. Go to [Bing Image Creator](https://www.bing.com/create)
2. Sign in with your Microsoft account
3. Open Developer Tools (F12)
4. Go to Application/Storage → Cookies → bing.com
5. Copy the `_U` cookie value

#### Samsung Frame TV API:
1. Go to [SmartThings Developer](https://smartthings.developer.samsung.com/)
2. Create developer account
3. Go to [Personal Access Tokens](https://account.smartthings.com/tokens)
4. Generate token with scopes: `r:devices:*`, `w:devices:*`, `x:devices:*`
5. Find your Frame TV device ID via SmartThings app
6. Edit `config/samsung_config.json` with your credentials

### 4. Test Your Setup

```bash
python main.py --test --cookie "YOUR_BING_COOKIE"
```

### 5. Run Generation

```bash
python main.py --run --cookie "YOUR_BING_COOKIE"
```

## 📖 Usage

### Command Line Options

```bash
# Test all components
python main.py --test --cookie "YOUR_COOKIE"

# Generate 5 images and upload to Frame TV
python main.py --run --cookie "YOUR_COOKIE"

# Generate 10 images
python main.py --run --cookie "YOUR_COOKIE" --num-images 10

# Test mode (generate but don't upload)
python main.py --run --test-mode --cookie "YOUR_COOKIE"

# Show setup instructions
python main.py --setup
```

### Batch Scheduling

For monthly automation:

1. Edit `run_monthly.bat` and set your Bing cookie
2. Use Windows Task Scheduler to run monthly:
   - Open Task Scheduler
   - Create Basic Task
   - Set to run monthly on 1st day
   - Set action to start `run_monthly.bat`

## 🗂️ Project Structure

```
frame_tv_art_generator/
├── config/
│   ├── base_prompt.txt         # Your art style preferences
│   ├── seasonal_themes.json    # Monthly theme definitions
│   └── samsung_config.json     # Frame TV API credentials
├── src/
│   ├── prompt_builder.py       # Combines prompts with seasonal themes
│   ├── bing_generator.py       # Bing Image Creator interface
│   ├── image_processor.py      # Resizes for Frame TV (4K)
│   ├── frame_tv_api.py        # Samsung SmartThings integration
│   └── scheduler.py           # Main orchestration logic
├── images/
│   ├── generated/             # Raw AI-generated images
│   ├── processed/             # Frame TV-ready images
│   └── archive/              # Historical backups
├── logs/                     # Application logs
├── main.py                   # Main application entry point
├── run_monthly.bat          # Windows batch script for scheduling
└── requirements.txt         # Python dependencies
```

## ⚙️ Configuration

### Art Style Preferences

Edit `config/base_prompt.txt` to customize the base art style:

```
Create a high-quality artistic image suitable for display as wall art...
Focus on creating artwork that would be appropriate for a modern home gallery...
```

### Seasonal Themes

Modify `config/seasonal_themes.json` to adjust monthly themes:

```json
{
    "january": [
        "winter landscapes with snow-covered trees",
        "cozy cabin scenes with warm lighting"
    ],
    "october": [
        "halloween-themed elegant autumn scenes",
        "spooky but sophisticated forest landscapes"
    ]
}
```

### Frame TV Settings

Update `config/samsung_config.json`:

```json
{
    "personal_access_token": "YOUR_TOKEN_HERE",
    "device_id": "YOUR_DEVICE_ID_HERE",
    "image_upload_settings": {
        "resolution": {
            "width": 3840,
            "height": 2160
        }
    }
}
```

## 🎯 How It Works

1. **Prompt Generation**: Combines your base preferences with current month's seasonal themes
2. **Image Creation**: Sends prompts to Bing Image Creator for AI generation
3. **Image Processing**: Downloads, resizes to 4K (3840×2160), and optimizes for Frame TV
4. **Frame TV Upload**: Uploads processed images via Samsung SmartThings API
5. **Archive Management**: Moves old images to archive folders

## 🔧 Troubleshooting

### Common Issues

**"Authentication cookie required"**
- Get fresh `_U` cookie from Bing Create
- Cookies expire periodically

**"Frame TV device not found"**
- Verify device ID in SmartThings app
- Ensure Frame TV is online and connected

**"Failed to generate images"**
- Check Bing Create daily limits (15 fast generations)
- Verify Microsoft account is in good standing

**"Upload failed"**
- Confirm SmartThings token permissions
- Check Frame TV firmware is up to date

### Logs

Check `logs/` directory for detailed error messages and execution history.

## 📊 Image Specifications

- **Resolution**: 3840×2160 (4K)
- **Format**: JPEG
- **Quality**: 95% (configurable)
- **Optimization**: Enhanced contrast, saturation, and sharpening for TV display

## 🔒 Security Notes

- Store authentication credentials securely
- Bing cookies should be kept private
- SmartThings tokens have device access permissions
- Consider using environment variables for production deployments

## 🤝 Contributing

This is a personal automation project, but improvements are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is for personal use. Respect Samsung's API terms of service and Microsoft's Bing usage policies.

## 🙏 Acknowledgments

- Samsung SmartThings API for Frame TV integration
- Microsoft Bing Image Creator for AI-generated artwork
- Pillow library for image processing

---

**Enjoy your automatically refreshed Frame TV art gallery! 🖼️✨**
