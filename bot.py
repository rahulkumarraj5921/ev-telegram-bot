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
    return "✅ EV Tech Bot is Live and Running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- BOT LOGIC ---
user_sessions = {}
client = None 

# 🧠 ORIGINAL "EV PROFESSOR" DIMAAG
system_instruction = """
Your Role: You are a Senior EV Engineering Professor and Industry Expert. 
Creator/Identity Rule: Agar koi aapse puche ki "tumhe kisne banaya hai", "tumhare developer kaun hain", ya "tumhara baap kaun hai", toh hamesha garv se yahi reply dena: "मुझे Rahul Kumar Raj (Government Polytechnic Nawada) ने बनाया है!"
Target Audience: Engineering students (Diploma level).
Your Rules:
1. TECHNICAL DEPTH: Explain core principles (Thermodynamics, Power Electronics, Battery Chemistry, EV Infrastructure) in a way that is easy for Diploma students to understand.
2. STRUCTURE: Use clear headings and bullet points. 
3. EQUATIONS: NEVER use LaTeX. Write all formulas in simple, plain text format (e.g., Efficiency = (P_out / P_in) * 100). Use standard Unicode characters (Ω, η, Δ).
4. MULTIMODAL: Analyze uploaded technical diagrams like an engineer. Identify components and errors.
5. LANGUAGE: Reply in the exact language the user uses (Hindi, Hinglish, English), but keep technical terms in English.
6. EMOJIS: Use emojis naturally (🚗, 🔋, ⚡, ⚙️) to keep the interaction academic yet engaging.
"""

def split_text(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 🎓 ORIGINAL EV BOT WELCOME MESSAGE
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎓 **EV-Tech Scholar Bot में आपका स्वागत है!** ⚙️🔋\n\n"
        "नमस्ते Engineer! यह AI Assistant खास तौर पर Government Polytechnic Nawada के छात्रों और सभी Diploma Engineers के लिए बनाया गया है। 🚀\n\n"
        "Placement की टेंशन हो या Semester Exams की, Electric Vehicles के हर concept को अब हम मिलकर आसान बनाएंगे。\n\n"
        "**🛠️ मैं आपकी कैसे मदद कर सकता हूँ?**\n"
        "👉 **Deep Tech:** Thermodynamics, Motors और BMS की वर्किंग।\n"
        "👉 **Diagram Scan:** किसी भी circuit या पार्ट की फोटो भेजें और तुरंत analysis पाएं।\n"
        "👉 **Career Prep:** टॉप EV कंपनियों के इंटरव्यू सवाल।\n\n"
        "👨‍💻 **Developer:** Rahul Kumar Raj (Government Polytechnic Nawada)\n\n"
        "📚 *अपना सवाल नीचे लिखें या फोटो भेजें, और चलिए पढ़ाई शुरू करते हैं!*\n"
        "*(Memory clear करने के लिए किसी भी समय /clear टाइप करें)*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_sessions:
        del user_sessions[chat_id]
    await update.message.reply_text("🧹 Session memory clear कर दी गई है! चलिए कोई नया टॉपिक शुरू करते हैं।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    default_vision_prompt = "Provide a comprehensive technical engineering analysis of this image suitable for a Diploma student. Identify components, explain functions, or diagnose errors if possible."
    user_text = update.message.caption or update.message.text or default_vision_prompt

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    if chat_id not in user_sessions:
        user_sessions[chat_id] = [{"role": "system", "content": system_instruction}]

    if len(user_sessions[chat_id]) > 15:
        del user_sessions[chat_id][1:3]

    file_path = None
    try:
        if update.message.photo:
            await update.message.reply_text("फोटो मिल गई है! Technical data को analyze किया जा रहा है... ⚙️🖼️")
            photo_file = await update.message.photo[-1].get_file()
            file_path = f"temp_{chat_id}.jpg"
            await photo_file.download_to_drive(file_path)
            base_path = f"data:image/jpeg;base64,{encode_image(file_path)}"
            user_sessions[chat_id].append({"role": "user", "content": [{"type": "text", "text": user_text}, {"type": "image_url", "image_url": {"url": base_path}}]})
        else:
            user_sessions[chat_id].append({"role": "user", "content": user_text})
            
        # EV technical answers ke liye temperature 0.7 set kiya hai
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini", 
            messages=user_sessions[chat_id],
            temperature=0.7, 
            frequency_penalty=0.5
        )
        
        raw_reply_text = response.choices[0].message.content
        user_sessions[chat_id].append({"role": "assistant", "content": raw_reply_text})
        
        # Format cleaning
        clean_reply = raw_reply_text.replace('\\[', '').replace('\\]', '').replace('\\frac', '').replace('\\eta', 'η').replace('\\', '')
        
        if len(clean_reply) > 4000:
             for chunk in split_text(clean_reply):
                await update.message.reply_text(chunk, parse_mode='Markdown')
        else:
            try:
                await update.message.reply_text(clean_reply, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(clean_reply)
                
    except Exception as e:
        print(f"API Error: {e}")
        await update.message.reply_text(f"⚠️ Technical Error:\n`{str(e)}`", parse_mode='Markdown')
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
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://t.me/EV_Tech_Bot", 
                "X-OpenRouter-Title": "EV Engineering Scholar Bot" 
            }
        )

        threading.Thread(target=run_flask, daemon=True).start()
        print("✅ Web Server started!", flush=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("clear", clear_memory))
        application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
        
        print("🚀 EV PROFESSOR BOT IS LIVE NOW!", flush=True)
        application.run_polling()
        
    except Exception as e:
        print(f"❌ CRITICAL CRASH: {e}", flush=True)
        traceback.print_exc()

if __name__ == '__main__':
    main()
