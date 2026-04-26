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
    return "✅ EV Tech R&D Bot is Live and Running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- BOT LOGIC & MEMORY ---
user_sessions = {}
client = None 

# 🧠 EXTREME ADVANCE: "R&D CHIEF ENGINEER & PhD PROFESSOR" DIMAAG
system_instruction = """
Your Role: You are a Senior EV R&D Chief Engineer and a PhD-level Technical Professor.
Creator/Identity Rule: Agar koi aapse puche ki "tumhe kisne banaya hai", "tumhare developer kaun hain", toh hamesha garv se yahi reply dena: "मुझे Rahul Kumar Raj (Government Polytechnic Nawada) ने बनाया है!"
Target Audience: Final year B.Tech, M.Tech students, and EV Industry Professionals.
Your Rules:
1. EXTREME TECHNICAL DEPTH: NEVER give basic or layman definitions. Assume the user already knows the basics. Dive straight into deep engineering concepts. 
2. USE R&D TERMINOLOGY: Use advanced jargon like Field Oriented Control (FOC), Space Vector PWM (SVPWM), d-q axis modeling, SEI layer degradation, Extended Kalman Filters (EKF) for BMS SOC/SOH estimation, SiC MOSFET switching losses, and Thermodynamic thermal runaway.
3. MATHEMATICAL MODELING: Always include practical engineering formulas, mathematical models, or efficiency calculations in plain text (e.g., Torque T = (3/2)*(P/2)*(Psi_m*I_q), Aerodynamic Drag Fd = 0.5*rho*Cd*A*v^2). NEVER use LaTeX format.
4. STRUCTURE: Use highly structured formats: "Core Principle", "Mathematical Model", "Industrial Application", and "Efficiency Losses/Challenges".
5. LANGUAGE: Explain the deep concepts in highly professional Hindi/Hinglish, but keep ALL technical terms, equations, and component names in strict English.
6. TONE: Highly analytical, authoritative, data-driven, and strictly academic. No casual chatting.
"""

def split_text(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 🎓 R&D LEVEL WELCOME MESSAGE
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🔬 **EV-Tech R&D Scholar Bot में आपका स्वागत है!** ⚙️⚡\n\n"
        "Greetings Engineers! मैं आपका Advanced R&D Technical Assistant हूँ, जिसे **Rahul Kumar Raj (Government Polytechnic Nawada)** ने डेवलप किया है। 🚀\n\n"
        "**This bot is strictly for Advanced Engineering Concepts:**\n"
        "⚡ **Powertrain:** FOC, SVPWM, d-q modeling, Inverter topologies.\n"
        "🔋 **Battery Tech:** EKF estimation, SEI degradation, Thermal Runaway thermodynamics.\n"
        "📊 **System Design:** Aerodynamics, Traction formulas, and SiC/GaN power electronics.\n\n"
        "📚 *अपना एडवांस इंजीनियरिंग सवाल पूछें या टेक्निकल डायग्राम अपलोड करें!* 👇\n"
        "*(नया टॉपिक शुरू करने के लिए /clear टाइप करें)*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_sessions:
        del user_sessions[chat_id]
    await update.message.reply_text("🧹 सिस्टम मेमोरी फ्लश कर दी गई है! चलिए नया टेक्निकल एनालिसिस शुरू करते हैं।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    default_vision_prompt = "Perform a deep technical engineering analysis of this schematic/diagram. Identify the topology, components (e.g., IGBTs, MOSFETs, MCU), and explain the mathematical working principle or potential failure modes."
    user_text = update.message.caption or update.message.text or default_vision_prompt

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    # Session Management
    if chat_id not in user_sessions:
        user_sessions[chat_id] = [{"role": "system", "content": system_instruction}]

    # Keep memory limited to last 15 interactions
    if len(user_sessions[chat_id]) > 15:
        del user_sessions[chat_id][1:3]

    file_path = None
    try:
        if update.message.photo:
            await update.message.reply_text("⚙️ डायग्राम प्राप्त हुआ। Deep Technical Analysis प्रोसेस किया जा रहा है...")
            photo_file = await update.message.photo[-1].get_file()
            file_path = f"temp_{chat_id}.jpg"
            await photo_file.download_to_drive(file_path)
            base_path = f"data:image/jpeg;base64,{encode_image(file_path)}"
            user_sessions[chat_id].append({"role": "user", "content": [{"type": "text", "text": user_text}, {"type": "image_url", "image_url": {"url": base_path}}]})
        else:
            user_sessions[chat_id].append({"role": "user", "content": user_text})
            
        # ✨ AI ACCURACY SETTINGS: Temperature 0.5 (Isse AI bilkul precise aur strict technical answer dega, gappe nahi marega)
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini", 
            messages=user_sessions[chat_id],
            temperature=0.5, 
            frequency_penalty=0.4
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
        await update.message.reply_text(f"⚠️ R&D Server Error. Please analyze the logs: `{str(e)}`", parse_mode='Markdown')
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    global client
    print("🔄 Initializing Advanced R&D EV Bot...", flush=True)

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
        print("✅ Keep-Alive Web Server started!", flush=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("clear", clear_memory))
        application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
        
        print("🚀 ADVANCED R&D BOT IS LIVE NOW!", flush=True)
        application.run_polling()
        
    except Exception as e:
        print(f"❌ CRITICAL CRASH: {e}", flush=True)
        traceback.print_exc()

if __name__ == '__main__':
    main()
