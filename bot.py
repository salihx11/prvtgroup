import datetime
import random
import os
import asyncio
import sqlite3
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

def add_user(user_id, first_name, last_name="", username=""):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users 
                 (user_id, first_name, last_name, username, join_date)
                 VALUES (?, ?, ?, ?, datetime('now'))''',
              (user_id, first_name, last_name, username))
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
    return (xp, int(level), rank)

def get_top_users(chat_id, limit=10):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    c.execute('''SELECT u.first_name, x.xp, x.level 
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

# Initialize database
init_db()

# ======================
# BOT CONFIGURATION
# ======================

BOT_TOKEN = "7406932492:AAGFveg9HUKC7B6fx9wHHboe3d_DZBWhppc"
ADMIN_IDS = [1362321291]  # Replace with your admin user IDs

# ======================
# CORE FUNCTIONS
# ======================

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        if new_user.is_bot and new_user.id == context.bot.id:
            await update.message.reply_text(
                "🤖 Thanks for adding me! Use /help to see my commands!"
            )
        else:
            add_user(new_user.id, new_user.first_name, 
                    new_user.last_name or "", new_user.username or "")
            
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Add to Group", 
         url="https://t.me/YourBotUsername?startgroup=true")],
        [InlineKeyboardButton("🎮 Games", callback_data="games_menu"),
         InlineKeyboardButton("😂 Fun", callback_data="fun_menu")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats_menu"),
         InlineKeyboardButton("🛡️ Mod", callback_data="mod_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = update.effective_user
    add_user(user.id, user.first_name, 
            user.last_name or "", user.username or "")
    
    await update.message.reply_text(
        f"✨ *Welcome {user.first_name} to UltimateBot!* ✨\n\n"
        "I'm your all-in-one entertainment bot with:\n"
        "🎮 Games | 😂 Fun | 📊 XP System | 🛡️ Moderation\n\n"
        "Tap below or type /help",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 *UltimateBot Command List* 🤖

🎮 *Games:*
/dice [1-5] - Roll dice 🎲
/coinflip - Heads or tails 🪙
/rps - Rock paper scissors 🪨📄✂️
/guess - Number guessing game 🔢
/trivia - Random trivia question ❓

😂 *Fun Commands:*
/joke - Get a random joke 😂
/roast - Get roasted 🔥
/meme - Random meme 🖼️
/gay - Gay percentage 🏳️‍🌈
/love @user - Love calculator 💘
/8ball [question] - Magic 8 ball 🔮
/rate - Rate something ★

📊 *Stats:*
/rank - Check your rank 📈
/top - Leaderboard 🏆
/profile [@user] - User profile 👤

🛡️ *Moderation:*
/warn @user [reason] - Warn user ⚠️
/ban @user [reason] - Ban user 🔨
/mute @user [time] - Mute user 🔇
/kick @user [reason] - Kick user 👢
/purge [amount] - Delete messages 🗑️

ℹ *Utilities:*
/id - Get user/chat info ℹ
/info @user - User details 📝
/groupinfo - Group stats 👥
/weather [city] - Weather forecast 🌦️
/calc [expression] - Calculator 🧮
/timer [seconds] - Set timer ⏱️
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "games_menu":
        text = "🎮 *Game Commands*\n\n/dice - Roll dice\n/coinflip - Heads or tails\n/rps - Rock paper scissors\n/guess - Number game\n/trivia - Random question"
    elif data == "fun_menu":
        text = "😂 *Fun Commands*\n\n/joke - Random joke\n/roast - Get roasted\n/meme - Random meme\n/gay - Gay test\n/love - Compatibility test"
    elif data == "stats_menu":
        text = "📊 *Stat Commands*\n\n/rank - Your stats\n/top - Leaderboard\n/profile - User profile"
    elif data == "mod_menu":
        text = "🛡️ *Mod Commands*\n\n/warn - Warn user\n/ban - Ban user\n/mute - Mute user\n/kick - Kick user\n/purge - Delete messages"
    else:
        text = "Unknown menu selection"
    
    await query.edit_message_text(text, parse_mode="Markdown")

# ======================
# GAME COMMANDS
# ======================

async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    
    try:
        count = min(max(int(context.args[0]), 1) if context.args else 1, 5)
    except:
        count = 1
    
    # Animation
    msg = await update.message.reply_text("🎲 Rolling...")
    await asyncio.sleep(1)
    
    rolls = [random.randint(1, 6) for _ in range(count)]
    emojis = [dice_faces[r-1] for r in rolls]
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
    keyboard = [
        [InlineKeyboardButton("🪙 Heads", callback_data="cf_heads"),
         InlineKeyboardButton("🪙 Tails", callback_data="cf_tails")],
        [InlineKeyboardButton("🎲 Random", callback_data="cf_random")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🪙 *Coin Flip Challenge*\n\nChoose your side:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_coinflip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_choice = query.data.split("_")[1]
    if user_choice == "random":
        user_choice = random.choice(["heads", "tails"])
    
    # Animation
    for frame in ["🔄 Spinning...", "🌀 Almost there..."]:
        await query.edit_message_text(frame)
        await asyncio.sleep(0.7)
    
    bot_choice = random.choice(["heads", "tails"])
    result = "won" if user_choice == bot_choice else "lost"
    
    response = (
        f"🪙 *Coin Flip Results*\n\n"
        f"• Your choice: {user_choice.capitalize()}\n"
        f"• Result: {bot_choice.capitalize()}\n\n"
        f"{'🎉 You won! +10 XP' if result == 'won' else '😅 You lost! +5 XP'}"
    )
    
    await query.edit_message_text(response, parse_mode="Markdown")
    add_xp(query.from_user.id, query.message.chat.id, query.from_user.first_name, 10 if result == 'won' else 5)

async def rps_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choices = {
        "rock": "🪨 Rock",
        "paper": "📄 Paper",
        "scissors": "✂️ Scissors"
    }
    
    keyboard = [
        [InlineKeyboardButton(choices["rock"], callback_data="rps_rock"),
         InlineKeyboardButton(choices["paper"], callback_data="rps_paper")],
        [InlineKeyboardButton(choices["scissors"], callback_data="rps_scissors")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🪨📄✂️ *Rock Paper Scissors*\n\nChoose your move:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_rps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_choice = query.data.split("_")[1]
    bot_choice = random.choice(["rock", "paper", "scissors"])
    
    # Determine winner
    if user_choice == bot_choice:
        result = "It's a tie!"
        xp = 5
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
        xp = 10
    else:
        result = "I win! 😎"
        xp = 3
    
    response = (
        f"🪨📄✂️ *RPS Results*\n\n"
        f"• You chose: {user_choice.capitalize()}\n"
        f"• I chose: {bot_choice.capitalize()}\n\n"
        f"*{result}* (+{xp} XP)"
    )
    
    await query.edit_message_text(response, parse_mode="Markdown")
    add_xp(query.from_user.id, query.message.chat.id, query.from_user.first_name, xp)

# ======================
# FUN COMMANDS
# ======================

async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them!",
        "Why don't skeletons fight each other? They don't have the guts!",
        "I told my wife she was drawing her eyebrows too high. She looked surprised.",
        "What do you call a fake noodle? An impasta!",
        "How do you organize a space party? You planet!"
    ]
    await update.message.reply_text(f"😂 *Joke:* {random.choice(jokes)}", parse_mode="Markdown")
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 3)

async def roast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roasts = [
        "You're the reason the gene pool needs a lifeguard.",
        "If I had a face like yours, I'd sue my parents.",
        "You're proof that evolution can go in reverse.",
        "You're as useless as the 'g' in lasagna.",
        "I'd agree with you but then we'd both be wrong.",
        "You're like a cloud. When you disappear, it's a beautiful day."
    ]
    await update.message.reply_text(f"🔥 *Roast:* {random.choice(roasts)}", parse_mode="Markdown")
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 3)

async def meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memes = [
        "https://i.imgflip.com/30b1gx.jpg",  # Distracted boyfriend
        "https://i.imgflip.com/9vct.jpg",    # Waiting skeleton
        "https://i.imgflip.com/1bij.jpg",    # One does not simply
        "https://i.imgflip.com/1g8my.jpg",   # Two buttons
        "https://i.imgflip.com/1h7in3.jpg",  # Roll safe
        "https://i.imgflip.com/1ihzfe.jpg"   # Batman slapping Robin
    ]
    await update.message.reply_photo(
        photo=random.choice(memes),
        caption="😂 *Here's your meme!*"
    )
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 3)

async def gay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.effective_user
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    
    percentage = random.randint(0, 100)
    rainbow = "🌈" * int(percentage/10) + "⚪" * (10 - int(percentage/10))
    
    responses = [
        ("Fabulous! 🌈", 80),
        ("Pretty gay! 😊", 60),
        ("Mostly straight 😐", 40),
        ("Super straight 🏳️", 20),
        ("No homo detected 🚫", 0)
    ]
    
    response = next((r for r in responses if percentage >= r[1]), responses[-1])[0]
    
    await update.message.reply_text(
        f"🏳️‍🌈 *Gaydar Analysis*\n\n"
        f"Subject: {target.mention_markdown()}\n"
        f"Gay Percentage: {percentage}%\n"
        f"{rainbow}\n\n"
        f"{response}",
        parse_mode="Markdown"
    )
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 3)

async def love_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("💘 Reply to someone to test your compatibility!")
        return
    
    user1 = update.effective_user
    user2 = update.message.reply_to_message.from_user
    percent = random.randint(10, 100)
    hearts = "❤️" * int(percent/10) + "💔" * (10 - int(percent/10))
    
    await update.message.reply_text(
        f"💘 *Love Compatibility*\n\n"
        f"{user1.first_name} ❤️ {user2.first_name} = {percent}%\n"
        f"{hearts}\n\n"
        f"{'Soulmates! 💞' if percent > 85 else 'Great match! 😊' if percent > 60 else 'Not compatible... 😢'}",
        parse_mode="Markdown"
    )
    add_xp(user1.id, update.effective_chat.id, user1.first_name, 3)
    add_xp(user2.id, update.effective_chat.id, user2.first_name, 3)

async def magic_8ball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    responses = [
        ("It is certain.", "🟢"),
        ("Without a doubt.", "🟢"),
        ("You may rely on it.", "🟢"),
        ("Ask again later.", "🟡"),
        ("Cannot predict now.", "🟡"),
        ("Don't count on it.", "🔴"),
        ("My reply is no.", "🔴"),
        ("Very doubtful.", "🔴")
    ]
    answer, color = random.choice(responses)
    question = " ".join(context.args) if context.args else "your question"
    
    await update.message.reply_text(
        f"🎱 *Magic 8-Ball*\n\n"
        f"Question: {question}\n"
        f"Answer: {color} {answer}",
        parse_mode="Markdown"
    )
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 3)

async def rate_something(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify something to rate!")
        return
    
    item = " ".join(context.args)
    rating = random.randint(1, 10)
    stars = "⭐" * rating + "☆" * (10 - rating)
    
    await update.message.reply_text(
        f"🌟 *Rating*\n\n"
        f"{item}:\n"
        f"{stars}\n"
        f"{rating}/10\n\n"
        f"{'Perfect! 🌟' if rating == 10 else 'Terrible! 💩' if rating < 3 else 'Not bad! 👍'}",
        parse_mode="Markdown"
    )
    add_xp(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name, 3)

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
    
    response = (
        f"📊 *Your Stats*\n\n"
        f"👤 {user.mention_markdown()}\n"
        f"⭐ Level: {level}\n"
        f"✨ XP: {xp}\n"
        f"🏆 Rank: #{rank}"
    )
    
    await update.message.reply_text(response, parse_mode="Markdown")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = get_top_users(update.effective_chat.id)
    
    if not top_users:
        await update.message.reply_text("🏆 No rankings yet in this chat!")
        return
    
    leaderboard_text = "🏆 *Top Users*\n\n"
    for i, (name, xp, level) in enumerate(top_users, 1):
        leaderboard_text += f"{i}. {name} - Lvl {level} ({xp} XP)\n"
    
    await update.message.reply_text(leaderboard_text, parse_mode="Markdown")

async def user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.effective_user
    if context.args:
        try:
            # This would need proper user mention parsing in a real implementation
            target_id = int(context.args[0])
            # In a real bot, you'd look up the user by ID/username
            target = target  # Simplified for example
        except:
            pass
    
    result = get_rank(target.id, update.effective_chat.id)
    
    if not result:
        await update.message.reply_text("📊 This user has no XP yet!")
        return
    
    xp, level, rank = result
    
    response = (
        f"👤 *User Profile*\n\n"
        f"Name: {target.mention_markdown()}\n"
        f"Level: {level}\n"
        f"XP: {xp}\n"
        f"Rank: #{rank}\n"
        f"Joined: {target.mention_markdown()}"
    )
    
    await update.message.reply_text(response, parse_mode="Markdown")

# ======================
# MODERATION COMMANDS
# ======================

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You need admin privileges for this command!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to the user you want to warn!")
        return
    
    target = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "No reason provided"
    
    add_warning(target.id, update.effective_chat.id, reason, update.effective_user.id)
    
    await update.message.reply_text(
        f"⚠️ *Warning Issued*\n\n"
        f"User: {target.mention_markdown()}\n"
        f"Reason: {reason}\n"
        f"By: {update.effective_user.mention_markdown()}",
        parse_mode="Markdown"
    )

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You need admin privileges for this command!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to the user you want to ban!")
        return
    
    target = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "No reason provided"
    
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

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You need admin privileges for this command!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to the user you want to mute!")
        return
    
    target = update.message.reply_to_message.from_user
    time = int(context.args[0]) if context.args and context.args[0].isdigit() else 60
    
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
            until_date=datetime.datetime.now() + datetime.timedelta(minutes=time)
        )
        
        await update.message.reply_text(
            f"🔇 *User Muted*\n\n"
            f"User: {target.mention_markdown()}\n"
            f"Duration: {time} minutes\n"
            f"By: {update.effective_user.mention_markdown()}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to mute user: {e}")

# ======================
# UTILITY COMMANDS
# ======================

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    await update.message.reply_text(
        f"🆔 *ID Information*\n\n"
        f"👤 User ID: `{user.id}`\n"
        f"👥 Chat ID: `{chat.id}`\n"
        f"🔤 Username: @{user.username if user.username else 'N/A'}",
        parse_mode="Markdown"
    )

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.effective_user
    if context.args:
        try:
            # This would need proper user mention parsing in a real implementation
            target_id = int(context.args[0])
            # In a real bot, you'd look up the user by ID/username
            target = target  # Simplified for example
        except:
            pass
    
    await update.message.reply_text(
        f"📝 *User Info*\n\n"
        f"Name: {target.mention_markdown()}\n"
        f"ID: `{target.id}`\n"
        f"Username: @{target.username if target.username else 'N/A'}\n"
        f"First Seen: {datetime.datetime.now().strftime('%Y-%m-%d')}",
        parse_mode="Markdown"
    )

async def group_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    
    await update.message.reply_text(
        f"👥 *Group Info*\n\n"
        f"Name: {chat.title}\n"
        f"ID: `{chat.id}`\n"
        f"Type: {chat.type}\n"
        f"Members: {await chat.get_member_count()}",
        parse_mode="Markdown"
    )

# ======================
# ERROR HANDLER
# ======================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"⚠️ Error occurred: {context.error}")
    if update and hasattr(update, 'message'):
        try:
            await update.message.reply_text("⚠️ An error occurred. Please try again later.")
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
    app.add_handler(CommandHandler("roll", dice))  # Alias
    app.add_handler(CommandHandler("coinflip", coinflip))
    app.add_handler(CommandHandler("flip", coinflip))  # Alias
    app.add_handler(CallbackQueryHandler(handle_coinflip, pattern="^cf_"))
    app.add_handler(CommandHandler("rps", rps_game))
    app.add_handler(CommandHandler("rockpaperscissors", rps_game))  # Alias
    app.add_handler(CallbackQueryHandler(handle_rps, pattern="^rps_"))
    app.add_handler(CommandHandler("guess", magic_8ball))  # Placeholder
    app.add_handler(CommandHandler("trivia", magic_8ball))  # Placeholder
    
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
    app.add_handler(CommandHandler("stats", rank))  # Alias
    app.add_handler(CommandHandler("top", leaderboard))
    app.add_handler(CommandHandler("leaderboard", leaderboard))  # Alias
    app.add_handler(CommandHandler("profile", user_profile))
    
    # Moderation commands
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("kick", ban_user))  # Alias with different text
    app.add_handler(CommandHandler("purge", warn_user))  # Placeholder
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    print("🤖 Bot is now running...")
    app.run_polling()

if __name__ == "__main__":
    main()
