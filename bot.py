import os
import re
import base64
import threading
import json
from flask import Flask
from openai import AsyncOpenAI
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") 

app = Flask(__name__)

@app.route('/')
def home():
    return "EV Tech Bot (Pro Version) is Live!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# OpenRouter Setup
client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://t.me/EV_Tech_Bot", 
        "X-OpenRouter-Title": "EV Engineering Scholar Bot" 
    }
)

# In-memory storage (Note: Render restart par ye clear ho jayega)
user_sessions = {}
user_memories = {} # Data yaad rakhne ke liye

# 🧠 ULTIMATE TECHNICAL SYSTEM PROMPT
system_instruction = """
Your Role: Senior EV Research Scientist & Technical Professor.
Creator: Rahul Kumar Raj (Government Polytechnic Nawada).

TARGET: Diploma Engineering Students.

STRICT RESPONSE RULES:
1. NO REPETITION: Har answer pichle answer se alag aur unique hona chahiye. Do not use the same introductory sentences.
2. EXTREME DETAIL: Sirf definition nahi, balki:
   - 🎯 Concept Explanation (Hinglish)
   - ⚙️ Technical Specs & Components (English)
   - 📉 Pros & Cons (Bullet points)
   - 🔄 Comparison (e.g., BLDC vs PMSM)
   - 💡 Industry Pro-Tip (Placement point of view se)
3. MEMORY UTILIZATION: Agar user ne kuch yaad rakhne ko kaha hai, toh apne answers ko us data ke hisab se personalize karein.
4. TECHNICAL TERMS: Hamesha English terms use karein (e.g., 'Braking' instead of 'Rukna').
5. NO LATEX: Use plain text for math (e.g., Torque = Force x Radius).
"""

# --- Helper Functions ---
def split_text(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 🎓 START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🚀 **EV-Tech Scholar Bot PRO v2.0** ⚙️\n\n"
        "नमस्ते Engineer! मैं अब पहले से ज़्यादा Detailed और Intelligent हूँ।\n\n"
        "**🌟 नए फीचर्स:**\n"
        "1. **Deep Analysis:** अब हर टॉपिक पर आपको गहरी जानकारी मिलेगी।\n"
        "2. **Memory:** मुझे कुछ भी याद रखने को कहें (जैसे: 'याद रखो मेरा नाम राहुल है') और मैं उसे भूलूंगा नहीं।\n"
        "3. **Interview Prep:** कंपनियों के हिसाब से technical answers।\n\n"
        "👨‍💻 **Dev:** Rahul Kumar Raj\n"
        "*(Memory clear करने के लिए /clear टाइप करें)*"
    )
    await update.message.reply_text(welcome, parse_mode='Markdown')

# 🧹 CLEAR MEMORY
async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_sessions[chat_id] = []
    user_memories[chat_id] = ""
    await update.message.reply_text("🧹 Sab kuch clear kar diya gaya hai! Main sab bhool gaya hoon.")

# 🛠️ MESSAGE HANDLER
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text or update.message.caption or ""

    # Memory feature: 'Yaad rakho' detection
    if "yaad rakho" in user_input.lower() or "remember" in user_input.lower():
        # Extract info to remember
        memory_data = user_input.replace("yaad rakho", "").replace("remember", "").strip()
        user_memories[chat_id] = user_memories.get(chat_id, "") + f" {memory_data}."
        await update.message.reply_text(f"✅ Theek hai, maine yaad kar liya: '{memory_data}'")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    # Session build-up
    if chat_id not in user_sessions:
        user_sessions[chat_id] = []
    
    # Inject persistent memory into system instruction
    current_memory = user_memories.get(chat_id, "Abhi tak kuch yaad nahi hai.")
    dynamic_system_prompt = f"{system_instruction}\n\nUSER SPECIFIC DATA (IMPORTANT): {current_memory}"

    messages = [{"role": "system", "content": dynamic_system_prompt}]
    messages.extend(user_sessions[chat_id][-10:]) # Sirf last 10 messages context ke liye
    
    # Handle Image/Text
    file_path = None
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        file_path = f"img_{chat_id}.jpg"
        await photo_file.download_to_drive(file_path)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_input or "Analyze this image technically."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(file_path)}"}}
            ]
        })
    else:
        messages.append({"role": "user", "content": user_input})

    try:
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages,
            temperature=0.7,         # Uniqueness aur accuracy ka balance
            presence_penalty=0.6,    # Naye concepts aur words lane ke liye
            frequency_penalty=0.5    # Baar-baar wahi word repeat na ho
        )

        reply = response.choices[0].message.content
        user_sessions[chat_id].append({"role": "user", "content": user_input})
        user_sessions[chat_id].append({"role": "assistant", "content": reply})

        # Format and send
        clean_reply = reply.replace('\\[', '').replace('\\]', '').replace('\\', '')
        
        if len(clean_reply) > 4000:
            for chunk in split_text(clean_reply):
                await update.message.reply_text(chunk, parse_mode='Markdown')
        else:
            try:
                await update.message.reply_text(clean_reply, parse_mode='Markdown')
            except:
                await update.message.reply_text(clean_reply)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: `{str(e)}`", parse_mode='Markdown')
    finally:
        if file_path and os.path.exists(file_path): os.remove(file_path)

def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_memory))
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    print("🚀 EV Tech Bot Pro is running...")
    application.run_polling()

if __name__ == '__main__':
    if TELEGRAM_BOT_TOKEN and OPENROUTER_API_KEY:
        main()
    else:
        print("Error: Missing API Keys in Environment Variables!")
