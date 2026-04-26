import os
import re
import base64
import threading
import sys
import traceback
from flask import Flask
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- KEYS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- WEB SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ EV Bot is Live and Running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- BOT LOGIC ---
user_sessions = {}
client = None 

system_instruction = """
Your Role: You are a Senior EV Engineering Professor and Industry Expert. 
Creator/Identity Rule: Agar koi aapse puche ki "tumhe kisne banaya hai", "tumhare developer kaun hain", toh hamesha garv se yahi reply dena: "मुझे Rahul Kumar Raj (Government Polytechnic Nawada) ने बनाया है!"
Target Audience: Engineering students (Diploma level).
Your Rules: Explain core EV principles simply. No LaTeX. Use Hindi/Hinglish.
"""

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎓 **EV-Tech Scholar Bot Online!** ⚙️\nमैं तैयार हूँ, अपना सवाल पूछें।", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.caption or update.message.text or "Analyze this."

    if chat_id not in user_sessions:
        user_sessions[chat_id] = [{"role": "system", "content": system_instruction}]

    if len(user_sessions[chat_id]) > 15:
        del user_sessions[chat_id][1:3]

    file_path = None
    try:
        if update.message.photo:
            await update.message.reply_text("⚙️ Analyzing image...")
            photo_file = await update.message.photo[-1].get_file()
            file_path = f"temp_{chat_id}.jpg"
            await photo_file.download_to_drive(file_path)
            base_path = f"data:image/jpeg;base64,{encode_image(file_path)}"
            user_sessions[chat_id].append({"role": "user", "content": [{"type": "text", "text": user_text}, {"type": "image_url", "image_url": {"url": base_path}}]})
        else:
            user_sessions[chat_id].append({"role": "user", "content": user_text})
            
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini", 
            messages=user_sessions[chat_id],
            temperature=0.8
        )
        reply_text = response.choices[0].message.content
        user_sessions[chat_id].append({"role": "assistant", "content": reply_text})
        
        await update.message.reply_text(reply_text.replace('\\[', '').replace('\\]', ''), parse_mode='Markdown')
                
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: `{str(e)}`", parse_mode='Markdown')
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    global client
    print("🔄 Bot start ho raha hai...", flush=True)

    # 1. Key Check
    if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
        print("❌ FATAL ERROR: API Keys missing! Render Settings me Keys check karein.", flush=True)
        sys.exit(1)

    try:
        # 2. Client Setup
        client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )

        # 3. Server Start
        threading.Thread(target=run_flask, daemon=True).start()
        print("✅ Web Server started!", flush=True)

        # 4. Bot Start
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
        
        print("🚀 BOT IS LIVE NOW! Waiting for messages...", flush=True)
        application.run_polling()
        
    except Exception as e:
        print(f"❌ CRITICAL CRASH: {e}", flush=True)
        traceback.print_exc()

if __name__ == '__main__':
    main()

