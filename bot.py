import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found!")
    exit(0)

# ===== Temporary storage =====
user_files = {}
user_thumbs = {}
user_stage = {}

# ===== Start command =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! Send me a file to rename. "
        "Optional: you can send a thumbnail. Use /skip to skip thumbnail."
    )

# ===== Step 1: Receive file =====
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not update.message.document:
        await update.message.reply_text("❌ Send a valid file.")
        return
    user_files[user_id] = update.message.document
    user_stage[user_id] = "thumb"
    await update.message.reply_text("🖼 Send thumbnail (optional) or /skip.")

# ===== Step 2: Receive thumbnail =====
async def receive_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_stage.get(user_id) != "thumb":
        return
    if not update.message.photo:
        await update.message.reply_text("❌ Send a valid photo or /skip.")
        return
    photo = update.message.photo[-1]
    file = await photo.get_file()
    thumb_path = f"{user_id}_thumb.jpg"
    await file.download_to_drive(thumb_path)
    user_thumbs[user_id] = thumb_path
    user_stage[user_id] = "rename"
    await update.message.reply_text("✏️ Send new file name (without extension).")

# ===== Step 2b: Skip thumbnail =====
async def skip_thumb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_stage.get(user_id) == "thumb":
        user_stage[user_id] = "rename"
        await update.message.reply_text("✏️ Send new file name (without extension).")

# ===== Step 3: Receive new name & upload with emoji progress =====
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

    # ===== Emoji progress bar =====
    status_msg = await update.message.reply_text("⚡ Uploading: ⬜⬜⬜⬜⬜ 0%")
    total_size = os.path.getsize(final_name)
    chunk_size = total_size // 5

    sent = 0
    for i in range(5):
        # simulate chunk read
        with open(final_name, "rb") as f:
            f.read(chunk_size)
        sent += chunk_size
        percent = int(sent * 100 / total_size)
        steps = percent // 20
        bar = "🟩" * steps + "⬜" * (5 - steps)
        try:
            await status_msg.edit_text(f"⚡ Uploading: {bar} {percent}%")
        except:
            pass

    # ===== Send final document =====
    thumb_file = user_thumbs.get(user_id)
    await update.message.reply_document(
        document=open(final_name, "rb"),
        caption=f"✅ Renamed to {final_name}",
        thumb=open(thumb_file, "rb") if thumb_file and os.path.exists(thumb_file) else None
    )

    # ===== Cleanup =====
    os.remove(final_name)
    if thumb_file and os.path.exists(thumb_file):
        os.remove(thumb_file)
    user_files.pop(user_id, None)
    user_thumbs.pop(user_id, None)
    user_stage.pop(user_id, None)
    await status_msg.delete()

# ===== Build app =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

# ===== Handlers =====
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, receive_file))
app.add_handler(MessageHandler(filters.PHOTO, receive_thumb))
app.add_handler(CommandHandler("skip", skip_thumb))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_name))

# ===== Run bot =====
print("✅ Bot is running...")
app.run_polling(drop_pending_updates=True, close_loop=False)
