import telebot
import os
import urllib.parse as urlparse
from datetime import datetime, timedelta
import time
import random
from flask import Flask
from threading import Thread

# 🔥 VAŠI PODACI
BOT_TOKEN = "8335453036:AAHtJccB5FgalVocPAo52L_9miyTI4VqOsY"
ADMIN_IDS = [7758741268]
YOUR_PAYPAL = "Bebogang46@gmail.com"
MAIN_GROUP_LINK = "https://t.me/+S4UDy5ylfGg4OGY0"
PRIVATE_CHANNEL_LINK = "https://t.me/+YvJdDpxnyqJhMmU0"
SUBSCRIPTION_DAYS = 30
MAIN_GROUP_ID = -1003896893394

# 🔗 POSTGRESQL DATABASE URL (OVO JE TVOJ)
DATABASE_URL = "postgresql://mia_bot_user:j0tQFEAvXyNB9D2Xp0gM0lX11ZzmBFcN@dpg-d63jhpshg0os73cht1bg-a/mia_bot_db"

bot = telebot.TeleBot(BOT_TOKEN)

print("=" * 60)
print("🤖 MIA ANTH BOT - WITH POSTGRESQL DATABASE")
print("=" * 60)

# ========== HELPER FUNCTIONS ==========
def is_admin(user_id):
    return user_id in ADMIN_IDS

def escape_markdown(text):
    if not text:
        return ""
    return str(text).replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]')

def notify_admins_with_photo(photo_file_id, caption):
    """Šalje sliku i caption svim adminima"""
    sent_count = 0
    for admin_id in ADMIN_IDS:
        try:
            bot.send_photo(admin_id, photo_file_id, caption=caption, parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.1)
        except Exception as e:
            print(f"⚠️  Cannot send photo to admin {admin_id}: {e}")
    return sent_count

def safe_send_message(chat_id, text, parse_mode='Markdown'):
    try:
        return bot.send_message(chat_id, text, parse_mode=parse_mode)
    except:
        try:
            return bot.send_message(chat_id, text, parse_mode=None)
        except:
            return None

# ========== POSTGRESQL DATABASE SETUP ==========
print("🔗 Connecting to PostgreSQL database...")
print(f"📊 Database URL: {DATABASE_URL[:50]}...")

