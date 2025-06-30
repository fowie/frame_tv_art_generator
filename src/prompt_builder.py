import json
import random
import datetime
from pathlib import Path

class PromptBuilder:
    def __init__(self, config_dir="config"):
        self.config_dir = Path(config_dir)
        self.base_prompt = self._load_base_prompt()
        self.seasonal_themes = self._load_seasonal_themes()
    
    def _load_base_prompt(self):
        """Load the base prompt from the text file."""
        prompt_file = self.config_dir / "base_prompt.txt"
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Base prompt file not found: {prompt_file}")
    
    def _load_seasonal_themes(self):
        """Load seasonal themes from JSON file."""
        themes_file = self.config_dir / "seasonal_themes.json"
        try:
            with open(themes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Seasonal themes file not found: {themes_file}")
    
    def get_current_month_key(self):
        """Get the current month as a lowercase string."""
        return datetime.datetime.now().strftime("%B").lower()
    
    def get_seasonal_theme(self, month=None):
        """Get a random seasonal theme for the specified month (or current month)."""
        if month is None:
            month = self.get_current_month_key()
        
        if month not in self.seasonal_themes:
            raise ValueError(f"No themes found for month: {month}")
        
        themes = self.seasonal_themes[month]
        return random.choice(themes)
    
    def build_prompt(self, month=None, custom_addition=""):
        """Build a complete prompt combining base prompt, seasonal theme, and optional custom addition."""
        seasonal_theme = self.get_seasonal_theme(month)
        
        # Put seasonal theme at the beginning of the prompt
        full_prompt = f"Generate a beautiful wall art painting of {seasonal_theme}. {self.base_prompt}"
        
        # Add custom addition if provided
        if custom_addition:
            full_prompt += f" {custom_addition}"
        
        return full_prompt
    
    def generate_multiple_prompts(self, count=5, month=None):
        """Generate multiple unique prompts for the same month with random theme selection."""
        prompts = []
        month_key = month or self.get_current_month_key()
        
        if month_key not in self.seasonal_themes:
            raise ValueError(f"No themes found for month: {month_key}")
        
        themes = self.seasonal_themes[month_key].copy()  # Copy to avoid modifying original
        
        # Shuffle the themes for random selection
        random.shuffle(themes)
        
        # Generate prompts using shuffled themes
        for i in range(count):
            # If we need more prompts than available themes, reshuffle and continue
            if i >= len(themes):
                random.shuffle(themes)
            
            theme = themes[i % len(themes)]
            prompt = f"Generate a beautiful wall art painting of {theme}. {self.base_prompt}"
            prompts.append(prompt)
        
        return prompts

if __name__ == "__main__":
    # Test the prompt builder
    try:
        builder = PromptBuilder("../config")
        
        print("Current month:", builder.get_current_month_key())
        print("\nSample prompt:")
        print(builder.build_prompt())
        
        print("\n5 prompts for current month:")
        prompts = builder.generate_multiple_prompts(5)
        for i, prompt in enumerate(prompts, 1):
            print(f"\n{i}. {prompt}")
            
    except Exception as e:
        print(f"Error: {e}")
