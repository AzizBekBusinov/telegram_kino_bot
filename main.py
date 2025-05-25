import logging
import random
import json
import os
from telegram import Update, InputMediaVideo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Application

CHANNELS_FILE = "channels.json"
# Token va URL
TOKEN = os.getenv("API_TOKEN")
WEBHOOK_URL = os.getenv("https://telegram-kino-bot.onrender.com/webhook")


# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Webhook orqali ishlayapman 😊")

def main():
    # Botni yaratish
    application = Application.builder().token(BOT_TOKEN).build()

    # Handler qo‘shamiz
    application.add_handler(CommandHandler("start", start))

    # Webhookni ishga tushiramiz
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),  # Render.com portni o'zi beradi
        webhook_url=WEBHOOK_URL,
        allowed_updates=Update.ALL_TYPES
    )

# Logger sozlamasi
logging.basicConfig(level=logging.INFO)

# Token va kanal ID lar
BOT_TOKEN = "7612425007:AAG_OwLhwXO0-QUqMlpLkCvtA4luxJfbRt0"
SOURCE_CHANNEL_ID = -1002537266083  # Maxfiy kanal ID
FORCE_SUB_CHANNEL = "@azeezbusinov"  # Majburiy obuna kanali

# Kodlar bazasi (post_id: video_id) saqlanadi
code_db = {}

# Video qo‘shilganda avtomatik kod yaratish
def generate_code():
    return str(random.randint(10000, 99999))

# Majburiy kanallar ro'yxatini fayldan o'qish
def load_channels():
    if not os.path.exists(CHANNELS_FILE):
        return []
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Majburiy kanallar ro'yxatini faylga yozish
def save_channels(channels):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4, ensure_ascii=False)

# Bot ishga tushganda kanallarni o'qib olish uchun global ro'yxat
force_sub_channels = load_channels()

# Kanal qo'shish komandasi
async def add_channel(update, context):
    user_id = update.effective_user.id
    if user_id != 1577699984:  # Admin ID
        await update.message.reply_text("Ruxsat yo‘q.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Foydalanish: /addchannel <kanal_username>")
        return

    channel = context.args[0]
    if channel in force_sub_channels:
        await update.message.reply_text("Bu kanal allaqachon ro‘yxatda.")
        return

    force_sub_channels.append(channel)
    save_channels(force_sub_channels)
    await update.message.reply_text(f"Kanal {channel} qo‘shildi.")

# Kanal o'chirish komandasi
async def remove_channel(update, context):
    user_id = update.effective_user.id
    if user_id != 1577699984:  # Admin ID
        await update.message.reply_text("Ruxsat yo‘q.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Foydalanish: /removechannel <kanal_username>")
        return

    channel = context.args[0]
    if channel not in force_sub_channels:
        await update.message.reply_text("Bunday kanal ro‘yxatda yo‘q.")
        return

    force_sub_channels.remove(channel)
    save_channels(force_sub_channels)
    await update.message.reply_text(f"Kanal {channel} ro‘yxatdan o‘chirildi.")

# Obuna tekshirish
async def check_subscription(user_id, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

# Maxfiy kanalga post qo‘shilganda ishga tushadi
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if message.video:
        code = generate_code()
        code_db[code] = message.message_id
        logging.info(f"Yangi video qo‘shildi. Kod: {code}, Post ID: {message.message_id}")

# Foydalanuvchi xabar yuborganda ishga tushadi
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not await check_subscription(user.id, context):
        await update.message.reply_text(
            f"Iltimos, avval {FORCE_SUB_CHANNEL} kanaliga obuna bo‘ling!",
            disable_web_page_preview=True
        )
        return

    if text in code_db:
        post_id = code_db[text]
        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=SOURCE_CHANNEL_ID,
            message_id=post_id
        )
    else:
        await update.message.reply_text("Bunday kod topilmadi.")

# Admin komandasi - barcha kodlarni ko‘rsatish
async def list_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Faqat sizga ruxsat beramiz (admin ID ni istasangiz tekshirib qo‘shish mumkin)
    if user_id != 1577699984:  # Bu yerga o‘z Telegram ID'ingizni yozing
        await update.message.reply_text("Kechirasiz, bu buyruq faqat admin uchun.")
        return

    if not code_db:
        await update.message.reply_text("Hozircha hech qanday kod mavjud emas.")
        return

    msg = "Aktiv kodlar:\n"
    for code, post_id in code_db.items():
        msg += f"- Kod: {code} | Post ID: {post_id}\n"
    await update.message.reply_text(msg)

# Kodni o‘chirish komandasi
async def delete_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != 1577699984:
        await update.message.reply_text("Ruxsat yo‘q.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Foydalanish: /del <kod>")
        return

    code = context.args[0]
    if code in code_db:
        del code_db[code]
        await update.message.reply_text(f"Kod {code} o‘chirildi.")
    else:
        await update.message.reply_text("Bunday kod mavjud emas.")

# Botni ishga tushurish
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.Chat(SOURCE_CHANNEL_ID), handle_channel_post))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("kodlar", list_codes))
    app.add_handler(CommandHandler("del", delete_code))
    app.add_handler(CommandHandler("addchannel", add_channel))
    app.add_handler(CommandHandler("removechannel", remove_channel))

    print("Bot ishga tushdi...")
    app.run_polling()


# Run
if __name__ == "__main__":
    main()