try:
    import psycopg2
    
    # Parsiraj URL za PostgreSQL
    url = urlparse.urlparse(DATABASE_URL)
    dbname = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port
    
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    conn.autocommit = False
    cursor = conn.cursor()
    print("✅ Connected to PostgreSQL database!")
    
    # Kreiraj tabele ako ne postoje
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (user_id BIGINT PRIMARY KEY,
                       username TEXT,
                       payment_date TEXT,
                       expiry_date TEXT,
                       status TEXT DEFAULT 'pending',
                       used_invite INTEGER DEFAULT 0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS pending_approvals
                      (user_id BIGINT PRIMARY KEY,
                       username TEXT,
                       request_time TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS banned_users
                      (user_id BIGINT PRIMARY KEY,
                       username TEXT,
                       ban_date TEXT,
                       reason TEXT)''')
    conn.commit()
    print("✅ Database tables created/verified")
    
except Exception as e:
    print(f"❌ PostgreSQL connection failed: {e}")
    print("⚠️ Falling back to in-memory SQLite")
    import sqlite3
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()

# ========== HELPER FUNCTIONS ==========
def calculate_expiry_date():
    return (datetime.now() + timedelta(days=SUBSCRIPTION_DAYS)).isoformat()

def days_until_expiry(expiry_date_str):
    if not expiry_date_str:
        return 0
    try:
        expiry_date = datetime.fromisoformat(expiry_date_str)
        days_left = (expiry_date - datetime.now()).days
        return max(0, days_left)
    except:
        return 0

def get_username(user_id):
    cursor.execute("SELECT username FROM users WHERE user_id=%s", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else f"User_{user_id}"

def ban_user(user_id, reason="Scam/fraud"):
    username = get_username(user_id)
    cursor.execute("INSERT INTO banned_users VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET username=%s, ban_date=%s, reason=%s",
                   (user_id, username, datetime.now().isoformat(), reason, username, datetime.now().isoformat(), reason))
    cursor.execute("UPDATE users SET status='banned' WHERE user_id=%s", (user_id,))
    cursor.execute("DELETE FROM pending_approvals WHERE user_id=%s", (user_id,))
    conn.commit()
    return username

# ========== GRUPNE PORUKE (14 SATI) ==========
def send_group_message():
    group_messages = [
        """📱 *Quick Access Guide:*
1. Message @MiaAnthBot
2. Send /start
3. View all exclusive content!

Updated daily just for you 💋""",
        """🔔 *REMINDER: Content Available!*

Don't forget your private access:
👉 @MiaAnthBot

New set dropping tonight! 🌶️""",
    ]
    
    message = random.choice(group_messages)
    
    try:
        bot.send_message(MAIN_GROUP_ID, message, parse_mode='Markdown')
        print(f"📨 [GROUP] Message sent at {datetime.now().strftime('%H:%M')}")
        return True
    except Exception as e:
        print(f"⚠️  Group message error: {e}")
        return False

# ========== USER COMMANDS ==========
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    
    cursor.execute("SELECT * FROM banned_users WHERE user_id=%s", (user_id,))
    if cursor.fetchone():
        safe_send_message(message.chat.id, "🚫 *ACCESS DENIED*\nYou have been permanently banned.")
        return
    
    username = message.from_user.username or "User"
    safe_username = escape_markdown(username)
    
    welcome_text = f"""🌸 *Hello {safe_username}!* 🌸

*Welcome to Mia Anth's Exclusive World*

⭐ *FREE PUBLIC GROUP:* (Always open!)
{MAIN_GROUP_LINK}

💰 *PRIVATE PREMIUM CONTENT:*
• Price: $12.99 / {SUBSCRIPTION_DAYS} days
• Daily exclusive photos/videos
• Uncensored content
• Personal interaction

📋 *HOW TO GET PREMIUM ACCESS:*
1. Send $12.99 to PayPal: *{YOUR_PAYPAL}*
2. Send payment screenshot here
3. Wait for admin approval
4. Receive instant access!

🚫 *Fake screenshots = permanent ban*
✅ *Approval: As soon as possible*

💋 *Ready for the exclusive experience?*"""
    
    safe_send_message(message.chat.id, welcome_text)

@bot.message_handler(commands=['status'])
def check_status(message):
    user_id = message.from_user.id
    
    cursor.execute("SELECT * FROM banned_users WHERE user_id=%s", (user_id,))
    if cursor.fetchone():
        return
    
    cursor.execute("SELECT expiry_date, status FROM users WHERE user_id=%s", (user_id,))
    result = cursor.fetchone()
    
    if not result:
        status_text = f"""📊 *SUBSCRIPTION STATUS*

❌ *No premium subscription*
⭐ *Free group:* {MAIN_GROUP_LINK}
💰 *Premium:* $12.99 / {SUBSCRIPTION_DAYS} days"""
    
    elif result[1] == 'pending':
        status_text = """⏳ *SUBSCRIPTION STATUS*

🔄 *Waiting for admin approval*
✅ Admin will verify *as soon as possible*"""
    
    elif result[1] == 'active':
        expiry_date, _ = result
        days_left = days_until_expiry(expiry_date)
        try:
            expiry_formatted = datetime.fromisoformat(expiry_date).strftime('%d %B %Y')
        except:
            expiry_formatted = "Unknown"
        
        status_text = f"""✅ *PREMIUM SUBSCRIPTION ACTIVE*

⏳ Days remaining: *{days_left} days*
📆 Expiry date: *{expiry_formatted}*
🔗 Private access: ✅ Granted

⭐ *Free group:* {MAIN_GROUP_LINK}"""
    
    elif result[1] == 'expired':
        status_text = f"""❌ *SUBSCRIPTION EXPIRED*

💳 Send new payment to renew premium!
⭐ *Free group:* {MAIN_GROUP_LINK}"""
    
    safe_send_message(message.chat.id, status_text)

@bot.message_handler(commands=['main'])
def send_main_group_link(message):
    safe_send_message(message.chat.id,
                    f"⭐ *MIA ANTH'S PUBLIC GROUP:*\n\n"
                    f"{MAIN_GROUP_LINK}\n\n"
                    f"Always open! Join for free content 💋")

@bot.message_handler(content_types=['photo'])
def handle_payment_screenshot(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"User_{user_id}"
    safe_username = escape_markdown(username)
    
    cursor.execute("SELECT * FROM banned_users WHERE user_id=%s", (user_id,))
    if cursor.fetchone():
        safe_send_message(message.chat.id, "🚫 You are banned.")
        return
    
    cursor.execute("SELECT * FROM pending_approvals WHERE user_id=%s", (user_id,))
    if cursor.fetchone():
        safe_send_message(message.chat.id,
                        "⏳ *Already pending approval!*\n"
                        "Admin will check *as soon as possible*.")
        return
    
    print(f"📸 Screenshot from: @{username}")
    
    cursor.execute("INSERT INTO pending_approvals VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET username=%s, request_time=%s",
                   (user_id, username, datetime.now().isoformat(), username, datetime.now().isoformat()))
    conn.commit()
    
    # Poruka za korisnika
    user_message = f"""✅ *Screenshot Received!*

⏳ *Waiting for admin verification...*

✅ Admin will check *as soon as possible*.

⭐ *While you wait, join free group:*
{MAIN_GROUP_LINK}

⚠️ *Important:*
• Only REAL payment proofs
• Fake = permanent ban"""
    
    safe_send_message(message.chat.id, user_message)
    
    # Najveća rezolucija slike
    photo_file_id = message.photo[-1].file_id
    
    # Caption za sliku
    caption = f"""🔄 *PAYMENT VERIFICATION NEEDED*

👤 User: @{safe_username}
🆔 ID: `{user_id}`
💰 Amount: $12.99
⏰ Time: {datetime.now().strftime('%H:%M:%S')}

*ADMIN ACTIONS:*
✅ Approve: `/approve_{user_id}`
❌ Reject: `/reject_{user_id}`"""
    
    # Šaljemo sliku adminima
    notified = notify_admins_with_photo(photo_file_id, caption)
    print(f"🔄 Pending: @{username} | Photo sent to {notified} admin(s)")

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=['stats'])
def show_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE status='active'")
    active = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM pending_approvals")
    pending = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM banned_users")
    banned = cursor.fetchone()[0] or 0
    
    stats_text = f"""📊 *ADMIN DASHBOARD*

✅ Premium subscribers: {active}
⏳ Pending approvals: {pending}
🚫 Banned users: {banned}
💰 Monthly revenue: ${active * 12.99}

⭐ *Main Group:* {MAIN_GROUP_LINK}
👑 *Total admins:* {len(ADMIN_IDS)}"""
    
    safe_send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['pending'])
def show_pending(message):
    if not is_admin(message.from_user.id):
        return
    
    cursor.execute("SELECT username, user_id FROM pending_approvals")
    pending = cursor.fetchall()
    
    if not pending:
        safe_send_message(message.chat.id, "✅ No pending approvals.")
        return
    
    pending_text = "⏳ *PENDING APPROVALS*\n\n"
    for username, user_id in pending[:15]:
        safe_username = escape_markdown(username)
        pending_text += f"• @{safe_username} (ID: `{user_id}`)\n"
        pending_text += f"  ✅ `/approve_{user_id}` | ❌ `/reject_{user_id}`\n\n"
    
    safe_send_message(message.chat.id, pending_text)

@bot.message_handler(commands=['send_group'])
def send_group_now(message):
    if not is_admin(message.from_user.id):
        return
    
    if send_group_message():
        safe_send_message(message.chat.id, "✅ Message sent to group!")
    else:
        safe_send_message(message.chat.id, "❌ Failed to send message.")

@bot.message_handler(commands=['announce'])
def announce_to_group(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        announcement_text = message.text.replace('/announce', '').strip()
        
        if not announcement_text:
            safe_send_message(message.chat.id, "📝 Usage: /announce <message>")
            return
        
        full_message = f"""📢 *ADMIN ANNOUNCEMENT*

{announcement_text}

⭐ *Group:* {MAIN_GROUP_LINK}
🤖 *Bot:* @MiaAnthBot"""
        
        bot.send_message(MAIN_GROUP_ID, full_message, parse_mode='Markdown')
        safe_send_message(message.chat.id, f"✅ Announcement sent to group!\nGroup ID: {MAIN_GROUP_ID}")
        
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ Error: {e}")

@bot.message_handler(commands=['admins'])
def list_admins(message):
    if not is_admin(message.from_user.id):
        return
    
    admin_list = "👑 *ACTIVE ADMINS*\n\n"
    for i, admin_id in enumerate(ADMIN_IDS, 1):
        admin_list += f"{i}. `{admin_id}`\n"
    
    admin_list += f"\nTotal: {len(ADMIN_IDS)} admin(s)"
    safe_send_message(message.chat.id, admin_list)

@bot.message_handler(func=lambda message: message.text and message.text.startswith('/approve_'))
def approve_user(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.split('_')[1])
        
        cursor.execute("SELECT username FROM pending_approvals WHERE user_id=%s", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            safe_send_message(message.chat.id, "❌ User not in pending list.")
            return
        
        username = result[0]
        safe_username = escape_markdown(username)
        expiry_date = calculate_expiry_date()
        expiry_formatted = datetime.fromisoformat(expiry_date).strftime('%d %B %Y')
        
        cursor.execute('''INSERT INTO users 
                          (user_id, username, payment_date, expiry_date, status, used_invite) 
                          VALUES (%s, %s, %s, %s, %s, %s)
                          ON CONFLICT (user_id) DO UPDATE SET 
                          username=%s, payment_date=%s, expiry_date=%s, status=%s, used_invite=%s''',
                       (user_id, username, datetime.now().isoformat(), expiry_date, 'active', 0,
                        username, datetime.now().isoformat(), expiry_date, 'active', 0))
        
        cursor.execute("DELETE FROM pending_approvals WHERE user_id=%s", (user_id,))
        conn.commit()
        
        user_message = f"""✅ *PAYMENT APPROVED!*

🎉 *Welcome to Mia Anth's Premium Club!*

🔗 *YOUR PRIVATE ACCESS LINK:*
{PRIVATE_CHANNEL_LINK}

⚠️ *IMPORTANT:*
• Click the link *IMMEDIATELY*
• Works *ONLY ONCE* (1 use only)
• Expires in *24 HOURS*

⭐ *Free Public Group:* {MAIN_GROUP_LINK}
📅 *Premium expires:* {expiry_formatted}

🔄 *Check status:* /status
💋 *Enjoy the exclusive experience!*"""
        
        safe_send_message(user_id, user_message)
        
        approval_msg = f"""✅ *PAYMENT APPROVED BY ADMIN*

👤 User: @{safe_username}
🆔 ID: `{user_id}`
👑 Approved by: `{message.from_user.id}`
📅 Expires: {expiry_formatted}"""
        
        # Obaveštava sve admine o odobrenju
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, approval_msg, parse_mode='Markdown')
            except:
                pass
        
        safe_send_message(message.chat.id,
                     f"✅ *APPROVED*\n"
                     f"👤 @{safe_username}\n"
                     f"📅 Expires: {expiry_formatted}")
        
        print(f"✅ Approved: @{username} by admin {message.from_user.id}")
        
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ Error: {e}")

@bot.message_handler(func=lambda message: message.text and message.text.startswith('/reject_'))
def reject_user(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.split('_')[1])
        username = get_username(user_id)
        safe_username = escape_markdown(username)
        
        banned_username = ban_user(user_id, "Fake payment")
        
        cursor.execute("DELETE FROM pending_approvals WHERE user_id=%s", (user_id,))
        conn.commit()
        
        try:
            safe_send_message(user_id,
                            "🚫 *PAYMENT REJECTED*\n\n"
                            "Reason: Suspected fraud/fake payment\n\n"
                            "You are now permanently banned.\n\n"
                            f"⭐ Free group still available: {MAIN_GROUP_LINK}")
        except:
            pass
        
        reject_msg = f"""🚫 *PAYMENT REJECTED BY ADMIN*

👤 User: @{safe_username}
🆔 ID: `{user_id}`
👑 Rejected by: `{message.from_user.id}`
🗑️ Reason: Fake payment"""
        
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, reject_msg, parse_mode='Markdown')
            except:
                pass
        
        safe_send_message(message.chat.id,
                     f"🚫 *REJECTED & BANNED*\n"
                     f"👤 @{safe_username}")
        
        print(f"🚫 Banned: @{banned_username} by admin {message.from_user.id}")
        
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ Error: {e}")

# ========== FLASK SERVER FOR RENDER ==========
print("\n🌐 Starting Flask server for Render...")

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Mia Anth Bot is running!"

@app.route('/health')
def health():
    return "🟢 Bot is healthy", 200

@app.route('/ping')
def ping():
    return "pong", 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    print(f"🌍 Flask server starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

# Pokreni Flask u pozadini
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()
print(f"✅ Flask server started on port {os.environ.get('PORT', 8080)}")

# ========== MAIN LOOP ==========
print("\n" + "=" * 60)
print("✅ BOT IS READY")
print(f"⭐ MAIN GROUP ID: {MAIN_GROUP_ID}")
print(f"👑 ADMIN COUNT: {len(ADMIN_IDS)}")
print("=" * 60)
print("\n📱 USER COMMANDS:")
print("   /start - Welcome & options")
print("   /status - Check subscription")
print("   /main - Free group link")
print("\n👑 ADMIN COMMANDS:")
print("   /stats - Dashboard")
print("   /pending - Pending approvals")
print("   /admins - List all admins")
print("   /send_group - Send message to group now")
print("   /announce <text> - Announce to group")
print("   /approve_USERID - Approve payment")
print("   /reject_USERID - Reject & ban")
print("\n⏰ AUTO-FEATURES:")
print("   • Group messages every 14 hours")
print("   • All admins get PAYMENT SCREENSHOTS")
print("=" * 60)
print("\n⏳ Starting Telegram bot polling...")

# Tajmer za grupu
last_group_message = datetime.now()

# Pokreni Telegram bota u glavnoj niti
try:
    # Pokreni polling
    bot.polling(none_stop=True, interval=2, timeout=30)
    
    # Ova petlja se izvršava dok bot radi
    while True:
        # Grupna poruka svakih 14 sati
        if (datetime.now() - last_group_message).seconds >= 50400:  # 14 sati = 50400 sekundi
            if send_group_message():
                last_group_message = datetime.now()
        
        # Proveri na svakih 5 minuta
        time.sleep(300)
        
except Exception as e:
    print(f"❌ Bot crashed: {e}")
    print("🔄 Restarting in 10 seconds...")
    time.sleep(10)
