import streamlit as st
import requests
from docx import Document
from io import BytesIO
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
import json
import google.generativeai as genai

# --- 1. 初期設定 ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX = st.secrets["GOOGLE_CX"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    
    key_dict = json.loads(st.secrets["FIRESTORE_KEY"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
    
    # ライブラリ側の設定（念のため残す）
    genai.configure(api_key=GEMINI_API_KEY, transport='rest')
except Exception as e:
    st.error(f"システム設定エラー: {e}")
    st.stop()

# --- 2. データベース取得 ---
today_str = datetime.now().strftime('%Y-%m-%d')
usage_ref = db.collection("daily_usage").document(today_str)
history_ref = db.collection("search_history")

try:
    usage_doc = usage_ref.get()
    current_usage = usage_doc.to_dict().get("count", 0) if usage_doc.exists else 0
except:
    current_usage = 0
remaining = 100 - current_usage

try:
    history_docs = history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).stream()
    recent_history = [d.to_dict() for d in history_docs]
except:
    recent_history = []

# --- 3. レイアウト（ここを整理しました） ---
st.set_page_config(page_title="Intel-Scope Personal", layout="wide")

# サイドバー
st.sidebar.title("🔐 Auth & Quota")
password = st.sidebar.text_input("Passcode", type="password") # ここが重複していた原因
quota_placeholder = st.sidebar.empty()
quota_placeholder.metric("Search Remaining", f"{remaining} / 100")

st.sidebar.divider()
st.sidebar.title("📜 Recent History")
for h in recent_history:
    t_str = h['timestamp'].strftime('%Y%m%d%H%M%S') if hasattr(h['timestamp'], 'strftime') else str(h['timestamp'])
    if st.sidebar.button(f"🕒 {h['target']}", key=f"btn_{t_str}"):
        st.session_state.history_data = h

# メイン画面
st.title("Intel-Scope: Personal AI Consultant")
target_input = st.text_input("Target Entity", placeholder="企業名を入力...")

# --- 4. メイン処理（修正版） ---
if st.button("EXECUTE ANALYSIS"):
    if password != "crc2025":
        st.error("パスワードが正しくありません。")
    elif not target_input:
        st.warning("社名を入力してください。")
    elif remaining <= 0:
        st.error("検索枠上限です。")
    else:
        # 使用量の更新
        usage_ref.set({"count": current_usage + 1}, merge=True)
        remaining -= 1
        quota_placeholder.metric("Search Remaining", f"{remaining} / 100")
        
        with st.spinner("Analyzing..."):
            news_results = []
            try:
                # 検索クエリの実行
                query = f'{target_input} 再生医療 ニュース 2025'
                url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={query}"
                response_search = requests.get(url, timeout=10)
                data = response_search.json()
                
                if "items" in data:
                    for item in data["items"]:
                        news_results.append({
                            'title': item.get('title'), 
                            'body': item.get('snippet'), 
                            'url': item.get('link')
                        })
                else:
                    st.warning("検索結果が見つかりませんでした。")
            except Exception as e:
                st.error(f"Search Error: {e}")

            if news_results:
                context = "\n".join([f"Title: {n['title']}\nSnippet: {n['body']}" for n in news_results[:5]])
                prompt_text = f"再生医療専門家として、{target_input}の動向を3点要約してください。また、今後の展望についても一言添えてください。\n\n検索結果:\n{context}"
                
                # --- 4. メイン処理（インデント修正版） ---

# (中略: 検索処理など)

            if news_results:
                context = "\n".join([f"Title: {n['title']}\nSnippet: {n['body']}" for n in news_results[:5]])
                prompt_text = f"再生医療専門家として、{target_input}の動向を3点要約してください。\n\n{context}"
                
                try:
                    # ★ ここから下の行はすべて「try:」より深くインデントしてください
                    current_key = "AIzaSyDKGUReXbwU0uB6j9wtRWNlxvLkZKiUjgg".strip()
                    
                    # モデル名を最新の 2.0-flash に、パスに /models/ を追加
                    # gemini-2.0-flash を gemini-1.5-flash に変更
                    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={current_key}"
                    
                    payload = {
                        "contents": [{
                            "parts": [{"text": prompt_text}]
                        }]
                    }
                    headers = {"Content-Type": "application/json"}
                    
                    response = requests.post(api_url, json=payload, headers=headers, timeout=20)
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        ai_response = res_json["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        ai_response = f"AIエラー（{response.status_code}）: {response.text}"
                        
                except Exception as ai_err:
                    # ★ ここも「except:」より深くインデント
                    ai_response = f"通信エラー: {str(ai_err)}"

                # --- 履歴保存とセッション更新 ---
                history_data = {
                    "target": target_input,
                    "ai_summary": ai_response,
                    "news": news_results[:5],
                    "timestamp": datetime.now()
                }
                history_ref.add(history_data)
                st.session_state.history_data = history_data
                st.rerun() # 結果を表示するために画面をリフレッシュ

# --- 5. 表示 ---
if "history_data" in st.session_state:
    d = st.session_state.history_data
    st.divider()
    st.subheader(f"🤖 AI Insight: {d['target']}")
    st.info(d['ai_summary'])
    
    cols = st.columns(2)
    for idx, n in enumerate(d['news']):
        with cols[idx % 2].expander(n['title']):
            st.write(n['body'])
            st.markdown(f"[全文]({n['url']})")














































