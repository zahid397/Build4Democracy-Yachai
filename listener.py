import os
import requests
import google.generativeai as genai
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print("🤖 YachaiBot listener running...")

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 60, "offset": offset}
    return requests.get(url, params=params).json()

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, data=payload)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

offset = None
while True:
    updates = get_updates(offset)
    if updates.get("result"):
        for update in updates["result"]:
            offset = update["update_id"] + 1
            msg = update["message"].get("text", "")
            chat_id = update["message"]["chat"]["id"]

            if msg:
                print(f"💬 {msg}")
                prompt = f"তুমি একজন ফ্যাক্ট-চেকিং AI। নিচের বার্তাটি বিশ্লেষণ করো: {msg}"
                try:
                    response = model.generate_content(prompt)
                    answer = response.text or "দুঃখিত, আমি এখন বিশ্লেষণ করতে পারছি না।"
                except Exception as e:
                    answer = f"ত্রুটি: {e}"

                send_message(chat_id, "🧠 যাচাই ফলাফল:\n" + answer)
    time.sleep(2)
