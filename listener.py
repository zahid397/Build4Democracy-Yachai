import os
import time
import requests
import google.generativeai as genai
import json
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def safe_parse_json(text):
    try:
        t = re.sub(r"^```json", "", text, flags=re.I).strip()
        t = re.sub(r"```$", "", t).strip()
        return json.loads(t)
    except:
        return None

def analyze_message(text):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
    তুমি 'যাচাই' নামের একটি AI ফ্যাক্ট-চেক বট।
    নিচের টেক্সট বিশ্লেষণ করো: "{text}"
    শুধু JSON আকারে উত্তর দাও:
    {{
      "score": [০-১০০],
      "verdict": ["সত্য", "সম্ভবত সত্য", "বিভ্রান্তিকর", "সম্ভবত মিথ্যা", "মিথ্যা"],
      "justification": "[বাংলায় সংক্ষিপ্ত ব্যাখ্যা]"
    }}
    """
    try:
        response = model.generate_content(prompt)
        data = safe_parse_json(response.text)
        if not data:
            return "⚠️ যাচাই করতে সমস্যা হয়েছে। পরে আবার চেষ্টা করুন।"
        return f"🧠 যাচাই ফলাফল:\n✅ Verdict: {data['verdict']}\n📊 Score: {data['score']}%\n📖 ব্যাখ্যা: {data['justification']}"
    except Exception as e:
        return f"❌ ত্রুটি: {e}"

def send_message(chat_id, text):
    requests.post(f"{URL}/sendMessage", data={"chat_id": chat_id, "text": text})

def main():
    offset = None
    print("🤖 YachaiBot Listener চলছে...")
    while True:
        updates = requests.get(f"{URL}/getUpdates", params={"offset": offset, "timeout": 30}).json()
        if "result" in updates and len(updates["result"]) > 0:
            for item in updates["result"]:
                offset = item["update_id"] + 1
                message = item.get("message")
                if message and "text" in message:
                    chat_id = message["chat"]["id"]
                    text = message["text"].strip()
                    reply = analyze_message(text)
                    send_message(chat_id, reply)
        time.sleep(2)

if __name__ == "__main__":
    main()
