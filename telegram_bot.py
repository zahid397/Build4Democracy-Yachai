import os
import telebot
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 🔐 API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ✅ Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# 🤖 Initialize Telegram Bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 🧠 /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "👋 স্বাগতম যাচাই (Yachai) - তোমার AI Fact Checking সহকারী!\n\n"
        "🧠 আমি যেকোনো তথ্য বিশ্লেষণ করে সত্যতা যাচাই করতে পারি।\n"
        "📩 শুধু মেসেজে লিখো — যেমন:\n"
        "'বাংলাদেশে ভোট স্থগিত হয়েছে কি সত্যি?'"
    )

# 🔍 Handle user message
@bot.message_handler(func=lambda message: True)
def fact_check(message):
    user_text = message.text.strip()
    bot.send_chat_action(message.chat.id, 'typing')

    try:
        # ChatGPT-style intelligent prompt
        prompt = f"""
        তুমি একজন বাংলা ভাষায় কথা বলা fact-checking সহকারী।
        নিচের বক্তব্য বিশ্লেষণ করো এবং সংক্ষিপ্তভাবে সত্যতা যাচাই করো।
        ব্যবহারকারী জিজ্ঞেস করেছে:
        "{user_text}"

        🔹 Verdict: (সত্য / মিথ্যা / বিভ্রান্তিকর)
        🔹 বিশ্লেষণ:
        """

        response = model.generate_content(prompt)
        result = response.text if response else "দুঃখিত, আমি এখন যাচাই করতে পারছি না।"

        bot.reply_to(message, f"✅ যাচাই ফলাফল:\n\n{result}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ ত্রুটি ঘটেছে:\n{str(e)}")

# 🚀 Run bot
if __name__ == "__main__":
    print("🤖 Yachai Telegram Bot is running...")
    bot.polling(non_stop=True)
