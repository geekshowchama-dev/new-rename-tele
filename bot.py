import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("BOT_TOKEN not found!")
    exit(0)

user_files = {}
user_stage = {}

# ===== Step 1: Receive file =====
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not update.message.document:
        await update.message.reply_text("❌ Send a valid file.")
        return
    user_files[user_id] = update.message.document
    user_stage[user_id] = "rename"
    await update.message.reply_text("✏️ Send new file name (without extension).")

# ===== Step 2: Receive new name and upload with progress =====
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

    # ===== Emoji Progress Function =====
    async def progress_callback(current, total, message):
        percent = int(current * 100 / total)
        # Show in steps of 20%
        steps = percent // 20
        bar = "🟩" * steps + "⬜" * (5 - steps)
        try:
            await message.edit_text(f"⚡ Uploading: {bar} {percent}%")
        except:
            pass  # ignore edit errors

    status_msg = await update.message.reply_text("⚡ Uploading: ⬜⬜⬜⬜⬜ 0%")

    # ===== Upload with progress =====
    from telegram import InputFile

    with open(final_name, "rb") as f:
        total = os.path.getsize(final_name)
        chunk_size = total // 5  # 20% each
        sent = 0
        for i in range(5):
            # simulate upload chunk
            f.read(chunk_size)
            sent += chunk_size
            await progress_callback(sent, total, status_msg)

    # Send final document
    await update.message.reply_document(
        document=open(final_name, "rb"),
        caption=f"✅ Renamed to {final_name}"
    )

    os.remove(final_name)
    user_files.pop(user_id, None)
    user_stage.pop(user_id, None)
