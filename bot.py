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

# --- SECURE API KEYS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- RENDER WEB SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ EV Tech Professor Bot is Live and Running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- BOT LOGIC & MEMORY ---
user_sessions = {}
client = None 

# 🧠 B.TECH / DIPLOMA LEVEL "EXPERT PROFESSOR" DIMAAG
system_instruction = """
Your Role: You are a highly qualified Senior EV Engineering Professor and Technical Expert.
Creator/Identity Rule: Agar koi aapse puche ki "tumhe kisne banaya hai", "tumhare developer kaun hain", toh hamesha garv se yahi reply dena: "मुझे Rahul Kumar Raj (Government Polytechnic Nawada) ने बनाया है!"
Target Audience: B.Tech and Diploma Engineering students.
Your Rules:
1. HIGH TECHNICAL DEPTH: Provide highly technical, detailed, and engineering-level answers. Do not give basic layman definitions. Use advanced engineering terminology (e.g., Thermodynamics, Power Electronics, Inverters, IGBTs/MOSFETs, BMS algorithms, Flux, Torque generation).
2. STRUCTURE: Use clear headings, bullet points, and step-by-step technical explanations suitable for university exams.
3. EQUATIONS & FORMULAS: Include relevant engineering formulas to explain concepts. NEVER use LaTeX. Write all formulas in simple plain text (e.g., Power (P) = V * I, Torque (T) = F * r).
4. LANGUAGE: Explain complex concepts in clear Hindi/Hinglish, but keep ALL technical terms, component names, and formulas in strict English.
5. TONE: Academic, professional, and highly informative, exactly like a strict university professor teaching a B.Tech class.
"""

def split_text(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 🎓 PROFESSIONAL WELCOME MESSAGE
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎓 **EV-Tech Engineering Bot में आपका स्वागत है!** ⚙️🔋\n\n"
        "Hello Engineers! मैं आपका AI Professor हूँ। यह बॉट खास तौर पर **Government Polytechnic Nawada** के छात्रों और B.Tech/Diploma Engineers की मदद के लिए बनाया गया है। 🚀\n\n"
        "**मैं आपकी किस प्रकार मदद कर सकता हूँ?**\n"
        "⚡ **Core Concepts:** Power Electronics, Motors, BMS, and Charging Protocols.\n"
        "📊 **Engineering Diagrams:** किसी भी सर्किट या मोटर के पार्ट की फोटो भेजें और उसका टेक्निकल एनालिसिस पाएं।\n"
        "🎓 **Exam & Placement:** इंटरव्यू के एडवांस सवाल और उनके इंजीनियरिंग लेवल के जवाब।\n\n"
        "👨‍💻 **Developer & Creator:** Rahul Kumar Raj\n\n"
        "📚 *अपना सवाल पूछें या फोटो भेजें! (पुराना सेशन डिलीट करने के लिए /clear इस्तेमाल करें)*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_sessions:
        del user_sessions[chat_id]
    await update.message.reply_text("🧹 Session memory clear कर दी गई है! चलिए कोई नया इंजीनियरिंग टॉपिक शुरू करते हैं।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    default_vision_prompt = "Provide a comprehensive technical engineering analysis of this image suitable for a B.Tech/Diploma student. Identify components, explain functions, or diagnose errors if possible."
    user_text = update.message.caption or update.message.text or default_vision_prompt

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    # Session Management
    if chat_id not in user_sessions:
        user_sessions[chat_id] = [{"role": "system", "content": system_instruction}]

    # Keep memory limited to last 15 interactions to prevent crashes
    if len(user_sessions[chat_id]) > 15:
        del user_sessions[chat_id][1:3]

    file_path = None
    try:
        if update.message.photo:
            await update.message.reply_text("⚙️ डायग्राम मिल गया है। Technical details एनालाइज की जा रही हैं...")
            photo_file = await update.message.photo[-1].get_file()
            file_path = f"temp_{chat_id}.jpg"
            await photo_file.download_to_drive(file_path)
            base_path = f"data:image/jpeg;base64,{encode_image(file_path)}"
            user_sessions[chat_id].append({"role": "user", "content": [{"type": "text", "text": user_text}, {"type": "image_url", "image_url": {"url": base_path}}]})
        else:
            user_sessions[chat_id].append({"role": "user", "content": user_text})
            
        # API Call - Temperature set to 0.7 for Technical Accuracy
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini", 
            messages=user_sessions[chat_id],
            temperature=0.7, 
            frequency_penalty=0.3
        )
        
        raw_reply_text = response.choices[0].message.content
        user_sessions[chat_id].append({"role": "assistant", "content": raw_reply_text})
        
        # Clean specific formatting that might break Telegram markdown
        clean_reply = raw_reply_text.replace('\\[', '').replace('\\]', '').replace('\\frac', '').replace('\\eta', 'η').replace('\\', '')
        
        # Send long messages in chunks
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
        await update.message.reply_text(f"⚠️ Technical Server Error. Please wait a moment and try again.\n`Error Info: {str(e)}`", parse_mode='Markdown')
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    global client
    print("🔄 Initializing EV Tech Bot Systems...", flush=True)

    if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
        print("❌ FATAL ERROR: API Keys are missing in Render Environment Variables!", flush=True)
        sys.exit(1)

    try:
        # Initialize OpenRouter Client
        client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://t.me/EV_Tech_Bot", 
                "X-OpenRouter-Title": "EV Engineering Scholar Bot" 
            }
        )

        # Start Flask Server for Render keep-alive
        threading.Thread(target=run_flask, daemon=True).start()
        print("✅ Keep-Alive Web Server started successfully!", flush=True)

        # Fix for "RuntimeError: There is no current event loop in thread 'MainThread'"
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Build and Start Telegram Bot
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("clear", clear_memory))
        application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
        
        print("🚀 B.TECH EV PROFESSOR BOT IS LIVE NOW!", flush=True)
        application.run_polling()
        
    except Exception as e:
        print(f"❌ CRITICAL CRASH: {e}", flush=True)
        traceback.print_exc()

if __name__ == '__main__':
    main()
