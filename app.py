import streamlit as st
import requests
from docx import Document
from io import BytesIO
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
import json
import google.generativeai as genai

# --- 1. 初期設定 & セキュリティ ---
try:
    # APIキー等の読み込み
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX = st.secrets["GOOGLE_CX"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    
    # Firestore設定
    key_dict = json.loads(st.secrets["FIRESTORE_KEY"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
    
    # Gemini AI設定
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"システム設定エラー: Secretsを確認してください。 ({e})")
    st.stop()

# --- 2. データベース（クォータ & 履歴）の取得 ---
today_str = datetime.now().strftime('%Y-%m-%d')
usage_ref = db.collection("daily_usage").document(today_str)
history_ref = db.collection("search_history")

# クォータ取得
try:
    usage_doc = usage_ref.get()
    current_usage = usage_doc.to_dict().get("count", 0) if usage_doc.exists else 0
except:
    current_usage = 0
remaining = 100 - current_usage

# 履歴取得（最新5件）
try:
    history_docs = history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).stream()
    recent_history = [d.to_dict() for d in history_docs]
except:
    recent_history = []

# --- 3. 画面レイアウト ---
st.set_page_config(page_title="Intel-Scope Personal", layout="wide")

# サイドバー
st.sidebar.title("🔐 Auth & Quota")
password = st.sidebar.text_input("Passcode", type="password")
quota_placeholder = st.sidebar.empty()
quota_placeholder.metric("Search Remaining", f"{remaining} / 100")

st.sidebar.divider()
st.sidebar.title("📜 Recent History")
for h in recent_history:
    if st.sidebar.button(f"🕒 {h['target']}", key=h['timestamp']):
        st.session_state.history_data = h

# メイン画面
st.title("Intel-Scope: Personal AI Consultant")
st.caption("Google Search × Firestore × Gemini AI：あなたの思考を拡張する専用機。")

target_input = st.text_input("Target Entity", placeholder="企業名を入力...")

# --- 4. メインロジック ---
if st.button("EXECUTE ANALYSIS"):
    if password != "crc2025":
        st.error("パスワードが正しくありません。")
    elif not target_input:
        st.warning("社名を入力してください。")
    elif remaining <= 0:
        st.error("本日の検索枠を使い切りました。")
    else:
        # クォータ更新
        usage_ref.set({"count": current_usage + 1}, merge=True)
        remaining -= 1
        quota_placeholder.metric("Search Remaining", f"{remaining} / 100")
        
        with st.spinner(f"Analyzing '{target_input}' with AI..."):
            # A. Google検索
            news_results = []
            try:
                query = f'{target_input} 再生医療 ニュース 2025'
                url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={query}"
                data = requests.get(url).json()
                if "items" in data:
                    for item in data["items"]:
                        news_results.append({'title': item.get('title'), 'body': item.get('snippet'), 'url': item.get('link')})
            except Exception as e:
                st.error(f"Search API Error: {e}")

            if news_results:
                # B. AI分析
                context = "\n".join([f"Title: {n['title']}\nSnippet: {n['body']}" for n in news_results[:5]])
               # --- ここを書き換え ---
                prompt = f"""
                あなたは再生医療・バイオテック専門のシニアアナリストです。
                
                【目的】
                提示されたニュースから、企業「{target_input}」の現状を投資家視点で整理してください。
                
                【ニュース内容】
                {context}
                
                【出力ルール】
                1. 必ず日本語で回答すること。
                2. 重要なポイントを3つ、箇条書きで簡潔にまとめること。
                3. もしニュースが少ない場合は、その中で読み取れる兆候や一般的な業界動向を補足すること。
                """
                # --------------------
                try:
                    ai_response = model.generate_content(prompt).text
                except:
                    ai_response = "AI分析中にエラーが発生しました。"

                # C. 履歴をFirestoreに保存
                history_data = {
                    "target": target_input,
                    "ai_summary": ai_response,
                    "news": news_results[:5],
                    "timestamp": datetime.now()
                }
                history_ref.add(history_data)
                st.session_state.history_data = history_data
            else:
                st.warning("情報が見つかりませんでした。")

# --- 5. 結果表示エリア ---
if "history_data" in st.session_state:
    data = st.session_state.history_data
    st.divider()
    st.subheader(f"🤖 AI Strategic Insight: {data['target']}")
    st.info(data['ai_summary'])
    
    st.subheader("📡 Supporting Intelligence")
    cols = st.columns(2)
    for idx, n in enumerate(data['news']):
        with cols[idx % 2].expander(n['title']):
            st.write(n['body'])
            st.markdown(f"[記事全文]({n['url']})")

    # Wordレポート作成
    doc = Document()
    doc.add_heading(f"Analysis Report: {data['target']}", 0)
    doc.add_heading("AI Strategic Insight", level=1)
    doc.add_paragraph(data['ai_summary'])
    doc.save(bio := BytesIO())
    st.download_button("💾 Download Executive Report", bio.getvalue(), f"{data['target']}_Report.docx")



















