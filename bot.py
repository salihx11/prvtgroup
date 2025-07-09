import datetime
import random
import os
import asyncio
import sqlite3
import requests
import time
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# ======================
# DATABASE SETUP
# ======================

def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  first_name TEXT, 
                  last_name TEXT, 
                  username TEXT,
                  country TEXT,
                  join_date TEXT)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS xp
                 (user_id INTEGER,
                  chat_id INTEGER,
                  xp INTEGER DEFAULT 0,
                  level INTEGER DEFAULT 1,
                  last_active TEXT,
                  PRIMARY KEY (user_id, chat_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS warns
                 (warn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  chat_id INTEGER,
                  reason TEXT,
                  admin_id INTEGER,
                  timestamp TEXT)''')
    
    conn.commit()
    conn.close()

def add_user(user_id, first_name, last_name="", username="", country="Unknown"):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users 
                 (user_id, first_name, last_name, username, country, join_date)
                 VALUES (?, ?, ?, ?, ?, datetime('now'))''',
              (user_id, first_name, last_name, username, country))
    conn.commit()
    conn.close()

def add_xp(user_id, chat_id, first_name, xp_amount):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    c.execute('''INSERT OR IGNORE INTO users 
                 (user_id, first_name, join_date)
                 VALUES (?, ?, datetime('now'))''',
              (user_id, first_name))
    
    c.execute('''INSERT INTO xp (user_id, chat_id, xp, last_active)
                 VALUES (?, ?, ?, datetime('now'))
                 ON CONFLICT(user_id, chat_id) 
                 DO UPDATE SET 
                 xp = xp + excluded.xp,
                 level = (xp + excluded.xp) / 1000 + 1,
                 last_active = excluded.last_active''',
              (user_id, chat_id, xp_amount))
    
    conn.commit()
    conn.close()

def get_rank(user_id, chat_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    c.execute('''SELECT xp, level FROM xp 
                 WHERE user_id = ? AND chat_id = ?''',
              (user_id, chat_id))
    result = c.fetchone()
    
    if not result:
        return None
        
    xp, level = result
    
    c.execute('''SELECT COUNT(*) FROM xp 
                 WHERE chat_id = ? AND xp > ?''',
              (chat_id, xp))
    rank = c.fetchone()[0] + 1
    
    conn.close()
    return (xp, int(level), rank

def get_top_users(chat_id, limit=10):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    c.execute('''SELECT u.first_name, x.xp, x.level, u.user_id
                 FROM xp x JOIN users u ON x.user_id = u.user_id
                 WHERE x.chat_id = ?
                 ORDER BY x.xp DESC LIMIT ?''',
              (chat_id, limit))
    
    results = c.fetchall()
    conn.close()
    return results

def add_warning(user_id, chat_id, reason, admin_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO warns 
                 (user_id, chat_id, reason, admin_id, timestamp)
                 VALUES (?, ?, ?, ?, datetime('now'))''',
              (user_id, chat_id, reason, admin_id))
    
    conn.commit()
    conn.close()

def get_user_country(user_id):
    return "Unknown"

# Initialize database
init_db()

# ======================
# IMAGE GENERATION
# ======================

async def generate_rank_card(user, xp, level, rank, chat_id):
    img = Image.new('RGB', (800, 300), color=(54, 57, 63))
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 40)
        normal_font = ImageFont.truetype("arial.ttf", 30)
    except:
        title_font = ImageFont.load_default()
        normal_font = ImageFont.load_default()
    
    try:
        profile_pic = await user.get_profile_photos(limit=1)
        if profile_pic.photos:
            photo = profile_pic.photos[0][-1]
            photo_file = await photo.get_file()
            photo_bytes = BytesIO()
            await photo_file.download_to_memory(photo_bytes)
            profile_img = Image.open(photo_bytes).resize((200, 200))
            
            mask = Image.new('L', (200, 200), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, 200, 200), fill=255)
            
            img.paste(profile_img, (50, 50), mask)
    except:
        pass
    
    draw.text((300, 50), f"{user.first_name}", font=title_font, fill=(255, 255, 255))
    draw.text((300, 120), f"Level: {level}", font=normal_font, fill=(200, 200, 200))
    draw.text((300, 160), f"XP: {xp}", font=normal_font, fill=(200, 200, 200))
    draw.text((300, 200), f"Rank: #{rank}", font=normal_font, fill=(200, 200, 200))
    
    xp_needed = level * 1000
    progress = min(xp % 1000 / 1000, 1.0)
    draw.rectangle([300, 250, 300 + 400 * progress, 270], fill=(114, 137, 218))
    draw.rectangle([300, 250, 700, 270], outline=(255, 255, 255), width=2)
    draw.text((710, 240), f"{int(progress*100)}%", font=normal_font, fill=(255, 255, 255))
    
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    return buf

async def generate_leaderboard(chat_id, top_users):
    img = Image.new('RGB', (800, 300 + len(top_users) * 60), color=(54, 57, 63))
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 40)
        normal_font = ImageFont.truetype("arial.ttf", 30)
    except:
        title_font = ImageFont.load_default()
        normal_font = ImageFont.load_default()
    
    draw.text((50, 30), "🏆 Leaderboard", font=title_font, fill=(255, 255, 255))
    
    for i, (name, xp, level, user_id) in enumerate(top_users, 1):
        y_pos = 100 + (i-1)*60
        draw.text((100, y_pos), f"{i}. {name}", font=normal_font, fill=(255, 255, 255))
        draw.text((550, y_pos), f"Lvl {level}", font=normal_font, fill=(200, 200, 200))
        draw.text((650, y_pos), f"{xp} XP", font=normal_font, fill=(200, 200, 200))
    
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    return buf

# ======================
# BOT CONFIGURATION
# ======================

BOT_TOKEN = "7406932492:AAGFveg9HUKC7B6fx9wHHboe3d_DZBWhppc"
ADMIN_IDS = []  # Add your admin user IDs here

# ======================
# MODERATION UTILITIES
# ======================

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    if user.id in ADMIN_IDS:
        return True
    
    try:
        member = await chat.get_member(user.id)
        return member.status in ['administrator', 'creator']
    except:
        return False

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    
    if context.args and context.args[0].startswith('@'):
        username = context.args[0][1:]
        try:
            chat_members = await update.effective_chat.get_members()
            for member in chat_members:
                if member.user.username and member.user.username.lower() == username.lower():
                    return member.user
        except:
            pass
    
    if context.args and context.args[0].isdigit():
        user_id = int(context.args[0])
        try:
            return await context.bot.get_chat_member(update.effective_chat.id, user_id).user
        except:
            pass
    
    return None

# ======================
# CORE FUNCTIONS
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.first_name, user.last_name or "", user.username or "")
    
    await update.message.reply_text(
        f"👋 Hello {user.first_name}! I'm your friendly group bot.\n\n"
        "Use /help to see all available commands!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Help", callback_data="help")]
        ])
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 *Bot Commands*

🎲 *Games:*
/dice [count] - Roll dice(s)
/coinflip - Flip a coin
/rps - Play Rock Paper Scissors

📊 *Stats:*
/rank - Check your rank
/top - Show leaderboard
/profile - Show user profile

🛡️ *Moderation (Admin only):*
/warn [user] [reason] - Warn a user
/mute [user] [duration] [reason] - Mute a user
/kick [user] [reason] - Kick a user
/ban [user] [reason] - Ban a user
/purge [count] - Delete messages

😄 *Fun:*
/joke - Get a random joke
/roast - Roast someone
/meme - Get a random meme
/love @user - Calculate love percentage
/8ball [question] - Magic 8 ball
/rate [something] - Rate something

ℹ️ *Info:*
/id - Get your user ID
/info - Get your info
/groupinfo - Get group info
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        await help_command(update, context)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    await update.message.reply_text(
        f"🆔 *ID Information*\n\n"
        f"• Your ID: `{user.id}`\n"
        f"• Chat ID: `{chat.id}`\n"
        f"• Username: @{user.username or 'N/A'}",
        parse_mode="Markdown"
    )

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👤 *User Information*\n\n"
        f"• Name: {user.full_name}\n"
        f"• Username: @{user.username or 'N/A'}\n"
        f"• ID: `{user.id}`\n"
        f"• Language: {user.language_code or 'Unknown'}",
        parse_mode="Markdown"
    )

async def group_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    
    if chat.type == "private":
        await update.message.reply_text("This command only works in groups!")
        return
    
    await update.message.reply_text(
        f"👥 *Group Information*\n\n"
        f"• Title: {chat.title}\n"
        f"• ID: `{chat.id}`\n"
        f"• Type: {chat.type}\n"
        f"• Members: {chat.get_member_count() if hasattr(chat, 'get_member_count') else 'Unknown'}",
        parse_mode="Markdown"
    )

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        if new_user.is_bot and new_user.id == context.bot.id:
            await update.message.reply_text(
                "🤖 Thanks for adding me! Use /help to see my commands!"
            )
        else:
            country = get_user_country(new_user.id)
            add_user(new_user.id, new_user.first_name, 
                    new_user.last_name or "", new_user.username or "", country)
            
            welcome_msg = (
                f"👋 Welcome {new_user.mention_markdown()} to the group!\n\n"
                f"• Type /help for commands\n"
                f"• Earn XP by being active\n"
                f"• Have fun with our games!"
            )
            
            await update.message.reply_text(
                welcome_msg,
                parse_mode="Markdown"
            )
            add_xp(new_user.id, update.message.chat.id, new_user.first_name, 20)

# ======================
# GAME COMMANDS
# ======================

async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dice_faces = {
        1: "⚀",
        2: "⚁",
        3: "⚂",
        4: "⚃",
        5: "⚄",
        6: "⚅"
    }
    
    try:
        count = min(max(int(context.args[0]), 1) if context.args else 1, 5)
    except:
        count = 1
    
    frames = []
    for _ in range(3):
        frame = " ".join([dice_faces[random.randint(1,6)] for _ in range(count)])
        frames.append(frame)
    
    msg = await update.message.reply_text("🎲 Rolling...")
    for frame in frames:
        await msg.edit_text(f"🎲 Rolling...\n{frame}")
        await asyncio.sleep(0.5)
    
    rolls = [random.randint(1, 6) for _ in range(count)]
    emojis = [dice_faces[r] for r in rolls]
    total = sum(rolls)
    
    result = f"{' '.join(emojis)}\nTotal: *{total}* "
    if count > 1:
        if all(r == 6 for r in rolls):
            result += "🎯 *PERFECT ROLL!*"
        elif all(r == 1 for r in rolls):
            result += "💀 *WORST LUCK!*"
        elif total >= count*5:
            result += "🔥 *Great rolls!*"
        elif total <= count*2:
            result += "😅 *Unlucky!*"
    
    await msg.edit_text(result, parse_mode="Markdown")
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 5 + count)

async def coinflip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = random.choice(["Heads", "Tails"])
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Flip Again", callback_data="cf_again")]
    ])
    
    await update.message.reply_text(
        f"🪙 The coin landed on *{result}*!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 5)

async def handle_coinflip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cf_again":
        await coinflip(update, context)

async def rps_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
         InlineKeyboardButton("📄 Paper", callback_data="rps_paper"),
         InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors")]
    ])
    
    await update.message.reply_text(
        "Choose your move:",
        reply_markup=keyboard
    )

async def handle_rps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_choice = query.data.split("_")[1]
    bot_choice = random.choice(["rock", "paper", "scissors"])
    
    result_map = {
        ("rock", "scissors"): "You win!",
        ("paper", "rock"): "You win!",
        ("scissors", "paper"): "You win!",
        ("scissors", "rock"): "I win!",
        ("rock", "paper"): "I win!",
        ("paper", "scissors"): "I win!"
    }
    
    if user_choice == bot_choice:
        result = "It's a tie!"
    else:
        result = result_map[(user_choice, bot_choice)]
    
    emoji_map = {
        "rock": "🪨",
        "paper": "📄",
        "scissors": "✂️"
    }
    
    await query.edit_message_text(
        f"{emoji_map[user_choice]} vs {emoji_map[bot_choice]}\n\n"
        f"*{result}*",
        parse_mode="Markdown"
    )
    add_xp(query.from_user.id, query.message.chat.id, query.from_user.first_name, 5)

# ======================
# FUN COMMANDS
# ======================

async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them.",
        "Why don't skeletons fight each other? They don't have the guts.",
        "I told my wife she was drawing her eyebrows too high. She looked surprised.",
        "What do you call a fake noodle? An impasta!"
    ]
    joke = random.choice(jokes)
    await update.message.reply_text(joke)
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 5)

async def roast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.effective_user
    if context.args and update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    
    roasts = [
        f"{target.first_name}, if laughter is the best medicine, your face must be curing the world.",
        f"{target.first_name}, you're not stupid; you just have bad luck when thinking.",
        f"{target.first_name}, your secrets are always safe with me. I never even listen when you talk.",
        f"{target.first_name}, you bring everyone so much joy... when you leave the room.",
        f"{target.first_name}, I'd agree with you but then we'd both be wrong."
    ]
    roast = random.choice(roasts)
    await update.message.reply_text(roast)
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 5)

async def meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get("https://meme-api.com/gimme")
        if response.status_code == 200:
            data = response.json()
            await update.message.reply_photo(
                photo=data["url"],
                caption=data["title"]
            )
            add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 5)
        else:
            await update.message.reply_text("Couldn't fetch a meme right now. Try again later!")
    except:
        await update.message.reply_text("Meme service unavailable. Try again later!")

async def gay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.effective_user
    if context.args and update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    
    percentage = random.randint(0, 100)
    rainbow = "🌈" * (percentage // 10)
    
    await update.message.reply_text(
        f"🏳️‍🌈 *Gay Meter*\n\n"
        f"{target.first_name} is {percentage}% gay!\n"
        f"{rainbow}",
        parse_mode="Markdown"
    )
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 5)

async def love_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text("Please mention someone or reply to a message!")
        return
    
    user1 = update.effective_user
    user2 = None
    
    if update.message.reply_to_message:
        user2 = update.message.reply_to_message.from_user
    elif context.args and context.args[0].startswith('@'):
        username = context.args[0][1:]
        try:
            chat_members = await update.effective_chat.get_members()
            for member in chat_members:
                if member.user.username and member.user.username.lower() == username.lower():
                    user2 = member.user
                    break
        except:
            pass
    
    if not user2:
        await update.message.reply_text("Couldn't find that user!")
        return
    
    # Calculate "love" based on names (for consistency)
    love_percent = (hash(user1.first_name + user2.first_name) % 101
    
    await update.message.reply_text(
        f"💖 *Love Calculator*\n\n"
        f"{user1.first_name} ❤️ {user2.first_name}\n"
        f"Love: {love_percent}%\n\n"
        f"{'💔' if love_percent < 30 else '❤️' * (love_percent // 20)}",
        parse_mode="Markdown"
    )
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 5)

async def magic_8ball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    responses = [
        "It is certain.", "It is decidedly so.", "Without a doubt.",
        "Yes - definitely.", "You may rely on it.", "As I see it, yes.",
        "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
        "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
        "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.",
        "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
    ]
    
    question = " ".join(context.args) if context.args else "nothing"
    response = random.choice(responses)
    
    await update.message.reply_text(
        f"🎱 *Magic 8 Ball*\n\n"
        f"Question: {question}\n"
        f"Answer: *{response}*",
        parse_mode="Markdown"
    )
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 5)

async def rate_something(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify something to rate!")
        return
    
    thing = " ".join(context.args)
    rating = (hash(thing) % 100) + 1  # Ensure it's between 1-100
    
    await update.message.reply_text(
        f"⭐ *Rating*\n\n"
        f"I rate {thing} a *{rating}/100*!",
        parse_mode="Markdown"
    )
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 5)

# ======================
# STATS COMMANDS
# ======================

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    result = get_rank(user.id, update.effective_chat.id)
    
    if not result:
        await update.message.reply_text("📊 You don't have any XP yet!")
        return
    
    xp, level, rank = result
    
    image = await generate_rank_card(user, xp, level, rank, update.effective_chat.id)
    
    await update.message.reply_photo(
        photo=image,
        caption=f"📊 *Stats for {user.first_name}*\nLevel: {level} | XP: {xp} | Rank: #{rank}",
        parse_mode="Markdown"
    )

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = get_top_users(update.effective_chat.id)
    
    if not top_users:
        await update.message.reply_text("🏆 No rankings yet in this chat!")
        return
    
    image = await generate_leaderboard(update.effective_chat.id, top_users)
    
    await update.message.reply_photo(
        photo=image,
        caption="🏆 *Top Users Leaderboard*",
        parse_mode="Markdown"
    )

async def user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.effective_user
    if context.args:
        try:
            target_user = await get_target_user(update, context)
            if target_user:
                target = target_user
        except:
            pass
    
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    c.execute('''SELECT first_name, last_name, username, country, join_date 
                 FROM users WHERE user_id = ?''', (target.id,))
    user_data = c.fetchone()
    
    if not user_data:
        await update.message.reply_text("User not found in database!")
        return
    
    first_name, last_name, username, country, join_date = user_data
    result = get_rank(target.id, update.effective_chat.id)
    
    response = (
        f"👤 *User Profile*\n\n"
        f"Name: {first_name} {last_name or ''}\n"
        f"Username: @{username or 'N/A'}\n"
        f"Country: {country}\n"
        f"Joined: {join_date}\n\n"
    )
    
    if result:
        xp, level, rank = result
        response += f"Level: {level}\nXP: {xp}\nRank: #{rank}"
    
    try:
        profile_pic = await target.get_profile_photos(limit=1)
        if profile_pic.photos:
            photo = profile_pic.photos[0][-1]
            await update.message.reply_photo(
                photo=photo.file_id,
                caption=response,
                parse_mode="Markdown"
            )
            return
    except:
        pass
    
    await update.message.reply_text(response, parse_mode="Markdown")

# ======================
# MODERATION COMMANDS
# ======================

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ You need admin privileges for this command!")
        return
    
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to or mention a user!")
        return
    
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason provided"
    
    add_warning(target.id, update.effective_chat.id, reason, update.effective_user.id)
    
    await update.message.reply_text(
        f"⚠️ *Warning Issued*\n\n"
        f"User: {target.mention_markdown()}\n"
        f"Reason: {reason}\n"
        f"By: {update.effective_user.mention_markdown()}",
        parse_mode="Markdown"
    )

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ You need admin privileges for this command!")
        return
    
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to or mention a user!")
        return
    
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason provided"
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id
        )
        
        await update.message.reply_text(
            f"🔨 *User Banned*\n\n"
            f"User: {target.mention_markdown()}\n"
            f"Reason: {reason}\n"
            f"By: {update.effective_user.mention_markdown()}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to ban user: {e}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ You need admin privileges for this command!")
        return
    
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to or mention a user!")
        return
    
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason provided"
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            until_date=int(time.time()) + 60
        )
        
        await update.message.reply_text(
            f"👢 *User Kicked*\n\n"
            f"User: {target.mention_markdown()}\n"
            f"Reason: {reason}\n"
            f"By: {update.effective_user.mention_markdown()}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to kick user: {e}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ You need admin privileges for this command!")
        return
    
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to or mention a user!")
        return
    
    duration = 60
    reason = ""
    
    if context.args:
        if context.args[0].isdigit():
            duration = min(int(context.args[0]), 1440)
            reason = " ".join(context.args[1:])
        else:
            reason = " ".join(context.args)
    
    if not reason:
        reason = "No reason provided"
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            ),
            until_date=datetime.datetime.now() + datetime.timedelta(minutes=duration)
        )
        
        time_unit = "minutes" if duration < 60 else "hours"
        duration_display = duration if duration < 60 else duration // 60
        
        await update.message.reply_text(
            f"🔇 *User Muted*\n\n"
            f"User: {target.mention_markdown()}\n"
            f"Duration: {duration_display} {time_unit}\n"
            f"Reason: {reason}\n"
            f"By: {update.effective_user.mention_markdown()}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to mute user: {e}")

async def purge_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ You need admin privileges for this command!")
        return
    
    try:
        count = int(context.args[0]) if context.args else 10
        count = min(max(count, 1), 100)
        
        await update.message.delete()
        
        messages = []
        async for message in context.bot.get_chat_history(
            chat_id=update.effective_chat.id,
            limit=count + 1
        ):
            messages.append(message.message_id)
        
        await context.bot.delete_messages(
            chat_id=update.effective_chat.id,
            message_ids=messages[:count]
        )
        
        msg = await update.effective_chat.send_message(
            f"🗑️ Deleted {count} messages"
        )
        await asyncio.sleep(5)
        await msg.delete()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to purge messages: {e}")

# ======================
# ERROR HANDLER
# ======================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error: {context.error}")
    
    try:
        await update.message.reply_text(
            "❌ An error occurred while processing your command. Please try again later."
        )
    except:
        pass

# ======================
# BOT SETUP
# ======================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Event handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    
    # Core commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("info", user_info))
    app.add_handler(CommandHandler("groupinfo", group_info))
    
    # Game commands
    app.add_handler(CommandHandler("dice", dice))
    app.add_handler(CommandHandler("roll", dice))
    app.add_handler(CommandHandler("coinflip", coinflip))
    app.add_handler(CommandHandler("flip", coinflip))
    app.add_handler(CallbackQueryHandler(handle_coinflip, pattern="^cf_"))
    app.add_handler(CommandHandler("rps", rps_game))
        app.add_handler(CallbackQueryHandler(handle_rps, pattern="^rps_"))
    
    # Fun commands
    app.add_handler(CommandHandler("joke", joke))
    app.add_handler(CommandHandler("roast", roast))
    app.add_handler(CommandHandler("meme", meme))
    app.add_handler(CommandHandler("gay", gay))
    app.add_handler(CommandHandler("love", love_calculator))
    app.add_handler(CommandHandler("8ball", magic_8ball))
    app.add_handler(CommandHandler("rate", rate_something))
    
    # Stats commands
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("stats", rank))
    app.add_handler(CommandHandler("top", leaderboard))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("profile", user_profile))
    
    # Moderation commands
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("purge", purge_messages))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    print("🤖 Bot is now running...")
    app.run_polling()

if __name__ == "__main__":
