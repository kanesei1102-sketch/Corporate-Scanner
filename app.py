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
    
    # Firestoreの設定
    key_dict = json.loads(st.secrets["FIRESTORE_KEY"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
    
    # Gemini SDK設定（REST APIと併用する場合は念のため）
    genai.configure(api_key=GEMINI_API_KEY, transport='rest')
except Exception as e:
    st.error(f"システム設定エラー: {e}")
    st.stop()

# --- 2. データベース取得（使用量制限と履歴） ---
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

# --- 3. レイアウト構成 ---
st.set_page_config(page_title="Intel-Scope Personal", layout="wide")

# サイドバー：認証とクォータ
st.sidebar.title("🔐 Auth & Quota")
password = st.sidebar.text_input("Passcode", type="password")
quota_placeholder = st.sidebar.empty()
quota_placeholder.metric("Search Remaining", f"{remaining} / 100")

st.sidebar.divider()
st.sidebar.title("📜 Recent History")
for h in recent_history:
    # タイムスタンプを安全に文字列変換
    try:
        t_str = h['timestamp'].strftime('%Y/%m/%d %H:%M')
    except:
        t_str = str(h['timestamp'])
        
    if st.sidebar.button(f"🕒 {h['target']}\n({t_str})", key=f"btn_{h.get('timestamp')}"):
        st.session_state.history_data = h

# メイン画面
st.title("Intel-Scope: Personal AI Consultant")
target_input = st.text_input("Target Entity", placeholder="企業名を入力してください（例: 富士フイルム）")

# --- 4. メイン処理（解析実行） ---
if st.button("EXECUTE ANALYSIS"):
    if password != "crc2025":
        st.error("パスワードが正しくありません。")
    elif not target_input:
        st.warning("企業名を入力してください。")
    elif remaining <= 0:
        st.error("本日の検索枠上限（100件）に達しました。")
    else:
        # 使用量のカウントアップ
        usage_ref.set({"count": current_usage + 1}, merge=True)
        remaining -= 1
        quota_placeholder.metric("Search Remaining", f"{remaining} / 100")
        
        with st.spinner(f"{target_input} に関する情報を収集中..."):
            # A. Google Custom Search でニュース取得
            news_results = []
            try:
                # 2025年の最新情報を取得するクエリ
                query = f'{target_input} 再生医療 ニュース 2025'
                search_url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={query}"
                resp = requests.get(search_url, timeout=10)
                search_data = resp.json()
                
                if "items" in search_data:
                    for item in search_data["items"][:5]: # 上位5件
                        news_results.append({
                            'title': item.get('title'),
                            'body': item.get('snippet'),
                            'url': item.get('link')
                        })
            except Exception as e:
                st.error(f"Google検索エラー: {e}")

            # B. Gemini API による解析
            if news_results:
                context = "\n".join([f"Title: {n['title']}\nSnippet: {n['body']}" for n in news_results])
                prompt_text = (
                    f"あなたは再生医療分野の専門コンサルタントです。以下の最新ニュースに基づき、"
                    f"{target_input}の動向を3つの重要ポイントで要約してください。"
                    f"最後に今後の展望を専門的な視点で1文添えてください。\n\n"
                    f"--- 検索結果 ---\n{context}"
                )
                
                try:
                    # 安定版 v1 エンドポイントを使用
                    api_key = GEMINI_API_KEY.strip()
                    gemini_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
                    
                    payload = {
                        "contents": [{"parts": [{"text": prompt_text}]}],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 1000
                        }
                    }
                    headers = {"Content-Type": "application/json"}
                    
                    ai_resp = requests.post(gemini_url, json=payload, headers=headers, timeout=25)
                    
                    if ai_resp.status_code == 200:
                        res_json = ai_resp.json()
                        ai_content = res_json["candidates"][0]["content"]["parts"][0]["text"]
                    elif ai_resp.status_code == 429:
                        ai_content = "【エラー】AIの利用制限（クォータ）を超過しました。30秒ほど待ってから再度お試しください。"
                    else:
                        ai_content = f"【AIエラー】状態: {ai_resp.status_code}\n詳細: {ai_resp.text}"
                        
                except Exception as ai_err:
                    ai_content = f"AI通信エラー: {str(ai_err)}"

                # C. 履歴の保存
                history_data = {
                    "target": target_input,
                    "ai_summary": ai_content,
                    "news": news_results,
                    "timestamp": datetime.now()
                }
                history_ref.add(history_data)
                st.session_state.history_data = history_data
                st.rerun()
            else:
                st.warning("関連する最新ニュースが見つかりませんでした。")

# --- 5. 解析結果の表示 ---
if "history_data" in st.session_state:
    data = st.session_state.history_data
    st.divider()
    st.subheader(f"🤖 AI Insight: {data['target']}")
    
    # AIの要約を表示
    st.info(data['ai_summary'])















































