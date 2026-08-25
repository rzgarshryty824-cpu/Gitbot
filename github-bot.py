import os
import logging
import requests
import zipfile
import tempfile
import shutil
import time
import base64  # <---- این رو اضافه کن
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== تنظیمات =====
TOKEN = "8768875388:AAGqRey6F0VLbRSlim6Pm0EFQQyrqR5d5-c"
GITHUB_TOKEN = "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"
USERNAME = "rzgarshryty824-cpu"
ADMINS = [6830764999]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== تابع آپلود روی گیت‌هاب =====
def upload_to_github(file_path, user_id):
    repo_name = f"site-{user_id}-{int(time.time())}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # ساخت ریپو
    response = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json={"name": repo_name, "private": False}
    )
    if response.status_code != 201:
        return None, f"❌ خطا در ساخت ریپو: {response.json().get('message', 'خطای ناشناخته')}"
    
    # آپلود فایل‌ها
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        with tempfile.TemporaryDirectory() as extract_dir:
            zip_ref.extractall(extract_dir)
            for root, _, files in os.walk(extract_dir):
                for file_name in files:
                    file_path_full = os.path.join(root, file_name)
                    github_path = os.path.relpath(file_path_full, extract_dir)
                    with open(file_path_full, 'rb') as f:
                        content = base64.b64encode(f.read()).decode()  # <---- اصلاح شد
                    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/contents/{github_path}"
                    response = requests.put(
                        url,
                        headers=headers,
                        json={
                            "message": f"آپلود {github_path}",
                            "content": content,
                            "branch": "main"
                        }
                    )
                    if response.status_code not in [200, 201]:
                        return None, f"❌ خطا در آپلود {github_path}: {response.json().get('message', 'خطای ناشناخته')}"
    
    # فعال‌سازی Pages
    requests.post(
        f"https://api.github.com/repos/{USERNAME}/{repo_name}/pages",
        headers=headers,
        json={"source": {"branch": "main", "path": "/"}}
    )
    time.sleep(2)
    return f"https://{USERNAME}.github.io/{repo_name}/", None

# ===== شروع =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 ارسال پروژه", callback_data="send_project")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")]
    ]
    await update.message.reply_text(
        "👋 سلام! به ربات **سایت‌آرا** خوش اومدی!\n"
        "من می‌تونم فایل‌های HTML/JS/CSS رو برات آنلاین کنم.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== دکمه‌ها =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "send_project":
        await query.edit_message_text("📤 لطفاً فایل ZIP پروژه‌ات رو بفرست.")
    elif query.data == "help":
        await query.edit_message_text(
            "❓ راهنما:\n"
            "1️⃣ یه فایل ZIP از پروژه‌ات بساز.\n"
            "2️⃣ برام بفرست.\n"
            "3️⃣ من لینک آنلاین رو برات می‌فرستم."
        )

# ===== دریافت فایل =====
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document
    
    if not doc.file_name.endswith('.zip'):
        await update.message.reply_text("❌ لطفاً فقط فایل ZIP بفرست!")
        return
    
    if doc.file_size > 25 * 1024 * 1024:
        await update.message.reply_text("❌ حجم فایل بیشتر از 25MB هست!")
        return
    
    msg = await update.message.reply_text("⏳ در حال پردازش...")
    
    try:
        file = await doc.get_file()
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name
        
        await msg.edit_text("⏳ در حال آپلود روی گیت‌هاب...")
        link, error = upload_to_github(tmp_path, user_id)
        
        if error:
            await msg.edit_text(error)
        else:
            await msg.edit_text(f"✅ سایت شما آنلاین شد! 🎉\n\n🔗 لینک: {link} توجه داشته باشید سایت شما بعد از 1 دقیقه فعال میشود و اگر حجم فایل شما زیاد باشد ممکن است 5 دقیقه یا بیشتر طول بکشد.")
        
        os.unlink(tmp_path)
    except Exception as e:
        await msg.edit_text(f"❌ خطا: {str(e)}")

# ===== اجرا =====
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    print("🤖 ربات سایت‌آرا روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()
