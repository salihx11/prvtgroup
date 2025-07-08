from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import textwrap
from datetime import datetime


# Ensure temp directory exists
os.makedirs("temp", exist_ok=True)

# Load fonts (you'll need to provide these font files)
try:
    title_font = ImageFont.truetype("fonts/Roboto-Bold.ttf", 32)
    text_font = ImageFont.truetype("fonts/Roboto-Regular.ttf", 24)
    small_font = ImageFont.truetype("fonts/Roboto-Light.ttf", 18)
except:
    # Fallback to default fonts if custom fonts not found
    title_font = ImageFont.load_default()
    text_font = ImageFont.load_default()
    small_font = ImageFont.load_default()

def add_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im

def generate_rank_card(username: str, xp: int, rank: int, level: int, avatar_path: str = None):
    """Generate a professional rank card with progress bar"""
    width, height = 800, 250
    bg_color = (36, 36, 36)
    primary_color = (0, 150, 255)
    secondary_color = (200, 200, 200)
    
    # Create base image
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Add gradient background
    for y in range(height):
        r = bg_color[0] + int((y / height) * 20)
        g = bg_color[1] + int((y / height) * 20)
        b = bg_color[2] + int((y / height) * 20)
        draw.line((0, y, width, y), fill=(r, g, b))
    
    # Add avatar if provided
    if avatar_path and os.path.exists(avatar_path):
        try:
            avatar = Image.open(avatar_path).convert("RGB")
            avatar = avatar.resize((150, 150))
            avatar = add_corners(avatar, 25)
            
            # Create border
            border = Image.new('RGB', (160, 160), primary_color)
            border.paste(avatar, (5, 5), avatar)
            image.paste(border, (30, (height - 160) // 2))
        except Exception as e:
            print(f"Error loading avatar: {e}")
    
    # Calculate positions
    text_x = 200 if avatar_path and os.path.exists(avatar_path) else 30
    
    # Add username
    draw.text((text_x, 30), username, fill=(255, 255, 255), font=title_font)
    
    # Add level
    level_text = f"LEVEL {level}"
    level_size = draw.textlength(level_text, font=text_font)
    draw.text((width - level_size - 40, 30), level_text, fill=primary_color, font=text_font)
    
    # Add rank
    rank_text = f"#{rank}"
    rank_size = draw.textlength(rank_text, font=text_font)
    draw.text((width - rank_size - 40, 70), rank_text, fill=secondary_color, font=text_font)
    
    # XP progress bar
    xp_needed = level * 1000
    progress = min(xp / xp_needed, 1.0)
    
    # Progress bar background
    bar_y = 120
    draw.rounded_rectangle((text_x, bar_y, width - 40, bar_y + 20), 
                          radius=10, fill=(50, 50, 50))
    
    # Progress bar fill
    bar_width = int((width - 40 - text_x) * progress)
    draw.rounded_rectangle((text_x, bar_y, text_x + bar_width, bar_y + 20), 
                          radius=10, fill=primary_color)
    
    # XP text
    xp_text = f"{xp:,}/{xp_needed:,} XP ({progress*100:.1f}%)"
    xp_text_size = draw.textlength(xp_text, font=small_font)
    xp_text_x = text_x + ((width - 40 - text_x) - xp_text_size) // 2
    draw.text((xp_text_x, bar_y - 30), xp_text, fill=secondary_color, font=small_font)
    
    # Add decorative elements
    draw.line((text_x, 170, width - 40, 170), fill=(60, 60, 60), width=2)
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    draw.text((width - 150, height - 30), timestamp, fill=(100, 100, 100), font=small_font)
    
    # Save and return path
    path = f"temp/rank_{username.replace(' ', '_')}.png"
    image.save(path, quality=95)
    return path

def generate_leaderboard(top_users: list, title: str = "🏆 LEADERBOARD"):
    """Generate a sleek leaderboard image"""
    width, height = 800, 100 + len(top_users) * 70
    bg_color = (28, 28, 28)
    primary_color = (0, 150, 255)
    secondary_color = (200, 200, 200)
    
    # Create base image
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Add gradient background
    for y in range(height):
        r = bg_color[0] + int((y / height) * 20)
        g = bg_color[1] + int((y / height) * 20)
        b = bg_color[2] + int((y / height) * 20)
        draw.line((0, y, width, y), fill=(r, g, b))
    
    # Add title
    title_size = draw.textlength(title, font=title_font)
    draw.text(((width - title_size) // 2, 30), title, fill=primary_color, font=title_font)
    
    # Add decorative line under title
    draw.line((50, 80, width - 50, 80), fill=(60, 60, 60), width=2)
    
    # Add users
    y_position = 100
    for i, (username, xp, level) in enumerate(top_users, 1):
        # Rank number
        rank_color = (255, 215, 0) if i == 1 else (192, 192, 192) if i == 2 else (205, 127, 50) if i == 3 else secondary_color
        draw.text((60, y_position + 10), f"{i}.", fill=rank_color, font=text_font)
        
        # Username
        draw.text((120, y_position), username, fill=(240, 240, 240), font=text_font)
        
        # Level
        level_text = f"Lvl {level}"
        level_size = draw.textlength(level_text, font=small_font)
        draw.text((120, y_position + 35), level_text, fill=secondary_color, font=small_font)
        
        # XP
        xp_text = f"{xp:,} XP"
        xp_size = draw.textlength(xp_text, font=text_font)
        draw.text((width - xp_size - 60, y_position + 15), xp_text, fill=primary_color, font=text_font)
        
        # Separator line
        if i < len(top_users):
            draw.line((60, y_position + 60, width - 60, y_position + 60), fill=(50, 50, 50), width=1)
        
        y_position += 70
    
    # Add footer
    draw.line((50, height - 50, width - 50, height - 50), fill=(60, 60, 60), width=2)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    draw.text((width - 200, height - 35), timestamp, fill=(100, 100, 100), font=small_font)
    
    # Save and return path
    path = "temp/leaderboard.png"
    image.save(path, quality=95)
    return path

def generate_warning_card(username: str, reason: str, warns: int, max_warns: int):
    """Generate a professional warning card"""
    width, height = 700, 300
    bg_color = (40, 0, 0)
    accent_color = (255, 100, 100)
    text_color = (240, 240, 240)
    
    # Create base image
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Add warning icon
    draw.ellipse((30, 30, 100, 100), outline=accent_color, width=5)
    draw.line((65, 50, 65, 80), fill=accent_color, width=5)
    draw.ellipse((60, 85, 70, 95), fill=accent_color)
    
    # Add title
    draw.text((120, 40), "WARNING ISSUED", fill=accent_color, font=title_font)
    
    # Add username
    draw.text((120, 90), f"User: {username}", fill=text_color, font=text_font)
    
    # Add reason (with text wrapping)
    reason_lines = textwrap.wrap(reason, width=40)
    for i, line in enumerate(reason_lines):
        draw.text((120, 140 + i * 30), line, fill=text_color, font=text_font)
    
    # Add warn counter
    warn_text = f"Warnings: {warns}/{max_warns}"
    warn_size = draw.textlength(warn_text, font=text_font)
    draw.text((width - warn_size - 40, height - 70), warn_text, fill=accent_color, font=text_font)
    
    # Add decorative border
    draw.rounded_rectangle((10, 10, width - 10, height - 10), radius=15, outline=accent_color, width=3)
    
    # Save and return path
    path = f"temp/warn_{username.replace(' ', '_')}.png"
    image.save(path, quality=95)
    return path

def generate_ban_notice(username: str, reason: str, admin: str):
    """Generate a professional ban notice"""
    width, height = 700, 350
    bg_color = (50, 0, 0)
    accent_color = (255, 50, 50)
    text_color = (240, 240, 240)
    
    # Create base image
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Add ban icon
    draw.line((50, 50, 150, 150), fill=accent_color, width=10)
    draw.line((150, 50, 50, 150), fill=accent_color, width=10)
    
    # Add title
    draw.text((180, 60), "ACCOUNT BANNED", fill=accent_color, font=title_font)
    
    # Add username
    draw.text((180, 120), f"User: {username}", fill=text_color, font=text_font)
    
    # Add reason
    reason_lines = textwrap.wrap(reason, width=40)
    draw.text((180, 170), "Reason:", fill=text_color, font=text_font)
    for i, line in enumerate(reason_lines):
        draw.text((180, 200 + i * 30), line, fill=text_color, font=text_font)
    
    # Add admin info
    admin_text = f"Banned by: {admin}"
    draw.text((180, height - 80), admin_text, fill=text_color, font=text_font)
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    draw.text((width - 250, height - 50), timestamp, fill=(100, 100, 100), font=small_font)
    
    # Add decorative border
    draw.rounded_rectangle((10, 10, width - 10, height - 10), radius=15, outline=accent_color, width=3)
    
    # Save and return path
    path = f"temp/ban_{username.replace(' ', '_')}.png"
    image.save(path, quality=95)
    return path