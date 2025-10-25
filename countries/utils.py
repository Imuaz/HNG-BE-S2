import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from typing import List, Tuple
from django.conf import settings
from .models import Country

class ImageGenerator:
    """Generates summary images for country data"""
    
    IMAGE_WIDTH = 800
    IMAGE_HEIGHT = 600
    BACKGROUND_COLOR = (255, 255, 255)  # White
    TEXT_COLOR = (0, 0, 0)  # Black
    TITLE_COLOR = (25, 25, 112)  # Midnight blue
    
    @staticmethod
    def get_cache_dir() -> str:
        """Get or create cache directory"""
        cache_dir = os.path.join(settings.BASE_DIR, 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    @staticmethod
    def get_image_path() -> str:
        """Get full path to summary image"""
        return os.path.join(ImageGenerator.get_cache_dir(), 'summary.png')
    
    @classmethod
    def generate_summary_image(cls) -> str:
        """
        Generate summary image with country statistics.
        
        Returns:
            Path to generated image
        """
        # Create blank image
        image = Image.new('RGB', (cls.IMAGE_WIDTH, cls.IMAGE_HEIGHT), cls.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)
        
        # Try to use a nice font, fallback to default
        try:
            title_font = ImageFont.truetype("arial.ttf", 40)
            text_font = ImageFont.truetype("arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Get data
        total_countries = Country.objects.count()
        top_countries = Country.objects.filter(
            estimated_gdp__isnull=False
        ).order_by('-estimated_gdp')[:5]
        
        last_refresh = Country.objects.first()
        refresh_time = last_refresh.last_refreshed_at if last_refresh else datetime.now()
        
        # Draw title
        title = "Country Data Summary"
        draw.text((50, 50), title, fill=cls.TITLE_COLOR, font=title_font)
        
        # Draw total countries
        draw.text((50, 120), f"Total Countries: {total_countries}", fill=cls.TEXT_COLOR, font=text_font)
        
        # Draw top 5 countries
        draw.text((50, 170), "Top 5 by GDP:", fill=cls.TITLE_COLOR, font=text_font)
        
        y_position = 210
        for i, country in enumerate(top_countries, 1):
            gdp_str = f"${country.estimated_gdp:,.2f}" if country.estimated_gdp else "N/A"
            text = f"{i}. {country.name}: {gdp_str}"
            draw.text((70, y_position), text, fill=cls.TEXT_COLOR, font=text_font)
            y_position += 40
        
        # Draw timestamp
        time_str = refresh_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        draw.text((50, 500), f"Last refreshed: {time_str}", fill=cls.TEXT_COLOR, font=text_font)
        
        # Save image
        image_path = cls.get_image_path()
        image.save(image_path)
        
        return image_path