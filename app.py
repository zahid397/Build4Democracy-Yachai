import streamlit as st
import pandas as pd
import requests
import google.generativeai as genai
import json
import re
import logging
import os
from datetime import datetime
import matplotlib.pyplot as plt # 👈 চার্ট লাইব্রেরি
from fpdf import FPDF # 👈 PDF লাইব্রেরি
import sqlite3 # 👈 তোমার ফাইনাল SQLite ইম্পোর্ট
import shutil # 👈 তোমার ব্যাকআপ ইম্পোর্ট

# --- 1. পেজ কনফিগারেশন এবং লগিং সেটআপ ---
st.set_page_config(page_title="YachaiFactBot - তথ্য যাচাই প্ল্যাটফর্ম", page_icon="🧠", layout="wide")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("অ্যাপ্লিকেশন শুরু হয়েছে।")

# --- তোমার নতুন CSS (ভার্সন ৫.৯) ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0a192f, #172a45);
    color: #f8f9fa;
}
h1, h2, h3 {
    color: #48cae4 !important;
    text-align: center;
    font-family: 'Poppins', sans-serif;
}
p, label, .stMarkdown { /* 'textarea' এখান থেকে সরানো হয়েছে */
    color: #e0e0e0 !important;
}
div.stButton>button:first-child {
    background: #00b4d8;
    color: white;
    font-weight: 600;
    border-radius: 10px;
    border: none;
    padding: 0.6rem 1.2rem;
    transition: all 0.3s ease-in-out;
}
div.stButton>button:first-child:hover {
    background: #0096c7;
    transform: scale(1.05);
}

/* === তোমার নতুন Chat-style Text Box (v5.9) === */
textarea {
    background: rgba(255, 255, 255, 0.15); /* translucent white */
    color: #ffffff !important; /* bright white text */
    border-radius: 16px;
    border: 1px solid #00b4d8;
    padding: 12px 15px;
    font-size: 16px;
    font-weight: 500;
    font-family: 'Poppins', sans-serif;
    box-shadow: 0 4px 20px rgba(0, 180, 216, 0.2); /* soft glow */
    backdrop-filter: blur(8px); /* glassy effect */
}
textarea:focus {
    outline: none;
    border: 1.5px solid #48cae4;
    box-shadow: 0 0 10px #00b4d8;
}
::placeholder {
    color: #cce3f0 !important;
    opacity: 0.8;
}
div[data-baseweb="textarea"] textarea {
    background: rgba(20, 35, 50, 0.7);
    color: #ffffff !important;
}
/* ============================================= */

/* Streamlit-এর ডিফল্ট ইনফো/সাকসেস বক্সের রঙ পরিবর্তন (ঐচ্ছিক কিন্তু ভালো দেখায়) */
.stAlert {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)


# --- 2. সিক্রেট এবং API কী লোড ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
BOT_TOKEN = st.secrets.get("bot_token", "YOUR_BOT_TOKEN")
CHAT_ID = st.secrets.get("chat_id", "YOUR_CHAT_ID")
ADMIN_PASS = st.secrets.get("ADMIN_PASS", "demo123")


# =====================================================
# 🧱 DATABASE LAYER (তোমার ফাইনাল ফিক্সড SQLite সিস্টেম v5.8)
# =====================================================
DB_PATH = "data.db"  # File stored permanently

# Always keep one live connection for Streamlit session
@st.cache_resource
def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")  # better concurrency
        logging.info("✅ SQLite Connected (Persistent Mode)")
        st.sidebar.success("🧠 Persistent Memory Active (SQLite)")
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        logging.error(f"DB Connect Error: {e}")
        st.stop()

# Initialize table once
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            text TEXT,
            score INTEGER,
            verdict TEXT,
            justification TEXT,
            final_verdict TEXT
        )
    """)
    conn.commit()
    # conn.close() - @st.cache_resource কানেকশন খোলা রাখে
    logging.info("🧠 Table 'reports' initialized successfully.")

# Insert data safely (don’t close conn!)
def insert_report(text, score, verdict, justification):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO reports (text, score, verdict, justification, final_verdict)
        VALUES (?, ?, ?, ?, ?)
    """, (text, score, verdict, justification, None))
    conn.commit()
    c.close() # কার্সর বন্ধ করা
    logging.info(f"📝 Report inserted successfully: {verdict}")

@st.cache_data(ttl=None, persist=True) # তোমার পার্মানেন্ট মেমোরি ক্যাশ
def fetch_all_reports():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY timestamp DESC", conn)
    # conn.close() - @st.cache_resource কানেকশন খোলা রাখে
    return df

