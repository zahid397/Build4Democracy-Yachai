import os
import telebot
import google.generativeai as genai

# 🔐 Environment variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# ❗ Safety check
if not GEMINI_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise Exception("❌ Missing environment variables! Please set GEMINI_API_KEY and TELEGRAM_BOT_TOKEN.")

# 🤖 Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# 💬 Initialize Telegram Bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 🧠 /start command
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "👋 স্বাগতম যাচাই (Yachai) — তোমার AI Fact-Checking সহকারী!\n\n"
        "🔎 যেকোনো খবর / পোস্ট / দাবি পাঠাও — আমি সত্যতা বিশ্লেষণ করে দিবো।"
    )

# 📌 Handle user message
@bot.message_handler(func=lambda msg: True)
def check_fact(message):
    text = message.text.strip()
    bot.send_chat_action(message.chat.id, "typing")

    try:
        prompt = f"""
তুমি একজন বাংলা fact-checking সহকারী।
নিচের বক্তব্য সত্য নাকি মিথ্যা তা বিশ্লেষণ করো।

বক্তব্য:
{text}

ফরম্যাট:
- Verdict: (সত্য / মিথ্যা / বিভ্রান্তিকর)
- বিশ্লেষণ:
"""

        response = model.generate_content(prompt)
        result = response.text if response else "দুঃখিত, আমি যাচাই করতে পারছি না।"

        bot.reply_to(message, f"🧾 Fact-Check Result:\n\n{result}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ ত্রুটি ঘটেছে: {str(e)}")

# 🚀 Run bot (Always active)
if __name__ == "__main__":
    print("🤖 Yachai Telegram Bot is running on Railway...")
    bot.polling(non_stop=True, timeout=90)
