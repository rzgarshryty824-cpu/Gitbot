import requests, zipfile, tempfile, os, base64, time, sqlite3, random, string, shutil, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ===== تنظیمات =====
TOKEN = "8768875388:AAGqRey6F0VLbRSlim6Pm0EFQQyrqR5d5-c"
GITHUB_TOKEN = "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"
USERNAME = "rzgarshryty824-cpu"
ADMINS = [6830764999]
CHANNEL_USERNAME = "kunfigs"
CHANNEL_ID = -1003344438918
PROXY = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== دیتابیس =====
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER UNIQUE,
                 username TEXT,
                 sites_count INTEGER DEFAULT 0,
                 created_at TEXT
              )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sites (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 repo_name TEXT,
                 link TEXT,
                 created_at TEXT
              )''')
    conn.commit()
    conn.close()

def save_user(user_id, username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)", 
             (user_id, username, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def save_site(user_id, repo_name, link):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO sites (user_id, repo_name, link, created_at) VALUES (?, ?, ?, ?)", 
             (user_id, repo_name, link, datetime.now().isoformat()))
    c.execute("UPDATE users SET sites_count = sites_count + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT sites_count FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_all_stats():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM sites")
    total_sites = c.fetchone()[0]
    c.execute("SELECT SUM(sites_count) FROM users")
    total_builds = c.fetchone()[0] or 0
    conn.close()
    return total_users, total_sites, total_builds

def get_top_users(limit=5):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, sites_count FROM users ORDER BY sites_count DESC LIMIT ?", (limit,))
    result = c.fetchall()
    conn.close()
    return result

# ===== Session گیت‌هاب =====
def get_github_session():
    session = requests.Session()
    if PROXY:
        session.proxies = {'http': PROXY, 'https': PROXY}
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 408])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

github_session = get_github_session()

# ===== چک کردن جوین =====
async def check_membership(update: Update, context):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def join_required(update: Update, context):
    keyboard = [[InlineKeyboardButton("📢 جوین کانال", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")]]
    await update.message.reply_text(f"🔒 برای استفاده از ربات ابتدا در کانال {CHANNEL_USERNAME} عضو شوید!",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

# ===== شروع =====
async def start(update: Update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username or "کاربر"
    if not await check_membership(update, context):
        await join_required(update, context)
        return
    save_user(user_id, username)
    keyboard = [[InlineKeyboardButton("📤 ارسال پروژه", callback_data="send_project")],
                [InlineKeyboardButton("📊 آمار من", callback_data="my_stats")],
                [InlineKeyboardButton("❓ راهنما", callback_data="help")]]
    if user_id in ADMINS:
        keyboard.append([InlineKeyboardButton("🔐 پنل مدیریت", callback_data="admin_panel")])
    await update.message.reply_text(f"👋 سلام {username}! به ربات سایت‌آرا خوش اومدی! 🚀", 
                                    reply_markup=InlineKeyboardMarkup(keyboard))

# ===== Callback =====
async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data != "check_join" and not await check_membership(update, context):
        await query.edit_message_text("🔒 لطفاً ابتدا در کانال عضو شوید!")
        return
    if query.data == "check_join":
        if await check_membership(update, context):
            await query.edit_message_text("✅ عضویت تأیید شد! /start رو بزن.")
        else:
            await query.edit_message_text("❌ هنوز عضو نشدید!")
        return
    elif query.data == "send_project":
        await query.edit_message_text("📤 فایل پروژه‌ات (ZIP یا HTML) رو بفرست.")
    elif query.data == "my_stats":
        await query.edit_message_text(f"📊 شما {get_user_stats(user_id)} سایت ساخته‌اید.")
    elif query.data == "help":
        await query.edit_message_text("❓ راهنما:\n1️⃣ فایل ZIP یا HTML بفرست\n2️⃣ ربات آپلود می‌کند\n3️⃣ لینک Pages دریافت کن")
    elif query.data == "admin_panel":
        keyboard = [[InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats")],
                    [InlineKeyboardButton("👥 کاربران برتر", callback_data="admin_top")],
                    [InlineKeyboardButton("🌐 ۵ سایت آخر", callback_data="admin_recent")]]
        await query.edit_message_text("🔐 پنل مدیریت:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith("admin_"):
        if user_id not in ADMINS:
            await query.edit_message_text("❌ دسترسی غیرمجاز!")
            return
        if query.data == "admin_stats":
            u, s, b = get_all_stats()
            await query.edit_message_text(f"👥 کاربران: {u}\n🌐 سایت‌ها: {s}\n📦 کل ساخت‌ها: {b}")
        elif query.data == "admin_top":
            users = get_top_users(10)
            text = "🏆 ۱۰ کاربر برتر:\n" + "\n".join(f"{i}. @{u or 'ناشناس'} - {c} سایت" for i, (_, u, c) in enumerate(users, 1))
            await query.edit_message_text(text)
        elif query.data == "admin_recent":
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT link, created_at FROM sites ORDER BY created_at DESC LIMIT 5")
            sites = c.fetchall()
            conn.close()
            text = "🌐 ۵ سایت آخر:\n" + "\n".join(f"{i}. {link}\n   🕐 {created[:10]}" for i, (link, created) in enumerate(sites, 1))
            await query.edit_message_text(text)

# ===== پردازش فایل =====
async def handle_file(update: Update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username or "کاربر"
    if not await check_membership(update, context):
        await update.message.reply_text("🔒 لطفاً ابتدا در کانال عضو شوید!")
        return
    save_user(user_id, username)
    if not update.message.document:
        await update.message.reply_text("❌ لطفاً یه فایل بفرست!")
        return
    doc = update.message.document
    file_name = doc.file_name or ""
    if not (file_name.endswith('.zip') or file_name.endswith('.html') or file_name.endswith('.htm')):
        await update.message.reply_text("❌ فقط فایل‌های ZIP یا HTML قبوله!")
        return
    if doc.file_size > 25 * 1024 * 1024:
        await update.message.reply_text("❌ حجم فایل بیشتر از 25MB هست!")
        return
    msg = await update.message.reply_text("⏳ ۰% - شروع پردازش...")
    try:
        file = await doc.get_file()
        with tempfile.NamedTemporaryFile(suffix='.zip' if file_name.endswith('.zip') else '.html', delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name
        await msg.edit_text("⏳ ۲۵% - فایل دانلود شد...")
        if not file_name.endswith('.zip'):
            temp_dir = tempfile.mkdtemp()
            os.rename(tmp_path, os.path.join(temp_dir, 'index.html'))
            zip_path = f"{tempfile.gettempdir()}/{int(time.time())}.zip"
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(os.path.join(temp_dir, 'index.html'), 'index.html')
            tmp_path = zip_path
            shutil.rmtree(temp_dir, ignore_errors=True)
        await msg.edit_text("⏳ ۵۰% - در حال ساخت ریپو...")
        repo_name = f"site-{user_id}-{int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        response = github_session.post("https://api.github.com/user/repos", headers=headers, json={"name": repo_name, "private": False}, timeout=60)
        if response.status_code != 201:
            await msg.edit_text(f"❌ خطا در ساخت ریپو: {response.json().get('message', 'خطای ناشناخته')}")
            return
        await msg.edit_text("⏳ ۷۰% - در حال آپلود فایل‌ها...")
        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            with tempfile.TemporaryDirectory() as extract_dir:
                zip_ref.extractall(extract_dir)
                uploaded, total_files = 0, 0
                for _, _, files in os.walk(extract_dir):
                    total_files += len(files)
                if total_files == 0:
                    await msg.edit_text("❌ فایلی برای آپلود پیدا نشد!")
                    return
                for root, _, files in os.walk(extract_dir):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        github_path = os.path.relpath(file_path, extract_dir)
                        with open(file_path, 'rb') as f:
                            content = base64.b64encode(f.read()).decode()
                        for branch in ['main', 'master']:
                            url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/contents/{github_path}"
                            response = github_session.put(url, headers=headers, json={"message": f"آپلود {github_path}", "content": content, "branch": branch}, timeout=60)
                            if response.status_code in [200, 201]:
                                uploaded += 1
                                break
                        await msg.edit_text(f"⏳ {70 + int((uploaded / total_files) * 25)}% - آپلود {uploaded}/{total_files}...")
        os.unlink(tmp_path)
        await msg.edit_text("⏳ ۹۵% - در حال فعال کردن Pages...")
        for branch in ['main', 'master']:
            response = github_session.post(f"https://api.github.com/repos/{USERNAME}/{repo_name}/pages", headers=headers, json={"source": {"branch": branch, "path": "/"}}, timeout=60)
            if response.status_code in [201, 204]:
                break
        time.sleep(2)
        link = f"https://{USERNAME}.github.io/{repo_name}/"
        save_site(user_id, repo_name, link)
        await msg.delete()
        await update.message.reply_text(f"✅ سایت شما ساخته شد! 🎉\n🔗 لینک: {link}\n📊 تعداد کل سایت‌های شما: {get_user_stats(user_id)}")
    except Exception as e:
        await msg.edit_text(f"❌ خطا: {str(e)}")

# ===== اجرا =====
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    print("🤖 ربات سایت‌آرا روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()      
