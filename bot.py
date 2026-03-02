import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_files = {}
user_thumbs = {}
user_stage = {}

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_files[user_id] = update.message.document
    user_stage[user_id] = "thumb"
    await update.message.reply_text("🖼 Send thumbnail (optional). If none, send /skip")

async def receive_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_stage.get(user_id) == "thumb":
        photo = update.message.photo[-1]
        file = await photo.get_file()
        thumb_path = f"{user_id}_thumb.jpg"
        await file.download_to_drive(thumb_path)
        user_thumbs[user_id] = thumb_path
        user_stage[user_id] = "rename"
        await update.message.reply_text("✏️ Send new file name (without extension)")

async def skip_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_stage.get(user_id) == "thumb":
        user_stage[user_id] = "rename"
        await update.message.reply_text("✏️ Send new file name (without extension)")

async def receive_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_stage.get(user_id) != "rename":
        return

    document = user_files[user_id]
    new_name = update.message.text.strip()
    ext = os.path.splitext(document.file_name)[1]
    final_name = new_name + ext

    file = await document.get_file()
    await file.download_to_drive(final_name)

    await update.message.reply_document(
        document=open(final_name, "rb"),
        caption=f"✅ Renamed to {final_name}",
        thumbnail=user_thumbs.get(user_id)
    )

    os.remove(final_name)
    if user_id in user_thumbs:
        os.remove(user_thumbs[user_id])

    user_files.pop(user_id, None)
    user_thumbs.pop(user_id, None)
    user_stage.pop(user_id, None)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.Document.ALL, receive_file))
app.add_handler(MessageHandler(filters.PHOTO, receive_thumb))
app.add_handler(CommandHandler("skip", skip_thumb))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_name))

print("Bot is running...")
app.run_polling()
