# 🧠 যাচাই (Yachai) — AI Fact-Checking Platform for Digital Democracy 🇧🇩  
**"যাচাই তথ্যে, সুরক্ষিত গণতন্ত্র"**

An **AI-powered misinformation detection and verification tool** designed to combat election-related fake news and protect digital democracy in Bangladesh.  
Built for the **#Build4Democracy Hackathon 2025** 🗳️ — powered by **Gemini AI, Streamlit, and Telegram Alerts**.

---

## 🚀 Overview
**যাচাই (Yachai)** empowers citizens, journalists, and fact-checkers to verify suspicious election-related claims in real-time.  
The system combines **AI-based text analysis** with **human verification** and **Telegram alert automation**, ensuring both speed and accuracy in combating misinformation.

---

## 💡 Problem Statement
Bangladesh has seen a **sharp rise in election misinformation**, leading to voter confusion and distrust.  
Platforms like *Rumor Scanner* and *DismisLab* recorded over **800+ false or misleading claims** in early 2025 alone.  
There is no centralized, citizen-friendly fact-checking tool in Bengali that connects AI and verified human reviewers.

---

## 🧩 Features
### 🗣️ Citizen Portal
- Paste suspicious text or link and get **AI-based verification**  
- Shows **truth probability score (0–100%)**, verdict, and justification in Bangla  
- Saves entries for human review  

### 🧑‍💼 Admin Panel
- Password-protected dashboard for **fact-checkers**  
- Verify or reject AI findings  
- Sends automatic **Telegram Alerts** for confirmed fake news  

### 🤖 Telegram Alert System
- Instant notifications for misinformation detection  
- Uses **Bot API** with secure token-based access  

---

## 🧠 Tech Stack
| Component | Technology |
|------------|-------------|
| Frontend & App | Streamlit |
| AI Engine | Google Gemini 1.5 Pro |
| Database | JSON (lightweight for hackathon) |
| Bot | Telegram Bot API |
| Deployment | Streamlit Cloud / Render |

---

## ⚙️ Installation
```bash
git clone https://github.com/TeamBelievers/Build4Democracy-Yachai.git
cd Build4Democracy-Yachai
pip install -r requirements.txt
streamlit run app.py
