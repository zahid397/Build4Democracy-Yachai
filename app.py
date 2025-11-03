import streamlit as st
import json
import pandas as pd
import requests
import google.generativeai as genai
import re
import logging
from datetime import datetime

# --- 1. Page Config & Logging ---
st.set_page_config(
    page_title="যাচাই | সুরক্ষিত গণতন্ত্র",
    page_icon="🧠",
    layout="wide"
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="yachai_app.log",
    filemode="a"
)
logging.info("App started.")

# --- 2. Secrets ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
BOT_TOKEN = st.secrets.get("bot_token", "YOUR_BOT_TOKEN")
CHAT_ID = st.secrets.get("chat_id", "YOUR_CHAT_ID")
ADMIN_PASS = st.secrets.get("ADMIN_PASS", "demo123")
MAX_INPUT_LENGTH = 3000

# --- 3. Safe JSON Parser ---
def safe_parse_json(text):
    try:
        t = text.strip()
        t = re.sub(r"^```json", "", t, flags=re.I).strip()
        t = re.sub(r"```$", "", t).strip()
        m = re.search(r"(\{.*\})", t, flags=re.S)
        if m:
            t = m.group(1)
        return json.loads(t)
    except Exception as e:
        logging.error(f"JSON parse error: {e}")
        return None

# --- 4. Gemini 2.5 Flash Function ---
def get_gemini_analysis(text_to_analyze):
    try:
        if GEMINI_API_KEY == "YOUR_GEMINI_KEY":
            st.error("Gemini API কী সেট করা নেই।")
            return None
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"API কনফিগারেশনে সমস্যা: {e}")
        return None

    # ✅ 2.5 Flash Model
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    তুমি 'যাচাই' নামের একজন AI ফ্যাক্ট-চেকার। তোমার কাজ বাংলাদেশের নির্বাচন সম্পর্কিত ভুল তথ্য শনাক্ত করা।
    টেক্সট: "{text_to_analyze}"
    শুধুমাত্র JSON ফরম্যাটে উত্তর দাও:
    {{
      "score": [০-১০০ পর্যন্ত একটি সংখ্যা],
      "verdict": ["সত্য", "সম্ভবত সত্য", "বিভ্রান্তিকর", "সম্ভবত মিথ্যা", "মিথ্যা"],
      "justification": "[সংক্ষিপ্ত ব্যাখ্যা বাংলায়]"
    }}
    """

    try:
        response = model.generate_content(prompt)
        analysis = safe_parse_json(response.text)

        if analysis is None:
            st.error("AI থেকে সঠিক ফরম্যাটে উত্তর পাওয়া যায়নি।")
            return None

        raw_score = analysis.get("score", 0)
        try:
            score = int(float(raw_score))
        except:
            score = 0
        analysis["score"] = score
        return analysis
    except Exception as e:
        logging.error(f"Gemini 2.5 Flash API error: {e}")
        st.error("AI সেবাটি এই মুহূর্তে পাওয়া যাচ্ছে না। কিছুক্ষণ পর চেষ্টা করুন।")
        return None

# --- 5. Telegram Alert ---
def send_alert(message):
    if BOT_TOKEN == "YOUR_BOT_TOKEN" or CHAT_ID == "YOUR_CHAT_ID":
        st.warning("⚠️ Telegram সেট করা নেই।")
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except Exception as e:
        logging.error(f"Telegram error: {e}")
        return False

# --- 6. Data Load/Save ---
DATA_FILE = "submissions.json"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f]
        return pd.DataFrame(data)
    except FileNotFoundError:
        return pd.DataFrame(columns=["text","score","verdict","justification","timestamp","final_verdict"])

def save_data(df):
    df.to_json(DATA_FILE, orient="records", lines=True, force_ascii=False)

# --- 7. Sidebar Navigation ---
st.sidebar.title("🧠 যাচাই (Yachai)")
page = st.sidebar.radio("নেভিগেশন", ["🔍 নাগরিক পোর্টাল", "🧑‍💼 অ্যাডমিন প্যানেল"])
st.sidebar.markdown("---")

# --- Citizen Portal ---
if page == "🔍 নাগরিক পোর্টাল":
    st.title("তথ্য যাচাই করুন")
    st.caption("AI-চালিত ফ্যাক্ট-চেকিং প্ল্যাটফর্ম")
    st.warning("⚠️ ব্যক্তিগত তথ্য জমা দেবেন না।")

    text = st.text_area("আপনার তথ্য লিখুন:", height=150, placeholder="উদাহরণ: 'নির্বাচনের তারিখ আবারো পেছানো হয়েছে...'")

    if st.button("যাচাই করুন"):
        if not text.strip():
            st.warning("অনুগ্রহ করে টেক্সট লিখুন।")
        elif len(text) > MAX_INPUT_LENGTH:
            st.error("টেক্সটটি অনেক বড়!")
        else:
            with st.spinner("AI বিশ্লেষণ করছে..."):
                result = get_gemini_analysis(text)
                if result:
                    score = result["score"]
                    verdict = result["verdict"]
                    justification = result["justification"]

                    if score > 75:
                        st.error(f"❌ ভার্ডিক্ট: {verdict} ({score}%)")
                    elif score > 50:
                        st.warning(f"⚠️ ভার্ডিক্ট: {verdict} ({score}%)")
                    else:
                        st.success(f"✅ ভার্ডিক্ট: {verdict} ({score}%)")

                    st.info(f"ব্যাখ্যা: {justification}")

                    df = load_data()
                    new_entry = pd.DataFrame([{
                        "text": text,
                        "score": score,
                        "verdict": verdict,
                        "justification": justification,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "final_verdict": None
                    }])
                    df = pd.concat([df, new_entry], ignore_index=True)
                    save_data(df)
                    st.success("✅ তথ্য সংরক্ষিত হয়েছে!")

# --- Admin Panel ---
elif page == "🧑‍💼 অ্যাডমিন প্যানেল":
    st.title("অ্যাডমিন প্যানেল")
    password = st.sidebar.text_input("অ্যাডমিন পাসওয়ার্ড", type="password")

    if password == ADMIN_PASS:
        df = load_data()
        st.dataframe(df, use_container_width=True)
        if st.button("ডেটা রিলোড করুন"):
            st.rerun()
    elif password != "":
        st.error("❌ ভুল পাসওয়ার্ড!")
