import os
import re
import base64
import threading
from flask import Flask
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ⚠️ SECURE KEYS: Ab keys yahan nahi, Render ki settings mein dalenge
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- RENDER DUMMY WEB SERVER ---
# Ye Render ko lagne dega ki ek website chal rahi hai, taaki wo bot ko crash na kare
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ EV Bot is Live and Running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
# -------------------------------

# OpenRouter Client Setup
client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://t.me/EV_Tech_Bot", 
        "X-OpenRouter-Title": "EV Engineering Scholar Bot" 
    }
)

user_sessions = {}

# 🧠 ADVANCED SYSTEM INSTRUCTIONS
system_instruction = """
Your Role: You are a Senior EV Engineering Professor and Industry Expert. 
Creator/Identity Rule: Agar koi aapse puche ki "tumhe kisne banaya hai", "tumhare developer kaun hain", toh hamesha garv se yahi reply dena: "मुझे Rahul Kumar Raj (Government Polytechnic Nawada) ने बनाया है!"
Target Audience: Engineering students (Diploma level).
Your Rules:
1. TECHNICAL DEPTH: Explain core principles (Thermodynamics, Power Electronics, Battery Chemistry) simply.
2. STRUCTURE: Use clear headings and bullet points. 
3. EQUATIONS: NEVER use LaTeX. Write all formulas in simple, plain text format.
4. LANGUAGE: Reply in Hindi/Hinglish, but keep technical terms in English.
"""

def split_text(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 🎓 WELCOME MESSAGE
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎓 **EV-Tech Scholar Bot में आपका स्वागत है!** ⚙️🔋\n\n"
        "नमस्ते Engineer! यह AI Assistant खास तौर पर Government Polytechnic Nawada के छात्रों के लिए बनाया गया है। 🚀\n\n"
        "👨‍💻 **Developer:** Rahul Kumar Raj\n\n"
        "📚 *अपना सवाल नीचे लिखें या डायग्राम की फोटो भेजें!*\n"
        "*(Memory clear करने के लिए /clear टाइप करें)*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_sessions:
        del user_sessions[chat_id]
    await update.message.reply_text("🧹 Session memory clear कर दी गई है!")

# MAIN CHAT LOGIC
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.caption or update.message.text or "Analyze this technical image."

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    if chat_id not in user_sessions:
        user_sessions[chat_id] = [{"role": "system", "content": system_instruction}]

    if len(user_sessions[chat_id]) > 15:
        del user_sessions[chat_id][1:3]

    file_path = None
    try:
        if update.message.photo:
            await update.message.reply_text("फोटो मिल गई है! Analyze किया जा रहा है... ⚙️🖼️")
            photo_file = await update.message.photo[-1].get_file()
            file_path = f"temp_img_{chat_id}.jpg"
            await photo_file.download_to_drive(file_path)
            
            base_path = f"data:image/jpeg;base64,{encode_image(file_path)}"
            user_sessions[chat_id].append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": base_path}}
                ]
            })
        else:
            user_sessions[chat_id].append({"role": "user", "content": user_text})
            
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini", 
            messages=user_sessions[chat_id],
            temperature=0.8, 
            frequency_penalty=0.5 
        )

        raw_reply_text = response.choices[0].message.content
        user_sessions[chat_id].append({"role": "assistant", "content": raw_reply_text})

        reply_text = raw_reply_text.replace('\\[', '').replace('\\]', '').replace('\\frac', '').replace('\\eta', 'η').replace('\\', '')
        
        if len(reply_text) > 4000:
             for chunk in split_text(reply_text):
                await update.message.reply_text(chunk, parse_mode='Markdown')
        else:
            try:
                await update.message.reply_text(reply_text, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(reply_text)
                
    except Exception as e:
        await update.message.reply_text(f"⚠️ API Error: `{str(e)}`", parse_mode='Markdown')
        
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
        print("❌ ERROR: API Keys missing. Please set Environment Variables!")
        return

    # 1. Start Flask Dummy Server in a background thread
    threading.Thread(target=run_flask, daemon=True).start()

    # 2. Start Telegram Bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_memory)) 
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    
    print("🚀 EV Telegram Bot is running on Render!")
    application.run_polling()

if __name__ == '__main__':
    main()

