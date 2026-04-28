import telebot
import requests
import os

# Render ke environment variables se keys uthana (Ye safe tarika hai)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def get_ev_answer(user_message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "You are an AI expert in Electric Vehicles (EV) designed to help diploma engineering students. "
        "Your strict rule: You must ONLY answer questions related to Electric Vehicles, their parts, batteries, motors, and EV technology. "
        "If a user asks about general programming, history, math, or anything unrelated to EVs, you must politely reply: "
        "'Sorry, main sirf Electric Vehicles (EV) se related technical questions ka hi answer de sakta hu.' "
        "Explain concepts simply. DO NOT use markdown formatting like asterisks for bold text. Keep the text completely plain."
    )
    
    data = {
        "model": "google/gemini-pro", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response_json = response.json()
        return response_json['choices'][0]['message']['content']
    except Exception as e:
        return "Network me kuch problem hai. Kripya thodi der baad try kare."

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Hello! Main ek Smart EV Expert Bot hu. "
        "Aap mujhse Electric Vehicles, motors, aur batteries se related koi bhi diploma level ka question puch sakte hai."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    ai_response = get_ev_answer(message.text)
    
    clean_response = ai_response.replace("*", "").replace("#", "")
    
    bot.reply_to(message, clean_response)

if __name__ == "__main__":
    print("EV Telegram Bot start ho gaya hai...")
    bot.polling(none_stop=True)
