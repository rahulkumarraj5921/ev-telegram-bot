import os
import re
import base64
import threading
from flask import Flask
from openai import AsyncOpenAI
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ⚠️ Render Environment Variables se keys fetch hongi
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") 

# Check agar keys set nahi hain toh warning print kare
if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
    print("⚠️ WARNING: TELEGRAM_BOT_TOKEN ya OPENROUTER_API_KEY Render Environment Variables me set nahi hai!")

# --- FLASK SERVER SETUP FOR RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "EV Tech Bot is running flawlessly on Render!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
# -------------------------------------

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

# 🧠 ADVANCED SYSTEM INSTRUCTIONS (For Diploma Engineers)
system_instruction = """
Your Role: You are an Elite Technical Professor and Industry Expert specializing in Electric Vehicles and core engineering.
Creator/Identity Rule: Agar koi aapse puche ki "tumhe kisne banaya hai", "tumhare developer kaun hain", ya "tumhara baap kaun hai", toh hamesha garv se yahi reply dena: "मुझे Rahul Kumar Raj (Government Polytechnic Nawada) ने बनाया है!"

Target Audience: Diploma Engineering Students who need practical, exam-oriented, and industry-ready knowledge.

YOUR STRICT RULES FOR ANSWERING:
1. LANGUAGE (HINGLISH): Explanation bilkul aasan Hindi-English mix (Hinglish) me honi chahiye. Lekin saare TECHNICAL TERMS, Definitions, aur Components ke naam pure English me hone chahiye.
2. TECHNICAL DEPTH & UNIQUENESS: Kitabi baaton ke bajaye 'Industrial Application' par focus karein. Explain karein ki "Ye component EV me kahan aur kyun use hota hai".
3. STRUCTURE: Answers ko in headings me divide karein (if applicable):
   - 🎯 Concept (Brief intro)
   - ⚙️ Working/Technical Details (Bullet points)
   - 🏭 Industrial Application (Real-world use case)
   - 📝 Quick Formula/Key Point (For exams)
4. EQUATIONS: NEVER use LaTeX. Write all formulas in simple, plain text format (e.g., Efficiency = (P_out / P_in) * 100). Use standard Unicode characters (Ω, η, Δ).
5. MULTIMODAL: Analyze uploaded diagrams like a senior engineer. Pinpoint specific flaws, circuit issues, or component functions accurately.
6. TONE: Professional, encouraging, aur strictly point-to-point. Faltu ki lambi baatein na karein.
"""

# --- Helper Functions ---
def split_text(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 🎓 PREMIUM WELCOME MESSAGE 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎓 **EV-Tech Scholar Bot में आपका स्वागत है!** ⚙️🔋\n\n"
        "नमस्ते Engineer! यह AI Assistant खास तौर पर Government Polytechnic Nawada के छात्रों और सभी Diploma Engineers के लिए बनाया गया है। 🚀\n\n"
        "Placement की टेंशन हो या Semester Exams की, Electric Vehicles के हर concept को अब हम मिलकर आसान बनाएंगे।\n\n"
        "**🛠️ मैं आपकी कैसे मदद कर सकता हूँ?**\n"
        "👉 **Deep Tech:** Thermodynamics, Motors और BMS की वर्किंग।\n"
        "👉 **Diagram Scan:** किसी भी circuit या पार्ट की फोटो भेजें और तुरंत analysis पाएं।\n"
        "👉 **Career Prep:** टॉप EV कंपनियों के इंटरव्यू सवाल।\n\n"
        "👨‍💻 **Developer:** Rahul Kumar Raj (Government Polytechnic Nawada)\n\n"
        "📚 *अपना सवाल नीचे लिखें या फोटो भेजें, और चलिए पढ़ाई शुरू करते हैं!*\n"
        "*(Memory clear करने के लिए किसी भी समय /clear टाइप करें)*"
    )
    
    try:
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    except Exception:
        await update.message.reply_text(welcome_text) # Fallback if markdown fails

# Memory clear karne ke liye command
async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_sessions:
        del user_sessions[chat_id]
    await update.message.reply_text("🧹 Session memory clear कर दी गई है! चलिए कोई नया टॉपिक शुरू करते हैं।")

# Message handler logic
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    default_vision_prompt = "Provide a comprehensive technical engineering analysis of this image suitable for a Diploma student. Identify components, explain functions, or diagnose errors if possible."
    user_text = update.message.caption or update.message.text or default_vision_prompt

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    # Naya session banayein agar pehli baar message aaya hai
    if chat_id not in user_sessions:
        user_sessions[chat_id] = [{"role": "system", "content": system_instruction}]

    # ⚠️ MEMORY LIMIT LOGIC: Agar chat 15 messages se badi ho jaye, toh purane messages delete karein
    if len(user_sessions[chat_id]) > 15:
        del user_sessions[chat_id][1:3]

    file_path = None
    try:
        if update.message.photo:
            await update.message.reply_text("फोटो मिल गई है! Technical data को analyze किया जा रहा है... ⚙️🖼️")
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
            
        current_model = "openai/gpt-4o-mini" 

        response = await client.chat.completions.create(
            model=current_model, 
            messages=user_sessions[chat_id],
            temperature=0.6,          # Technical accuracy + uniqueness
            presence_penalty=0.4,     # Naye concepts push karne ke liye
            frequency_penalty=0.3     # Repetition rokne ke liye
        )

        raw_reply_text = response.choices[0].message.content
        user_sessions[chat_id].append({"role": "assistant", "content": raw_reply_text})

        # --- POST-PROCESSING: TEXT RESPONSE ---
        reply_text = raw_reply_text.replace('\\[', '').replace('\\]', '').replace('\\frac', '').replace('\\eta', 'η').replace('\\', '')
        
        # Long message handler (for long queries)
        if len(reply_text) > 4000:
             chunks = split_text(reply_text)
             for chunk in chunks:
                try:
                    await update.message.reply_text(chunk, parse_mode='Markdown')
                except Exception:
                    await update.message.reply_text(chunk) # Fallback to plain text 
        else:
            try:
                await update.message.reply_text(reply_text, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(reply_text) # Fallback to plain text
                
    except Exception as e:
        error_msg = f"⚠️ API Error:\n`{str(e)}`"
        try:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(error_msg)
        print(f"Error detail: {e}")
        
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    # Render ke liye background me Flask server start karein
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_memory)) 
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    
    print("🚀 EV Telegram Bot is running on Render! (Creator: Rahul Kumar Raj)")
    application.run_polling()

if __name__ == '__main__':
    if TELEGRAM_BOT_TOKEN and OPENROUTER_API_KEY:
        main()
    else:
        print("Bot start nahi ho sakta kyunki API keys missing hain. Kripya Render me Environment Variables set karein.")

