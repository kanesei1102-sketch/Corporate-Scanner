import streamlit as st
import requests
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
import json

# --- 1. 初期設定 ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX = st.secrets["GOOGLE_CX"]
    
    # Firestore設定
    key_dict = json.loads(st.secrets["FIRESTORE_KEY"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
except Exception as e:
    st.error(f"システム設定エラー: {e}")
    st.stop()

# --- 2. データベース取得 ---
today_str = datetime.now().strftime('%Y-%m-%d')
usage_ref = db.collection("daily_usage").document(today_str)
history_ref = db.collection("search_history")

# 本日の使用量取得
try:
    usage_doc = usage_ref.get()
    current_usage = usage_doc.to_dict().get("count", 0) if usage_doc.exists else 0
except:
    current_usage = 0
remaining = 100 - current_usage

# 履歴を最大10件取得（日付の新しい順）
try:
    history_docs = history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()
    recent_history = [d.to_dict() for d in history_docs]
except:
    recent_history = []

# --- 3. レイアウト ---
st.set_page_config(page_title="Intel-Scope Personal", layout="wide")

# サイドバー設定
st.sidebar.title("🔐 Auth & Quota")
password = st.sidebar.text_input("Passcode", type="password")
quota_placeholder = st.sidebar.empty()
quota_placeholder.metric("Search Remaining", f"{remaining} / 100")

st.sidebar.divider()
st.sidebar.title("📜 Search History")

# サイドバーに履歴ボタンを表示（西暦・日付付き）
for h in recent_history:
    if 'timestamp' in h:
        # FirestoreのTimestampオブジェクトをPythonのdatetimeに変換してフォーマット
        ts = h['timestamp']
        date_str = ts.strftime('%Y/%m/%d %H:%M')
        t_key = ts.strftime('%Y%m%d%H%M%S%f')
    else:
        date_str = "Unknown Date"
        t_key = "unknown"

    # ボタンラベルに「日付 + 企業名」を表示
    if st.sidebar.button(f"📅 {date_str}\n{h['target']}", key=f"btn_{t_key}"):
        st.session_state.history_data = h

# メイン画面
st.title("Intel-Scope: Personal News Scanner")
st.markdown("再生医療・バイオテック企業の最新動向をリアルタイムでスキャンし、履歴に保存します。")
target_input = st.text_input("Target Entity", placeholder="企業名を入力...")

# --- 4. メイン処理 (検索と保存) ---
if st.button("EXECUTE SCAN"):
    if password != "crc2025":
        st.error("パスワードが正しくありません。")
    elif not target_input:
        st.warning("社名を入力してください。")
    elif remaining <= 0:
        st.error("本日の検索枠上限です。")
    else:
        # 使用量カウントアップ
        usage_ref.set({"count": current_usage + 1}, merge=True)
        remaining -= 1
        quota_placeholder.metric("Search Remaining", f"{remaining} / 100")
        
        with st.spinner(f"Scanning latest news for {target_input}..."):
            news_results = []
            try:
                # 検索クエリを最適化
                query = f'{target_input} 再生医療 ニュース 2025'
                url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={query}"
                data = requests.get(url).json()
                
                if "items" in data:
                    for item in data["items"]:
                        news_results.append({
                            'title': item.get('title'),
                            'body': item.get('snippet'),
                            'url': item.get('link')
                        })
            except Exception as e:
                st.error(f"Search Error: {e}")

            if news_results:
                # 履歴データを作成（AIサマリーの代わりにステータスを保存）
                    history_data = {
                    "target": target_input,
                    "ai_summary": f"{target_input} に関する最新ニュースを {len(news_results)} 件取得しました。",
                    "news": news_results[:6], # 上位6件を





















































