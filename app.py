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
    # Streamlit Secretsから各キーを取得
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX = st.secrets["GOOGLE_CX"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    
    # Firestoreの設定
    key_dict = json.loads(st.secrets["FIRESTORE_KEY"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
    
    # SDK側の設定（念のため）
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"システム設定（Secrets）の読み込みエラー: {e}")
    st.stop()

# --- 2. データベース取得（使用量と履歴） ---
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
    # 履歴を最新5件取得
    history_docs = history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).stream()
    recent_history = [d.to_dict() for d in history_docs]
except:
    recent_history = []

# --- 3. レイアウト構成 ---
st.set_page_config(page_title="Intel-Scope Personal", layout="wide")

# サイドバー：認証と残り枠
st.sidebar.title("🔐 Auth & Quota")
password = st.sidebar.text_input("Passcode", type="password")
quota_placeholder = st.sidebar.empty()
quota_placeholder.metric("Search Remaining", f"{remaining} / 100")

st.sidebar.divider()
st.sidebar.title("📜 Recent History")
for h in recent_history:
    t_obj = h.get('timestamp')
    t_display = t_obj.strftime('%m/%d %H:%M') if hasattr(t_obj, 'strftime') else "No Date"
    if st.sidebar.button(f"🕒 {h['target']}\n({t_display})", key=f"btn_{t_display}_{h['target']}"):
        st.session_state.history_data = h

# メイン画面
st.title("Intel-Scope: Personal AI Consultant")
target_input = st.text_input("Target Entity", placeholder="企業名や技術名を入力...")

# --- 4. メイン処理 ---
if st.button("EXECUTE ANALYSIS"):
    if password != "crc2025":
        st.error("パスワードが正しくありません。")
    elif not target_input:
        st.warning("対象（社名など）を入力してください。")
    elif remaining <= 0:
        st.error("本日の検索上限に達しました。")
    else:
        # 使用量のカウント更新
        usage_ref.set({"count": current_usage + 1}, merge=True)
        remaining -= 1
        quota_placeholder.metric("Search Remaining", f"{remaining} / 100")
        
        with st.spinner(f"{target_input} の動向を解析中..."):
            # A. Google検索で最新情報を取得
            news_results = []
            try:
                query = f'{target_input} 再生医療 ニュース 2025'
                search_url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={query}"
                search_resp = requests.get(search_url, timeout=10)
                search_data = search_resp.json()
                
                if "items" in search_data:
                    for item in search_data["items"][:5]:
                        news_results.append({
                            'title': item.get('title'),
                            'body': item.get('snippet'),
                            'url': item.get('link')
                        })
            except Exception as e:
                st.error(f"Google検索中にエラーが発生しました: {e}")

            # B. Gemini API による要約生成
            if news_results:
                context = "\n".join([f"記事題名: {n['title']}\n概要: {n['body']}" for n in news_results])
                prompt_text = (
                    f"あなたは再生医療分野の専門コンサルタントです。以下の最新ニュースに基づき、"
                    f"{target_input}の動向を3つの重要ポイントで簡潔に要約してください。"
                    f"最後に今後の展望について専門的な視点で1文添えてください。\n\n"
                    f"--- ニュースデータ ---\n{context}"
                )
                
                try:
                    # APIキーの取得（前後の余計な文字を排除）
                    api_key_clean = GEMINI_API_KEY.strip()
                    
                    # 404/429を回避するための標準エンドポイント（v1beta）
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key_clean}"
                    
                    payload = {
                        "contents": [{"parts": [{"text": prompt_text}]}],
                        "generationConfig": {
                            "temperature": 0.7,
                            "topP": 0.95,
                            "maxOutputTokens": 1024
                        }
                    }
                    headers = {"Content-Type": "application/json"}
                    
                    response = requests.post(gemini_url, json=payload, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        # 安全にテキストを取り出し
                        ai_response_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                    elif response.status_code == 429:
                        ai_response_text = "【API制限エラー】リクエストが集中しています。30秒ほど待ってから再度実行してください。"
                    else:
                        ai_response_text = f"【AI通信エラー】状態: {response.status_code}\n詳細: {response.text}"
                        
                except Exception as ai_err:
                    ai_response_text = f"AI解析中に予期せぬエラーが発生しました: {str(ai_err)}"

                # C. 履歴保存
                history_data = {
                    "target": target_input,
                    "ai_summary": ai_response_text,
                    "news": news_results,
                    "timestamp": datetime.now()
                }
                history_ref.add(history_data)
                st.session_state.history_data = history_data
                st.rerun() # 結果を表示するために画面を更新
            else:
                st.warning("関連する最新ニュースが見つかりませんでした。")

# --- 5. 結果表示エリア ---
if "history_data" in st.session_state:
    res = st.session_state.history_data
    st.divider()
    st.subheader(f"🤖 AI Analysis Result: {res['target']}")
    
    # AIの回答を表示
    st.info(res['ai_summary'])
    
    # ニュース記事のカード表示
    st.write("### 🌐 Sources")
    cols = st.columns(2)
    for i, n in enumerate(res['news']):
        with cols[i % 2].expander(f"📰 {n['title']}", expanded=False):
            st.write(n['body'])
            st.markdown(f"[詳細（出典先）へ]({n['url']})")
















































