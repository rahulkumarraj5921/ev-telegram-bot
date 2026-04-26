import os
import re
import base64
import threading
import sys
import traceback
import asyncio
from flask import Flask
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- KEYS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- WEB SERVER (For Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Telegram Smart Bot is Live and Running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- BOT LOGIC ---
user_sessions = {}
client = None 

# 🧠 NAYA DIMAAG: Ekdum WhatsApp bot wala (Human-like & Smart)
system_instruction = """
Role: You are a highly intelligent, thoughtful, and friendly human-like companion. 
Creator/Identity Rule: Agar koi aapse puche ki "tumhe kisne banaya hai", "tumhare developer kaun hain", ya "tumhara baap kaun hai", toh hamesha garv se yahi reply dena: "मुझे Rahul Kumar Raj (Government Polytechnic Nawada) ने बनाया है!"
Rules for your behavior:
1. Act Like a Human: Talk naturally, empathetically, and logically like a smart human mentor/friend. NEVER say "I am an AI", "I am a large language model", or act like a robot.
2. Context Aware: Remember the user's previous messages in the conversation and reply accordingly.
3. Variety: Never repeat the exact same response or robotic phrases. Be dynamic, creative, and natural in your wording.
4. Thoughtful Answers: Think carefully before answering. Give practical, detailed, and accurate answers on ANY topic (coding, science, casual chat, etc.).
5. Language: Communicate naturally in conversational Hindi/Hinglish (like WhatsApp chats), unless asked in English.
6. Formatting: Use short paragraphs and simple plain text. NEVER use LaTeX.
"""

def split_text(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 🎓 NAYA WELCOME MESSAGE
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🌟 **Welcome to your Smart AI Assistant!** 🚀\n\n"
        "Hello! मैं एक एडवांस और दोस्ताना AI हूँ, बिल्कुल एक इंसान की तरह।\n\n"
        "आप मुझसे कुछ भी पूछ सकते हैं—चाहे वो कोडिंग हो, पढ़ाई हो, या बस ऐसे ही कोई गपशप! अपना सवाल टाइप करें और भेजें। 👇\n\n"
        "👨‍💻 **Developer:** Rahul Kumar Raj (GP Nawada)\n\n"
        "*(पुरानी बातें भुलाकर नया टॉपिक शुरू करने के लिए /clear टाइप करें)*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_sessions:
        del user_sessions[chat_id]
    await update.message.reply_text("🧹 मैंने पुरानी बातें भुला दी हैं! चलिए कोई नया टॉपिक शुरू करते हैं।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.caption or update.message.text or "Is image me kya hai?"

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    # Memory Check
    if chat_id not in user_sessions:
        user_sessions[chat_id] = [{"role": "system", "content": system_instruction}]

    # Memory Limit (Delete oldest if history is too long)
    if len(user_sessions[chat_id]) > 15:
        del user_sessions[chat_id][1:3]

    file_path = None
    try:
        if update.message.photo:
            await update.message.reply_text("फोटो मिल गई! मैं इसे देख रहा हूँ... 👀")
            photo_file = await update.message.photo[-1].get_file()
            file_path = f"temp_{chat_id}.jpg"
            await photo_file.download_to_drive(file_path)
            base_path = f"data:image/jpeg;base64,{encode_image(file_path)}"
            user_sessions[chat_id].append({"role": "user", "content": [{"type": "text", "text": user_text}, {"type": "image_url", "image_url": {"url": base_path}}]})
        else:
            user_sessions[chat_id].append({"role": "user", "content": user_text})
            
        # API Call with WhatsApp bot settings (temperature 0.85, frequency_penalty 0.5)
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini", 
            messages=user_sessions[chat_id],
            temperature=0.85,
            frequency_penalty=0.5
        )
        
        raw_reply_text = response.choices[0].message.content
        user_sessions[chat_id].append({"role": "assistant", "content": raw_reply_text})
        
        reply_text = raw_reply_text.replace('\\[', '').replace('\\]', '')
        
        if len(reply_text) > 4000:
             for chunk in split_text(reply_text):
                await update.message.reply_text(chunk, parse_mode='Markdown')
        else:
            try:
                await update.message.reply_text(reply_text, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(reply_text)
                
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: `{str(e)}`", parse_mode='Markdown')
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    global client
    print("🔄 Bot start ho raha hai...", flush=True)

    if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
        print("❌ FATAL ERROR: API Keys missing!", flush=True)
        sys.exit(1)

    try:
        client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )

        threading.Thread(target=run_flask, daemon=True).start()
        print("✅ Web Server started!", flush=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("clear", clear_memory))
        application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
        
        print("🚀 SMART BOT IS LIVE NOW!", flush=True)
        application.run_polling()
        
    except Exception as e:
        print(f"❌ CRITICAL CRASH: {e}", flush=True)
        traceback.print_exc()

if __name__ == '__main__':
    main()
