import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
import pyrogram.errors

# ====== RAILWAY ENV VARIABLES ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

if not BOT_TOKEN or not API_ID or not API_HASH:
    print("❌ Missing BOT_TOKEN / API_ID / API_HASH")
    exit(0)

# ====== TIME SYNC FIX ======
try:
    os.environ["TZ"] = "Asia/Colombo"  # Change as needed
    time.tzset()
except Exception:
    pass  # tzset not available on some systems

# ====== CREATE CLIENT ======
app = Client(
    "rename_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ====== TEMP STORAGE ======
user_files = {}
user_thumbs = {}
user_stage = {}

# ====== /start MESSAGE ======
@app.on_message(filters.command("start"))
async def start_msg(client, message: Message):
    await message.reply(
        "👋 Hi! Send me a file to rename.\nOptional thumbnail: send /skip to skip."
    )

# ====== RECEIVE FILE ======
@app.on_message(filters.document)
async def receive_file(client, message: Message):
    user_id = message.from_user.id
    user_files[user_id] = message
    user_stage[user_id] = "thumb"
    await message.reply("🖼 Send thumbnail (optional) or /skip.")

# ====== RECEIVE THUMBNAIL ======
@app.on_message(filters.photo)
async def receive_thumb(client, message: Message):
    user_id = message.from_user.id
    if user_stage.get(user_id) != "thumb":
        return
    thumb_path = await message.download()
    user_thumbs[user_id] = thumb_path
    user_stage[user_id] = "rename"
    await message.reply("✏️ Send new file name (without extension).")

# ====== SKIP THUMBNAIL ======
@app.on_message(filters.command("skip"))
async def skip_thumb(client, message: Message):
    user_id = message.from_user.id
    if user_stage.get(user_id) == "thumb":
        user_stage[user_id] = "rename"
        await message.reply("✏️ Send new file name (without extension).")

# ====== RECEIVE NEW NAME & UPLOAD ======
@app.on_message(filters.text & ~filters.command("skip"))
async def receive_new_name(client, message: Message):
    user_id = message.from_user.id
    if user_stage.get(user_id) != "rename":
        return

    original_msg = user_files[user_id]
    new_name = message.text.strip()
    ext = os.path.splitext(original_msg.document.file_name)[1]
    final_name = new_name + ext

    status = await message.reply("⚡ Downloading...")

    # Download original file
    file_path = await original_msg.download(file_name=f"./{final_name}")

    # ===== Emoji progress bar 20% steps =====
    total_size = os.path.getsize(file_path)
    chunk_size = max(total_size // 5, 1)
    sent = 0
    progress_msg = await message.reply("⚡ Uploading: ⬜⬜⬜⬜⬜ 0%")
    for i in range(5):
        with open(file_path, "rb") as f:
            f.read(chunk_size)
        sent += chunk_size
        percent = int(sent * 100 / total_size)
        steps = min(percent // 20, 5)
        bar = "🟩" * steps + "⬜" * (5 - steps)
        try:
            await progress_msg.edit_text(f"⚡ Uploading: {bar} {percent}%")
        except:
            pass

    # ===== Upload renamed file =====
    thumb_path = user_thumbs.get(user_id)
    await message.reply_document(
        document=file_path,
        thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
        caption=f"✅ Renamed to {final_name}"
    )

    # ===== CLEANUP =====
    if os.path.exists(file_path):
        os.remove(file_path)
    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)
    user_files.pop(user_id, None)
    user_thumbs.pop(user_id, None)
    user_stage.pop(user_id, None)
    await status.delete()
    await progress_msg.delete()


# ====== RUN BOT WITH RETRY ======
while True:
    try:
        print("✅ Bot is running...")
        app.run()
    except pyrogram.errors.BadMsgNotification:
        print("⚠️ BadMsgNotification detected. Retrying in 5s...")
        time.sleep(5)