def update_verdict(report_id, verdict):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE reports SET final_verdict=? WHERE id=?", (verdict, report_id))
    conn.commit()
    c.close() # কার্সর বন্ধ করা
    logging.info(f"🔄 Verdict updated for ID {report_id}: {verdict}")

# Initialize database
try:
    init_db()
except Exception as e:
    st.error(f"❌ Database initialization error: {e}")
    logging.error(e)
    st.stop()


# =====================================================
# 🔍 HELPER FUNCTIONS (জেসন)
# =====================================================
def safe_parse_json(text):
    try:
        t = re.sub(r"^```json", "", text, flags=re.I).strip()
        t = re.sub(r"```$", "", t).strip()
        m = re.search(r"(\{.*\})", t, flags=re.S)
        if m:
            t = m.group(1)
        return json.loads(t)
    except Exception as e:
        logging.error(f"JSON Parse Error: {e}")
        return None

# =====================================================
# 🧠 AI ANALYSIS (আসল Gemini)
# =====================================================
def get_gemini_analysis(text_to_analyze):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash-latest']

        prompt = f"""
        তুমি 'যাচাই' নামের একজন AI ফ্যাক্ট-চেকার।
        নিচের টেক্সট বিশ্লেষণ করো: "{text_to_analyze}"
        শুধু JSON আকারে উত্তর দাও:
        {{
          "score": [০-১০০],
          "verdict": ["সত্য", "সম্ভবত সত্য", "বিভ্রান্তিকর", "সম্ভবত মিথ্যা", "মিথ্যা"],
          "justification": "[বাংলায় সংক্ষিপ্ত ব্যাখ্যা]"
        }}
        """

        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                analysis = safe_parse_json(response.text)
                if analysis:
                    analysis["score"] = int(float(analysis.get("score", 0)))
                    return analysis
            except Exception as e:
                logging.warning(f"{model_name} ব্যর্থ: {e}")
        return None
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return None

# =====================================================
# 📢 TELEGRAM ALERT (আসল বট)
# =====================================================
def send_alert(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"} # HTML পার্স মোড
        res = requests.post(url, data=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        logging.error(f"Telegram alert ব্যর্থ: {e}")
        return False

@st.cache_data(ttl=300) # ৫ মিনিটের জন্য কানেকশন স্ট্যাটাস ক্যাশ করা
def check_telegram_connection():
    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        st.sidebar.error("❌ Telegram Token নেই।")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("ok"):
            st.sidebar.success(f"✅ Telegram connected ({data['result']['username']})")
            return True
        else:
            st.sidebar.error("❌ Telegram connection failed.")
            return False
    except Exception as e:
        st.sidebar.error(f"⚠️ Telegram check failed: {e}")
        return False

# =====================================================
# 💾 তোমার নতুন ব্যাকআপ ফাংশন (v5.6)
# =====================================================
def backup_database():
    try:
        shutil.copyfile("data.db", f"backup_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        st.sidebar.info("💾 Backup created successfully!")
    except Exception as e:
        st.sidebar.error(f"Backup failed: {e}")


# =====================================================
# 🎨 ANIMATIONS (লটি লোডার)
# =====================================================
@st.cache_data
def load_lottie_url(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None # লোড ফেইল হলে অ্যাপ যেন ক্র্যাশ না করে

lottie_loading = load_lottie_url("https://assets9.lottiefiles.com/packages/lf20_qp1q7mct.json")
lottie_success = load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_mq9m0vpg.json")
lottie_alert = load_lottie_url("https://assets1.lottiefiles.com/packages/lf20_jtbfg2nb.json")

# =====================================================
# 🧭 NAVIGATION (সাইডবার)
# =====================================================
# --- তোমার নতুন সাইডবার ডিজাইন ---
try:
    st.sidebar.image("yachai_logo.png", width=180)
except:
    st.sidebar.warning("`yachai_logo.png` ফাইলটি যোগ করুন।")

st.sidebar.markdown("### 🤖 YachaiFactBot")
st.sidebar.markdown("_Uncover the truth, one fact at a time._")
# st.sidebar.success("🧠 Persistent Memory Active (SQLite)") # এই লাইনটি get_db_connection() ফাংশনে মুভ করা হয়েছে
st.sidebar.markdown("---")

page = st.sidebar.radio("নেভিগেশন", ["🔍 নাগরিক পোর্টাল", "🧑‍💼 অ্যাডমিন প্যানেল"])
st.sidebar.markdown("---")


# =====================================================
# 🌐 Citizen Portal (তোমার নতুন ডিজাইন + আসল ব্যাকএন্ড)
# =====================================================
if page == "🔍 নাগরিক পোর্টাল":
    
    # --- তোমার নতুন হেডার ---
    st.markdown("""
    <h1>🧠 YachaiFactBot</h1>
    <p style='text-align:center;color:#cccccc;'>AI-চালিত তথ্য যাচাই এবং টেলিগ্রাম অ্যালার্ট সিস্টেম 🇧🇩</p>
    """, unsafe_allow_html=True)

    # === 4. তোমার নতুন Intro Text ===
    st.markdown("> “An AI-driven fact-verification platform for citizens of Bangladesh — powered by Gemini Pro & Team Believer.”")

    st.write("### 🔍 নাগরিক তথ্য যাচাই পোর্টাল")
    user_input = st.text_area("👉 উদাহরণ: 'ভোটার লিস্টে ১ কোটি নাম মুছে গেছে' জাতীয় খবর বা পোস্ট লিখুন:", height=150)

    if st.button("যাচাই করুন", type="primary"):
        input_text = user_input.strip()
        if not input_text:
            st.warning("⚠️ অনুগ্রহ করে কিছু লিখুন।")
        else:
            with st.spinner("🤖 AI যাচাই চলছে..."):
                # --- আসল AI কল (র‍্যান্ডম নয়) ---
                result = get_gemini_analysis(input_text)

            if result:
                # --- আসল ফলাফল ---
                score = result.get("score", 0) # Suspicion Score
                truth_score = 100 - score
                verdict = result.get("verdict", "N/A")
                justification = result.get("justification", "N/A")

                # --- আসল ডেটাবেসে সেভ ---
                insert_report(input_text, score, verdict, justification)

                # --- ফলাফল প্রদর্শন ---
                if score > 75:
                    st.error(f"❌ **ভার্ডিক্ট:** {verdict} ({score}% সন্দেহজনক)")
                elif score > 50:
                    st.warning(f"⚠️ **ভার্ডিক্ট:** {verdict} ({score}% সন্দেহজনক)")
                else:
                    st.success(f"✅ **ভার্ডিক্ট:** {verdict} ({score}% সন্দেহজনক)")

                # --- তোমার নতুন matplotlib চার্ট ---
                st.write("### 📊 AI Confidence Meter")
                data = pd.DataFrame({'Category':['Truth Probability','Misinformation Probability'],'Score':[truth_score,score]})
                fig, ax = plt.subplots(figsize=(5,3))
                ax.bar(data['Category'], data['Score'], color=['#00bfff','#ff4d4d'])
                ax.set_ylim(0,100)
                ax.set_ylabel('Confidence %')
                ax.set_title('AI Confidence Meter', color='white')
                ax.tick_params(colors='white') # অক্ষের রঙ
                fig.patch.set_alpha(0) # চার্টের الخلفية স্বচ্ছ করা
                ax.set_facecolor('none') # অক্ষের الخلفية স্বচ্ছ করা
                st.pyplot(fig)
                chart_path = "chart.png"
                # === 2. তোমার নতুন Sharp চার্ট ===
                fig.savefig(chart_path, transparent=True, bbox_inches='tight', dpi=200)


                # --- তোমার নতুন AI ব্যাখ্যা (আসল জাস্টিফিকেশন) ---
                st.info(f"**💬 AI ব্যাখ্যা:** {justification}")
                st.success("✅ রিপোর্টটি আমাদের ডেটাবেসে সংরক্ষিত হয়েছে।")

                # --- তোমার নতুন PDF রিপোর্ট (আসল ডেটা সহ) ---
                if st.button("📄 Save Visual Report (PDF)"):
                    pdf = FPDF()
                    pdf.add_page()
                    
                    # বাংলা ফন্ট যোগ করা (গুরুত্বপূর্ণ)
                    try:
                        pdf.add_font('Bangla', '', 'SolaimanLipi.ttf', uni=True)
                        pdf.set_font('Bangla', '', 12)
                    except RuntimeError:
                        st.error("❌ PDF বানাতে সমস্যা: `SolaimanLipi.ttf` ফন্ট ফাইলটি পাওয়া যায়নি।")
                        st.stop()

                    pdf.set_font('Bangla', 'B', 16)
                    pdf.cell(0, 10, txt="YachaiFactBot - AI Verification Report", ln=True, align='C')
                    
                    pdf.set_font('Bangla', '', 12)
                    pdf.multi_cell(0, 10, txt=f"\nUser Query:\n{input_text}")
                    pdf.cell(0, 10, txt=f"\nSuspicion Score: {score}%", ln=True)
                    pdf.cell(0, 10, txt=f"Truth Probability: {truth_score}%", ln=True)
                    pdf.multi_cell(0, 10, txt=f"\nAI Explanation:\n{justification}")
                    
                    # === 3. PDF-এ Gemini মডেলের নাম ===
                    pdf.cell(0, 10, txt="Model: Gemini-2.5 Flash (Pro API)", ln=True)
                    pdf.ln(5) # একটু গ্যাপ
                    
                    try:
                        pdf.image("yachai_logo.png", x=160, y=10, w=30)
                    except:
                        pass # লোগো না থাকলে সমস্যা নেই
                    
                    pdf.image(chart_path, x=40, y=pdf.get_y() + 5, w=130)
                    pdf.set_y(pdf.get_y() + 80) # চার্টের নিচে কার্সর আনা

                    # === 1. PDF-এ টিমের নাম ===
                    pdf.set_font('Bangla', 'B', 12)
                    pdf.cell(0, 10, txt="Developed by Team Believer 💡", ln=True, align='C')

                    pdf_file_path = "Yachai_Report_Visual.pdf"
                    pdf.output(pdf_file_path)

                    with open(pdf_file_path, "rb") as file:
                        st.download_button("⬇️ Download Visual Report (PDF)", file, pdf_file_path, "application/pdf")
            else:
                st.error("❌ AI সেবাটি এই মুহূর্তে পাওয়া যাচ্ছে না। অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।")

# =====================================================
# 🧑‍💼 Admin Panel (আমাদের পুরোনো প্যানেল)
# =====================================================
elif page == "🧑‍💼 অ্যাডমিন প্যানেল":
    password = st.sidebar.text_input("🔑 অ্যাডমিন পাসওয়ার্ড", type="password")

    if password == ADMIN_PASS:
        st.sidebar.success("লগ-ইন সফল!")
        logging.info("অ্যাডমিন লগইন সফল।")
        
        # --- অ্যাডমিন সাইডবার কন্ট্রোল ---
        check_telegram_connection()
        
        st.sidebar.markdown("### 🔔 Alert settings")
        alert_threshold = st.sidebar.slider(
            "Alert threshold (score %)", 
            min_value=0, max_value=100, value=75, step=5
        )
        auto_send = st.sidebar.checkbox("Auto-send 'মিথ্যা' alerts", value=False)
        
        st.sidebar.markdown("---")
        with st.sidebar.expander("🧩 Secrets Debug Panel", expanded=False):
            st.write("**GEMINI_API_KEY:**", "✅ লোড হয়েছে" if GEMINI_API_KEY and "AIza" in GEMINI_API_KEY else "❌ নেই")
            st.write("**BOT_TOKEN:**", "✅ লোড হয়েছে" if BOT_TOKEN and ":" in BOT_TOKEN else "❌ নেই")
            chat_id_check = CHAT_ID and (CHAT_ID.isdigit() or (CHAT_ID.startswith("-") and CHAT_ID[1:].isdigit()))
            st.write("**CHAT_ID:**", f"✅ {CHAT_ID}" if chat_id_check else "❌ নেই")
            # ডিবাগ প্যানেলে ডেটাবেস স্ট্যাটাস (SQLite)
            st.write("**DATABASE:**", "✅ SQLite (Local)")
            
            if st.sidebar.button("📲 Test Telegram Alert (Debug)"):
                send_alert("🧪 Debug: YachaiBot test alert — সিক্রেট যাচাই সফল!")
        
        st.sidebar.markdown("---")
        # --- নতুন ব্যাকআপ এবং রিলোড বাটন (v5.6) ---
        col1, col2 = st.sidebar.columns(2)
        if col1.button("🔄 ডেটা রিলোড করুন"):
            st.cache_data.clear()
            st.rerun()
        if col2.button("💾 ডেটাবেস ব্যাকআপ"):
            backup_database() # তোমার নতুন ফাংশন কল
        
        # --- অ্যাডমিন ড্যাশবোর্ড ---
        st.title("🧑‍💼 Admin Dashboard")
        
        try:
            df = fetch_all_reports()
        except Exception as e:
            st.error(f"ডেটা লোড করতে ব্যর্থ: {e}")
            st.stop()
        
        st.info(f"মোট রিপোর্ট: {len(df)}")
        st.dataframe(df, use_container_width=True)

        if len(df) > 0:
            st.subheader("✅ রিপোর্ট যাচাই করুন")
            pending = df[df["final_verdict"].isna()]
            if len(pending) == 0:
                st.success("🎉 সব রিপোর্ট যাচাই সম্পন্ন!")
            else:
                # পেন্ডিং রিপোর্টগুলো থেকে সিলেক্ট করা
                selected_text = st.selectbox("একটি পেন্ডিং রিপোর্ট নির্বাচন করুন:", pending["text"])
                selected_row = pending[pending["text"] == selected_text].iloc[0]
                
                report_id = int(selected_row["id"]) # ID ঠিকমতো নেওয়া
                ai_score = int(selected_row["score"])

                st.markdown(f"**AI ভার্ডিক্ট:** {selected_row['verdict']} ({ai_score}%)")
                st.markdown(f"**ব্যাখ্যা:** {selected_row['justification']}")

                status = st.radio("ফাইনাল ট্যাগ দিন:", ["সত্য", "বিভ্রান্তিকর", "মিথ্যা"], key=f"status_{report_id}")
                
                if st.button("ফাইনাল ট্যাগ করুন ✅", type="primary"):
                    update_verdict(report_id, status)
                    st.cache_data.clear() # ডেটা আপডেট হয়েছে, ক্যাশ ক্লিয়ার
                    
                    if status == "মিথ্যা":
                        # অটো-সেন্ড লজিক
                        if auto_send and ai_score >= alert_threshold:
                            alert_msg = (
                                f"🚨 <b>ভুয়া তথ্য শনাক্ত!</b> 🚨\n\n"
                                f"<b>তথ্য:</b> <i>{selected_row['text']}</i>\n"
                                f"<b>AI স্কোর:</b> {ai_score}%\n"
                                f"<b>চূড়ান্ত সিদ্ধান্ত:</b> ❌ {status}\n\n"
                                f"<i>#Build4Democracy #YachaiBot</i>"
                            )
                            if send_alert(alert_msg):
                                st.success("📲 অটোমেটিক টেলিগ্রাম অ্যালার্ট পাঠানো হয়েছে।")
                            else:
                                st.error("⚠️ অ্যালার্ট পাঠাতে ব্যর্থ হয়েছে।")
                            st.rerun()
                        
                        else:
                            # ম্যানুয়াল-সেন্ড লজিক
                            st.info("রিপোর্টটি ‘মিথ্যা’ ট্যাগ করা হয়েছে।")
                            st.write(f"AI স্কোর: **{ai_score}%** | থ্রেশহোল্ড: **{alert_threshold}%** | অটো-সেন্ড: **{auto_send}**")
                            
                            if st.button("📨 ম্যানুয়ালি অ্যালার্ট পাঠাও", key=f"manual_alert_{report_id}"):
                                alert_msg = (
                                    f"🚨 <b>ম্যানুয়াল অ্যালার্ট:</b> যাচাইকৃত ভুয়া তথ্য!\n\n"
                                    f"<b>তথ্য:</b> <i>{selected_row['text']}</i>\n"
                                    f"<b>AI স্কোর:</b> {ai_score}%\n"
                                    f"<b>সিদ্ধান্ত:</b> ❌ {status}\n\n"
                                    f"<i>#Build4Democracy #YachaiBot</i>"
                                )
                                if send_alert(alert_msg):
                                    st.success("✅ ম্যানুয়াল অ্যালার্ট পাঠানো হয়েছে।")
                                    st.rerun()
                                else:
                                    st.error("❌ ম্যানুয়াল অ্যালার্ট পাঠানো ব্যর্থ হয়েছে।")
                        
                        # --- তোমার বাগ ফিক্স (v5.9) ---
                        # এখানের 'else' ব্লকটি ডিলিট করা হয়েছে যাতে ম্যানুয়াল বাটনটি দেখা যায়

                    else:
                        # যদি স্ট্যাটাস "মিথ্যা" না হয় (যেমন: সত্য বা বিভ্রান্তিকর)
                        st.success("✅ আপডেট হয়েছে!")
                        st.rerun()
    
    elif password:
        st.error("🔒 ভুল পাসওয়ার্ড।")
    else:
        st.info("🔒 অ্যাডমিন প্যানেল দেখতে সাইডবারে পাসওয়ার্ড দিন।")

# ---------- তোমার নতুন FOOTER ----------
st.markdown("""
<hr style='border-color:#00bfff22; margin-top: 40px;'>
<p style='text-align:center;color:#aaaaaa;font-size:14px;'>
Developed by <b>Team Believer</b> | Hackathon: <i>Build for Democracy 2025 🇧🇩</i>
</p>
""", unsafe_allow_html=True)
