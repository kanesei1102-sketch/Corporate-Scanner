import streamlit as st
import requests
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
import json

# --- 1. システム初期設定 ---
st.set_page_config(page_title="Intel-Scope Personal", layout="wide")

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

# 履歴を最大10件取得
try:
    history_docs = history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()
    recent_history = [d.to_dict() for d in history_docs]
except:
    recent_history = []

# --- 3. レイアウト設定 ---
# サイドバー
st.sidebar.title("📊 Quota")
st.sidebar.metric("Search Remaining", f"{remaining} / 100")

st.sidebar.divider()
st.sidebar.title("📜 Search History")

# 履歴ボタンの生成
for h in recent_history:
    if 'timestamp' in h:
        ts = h['timestamp']
        date_str = ts.strftime('%Y/%m/%d %H:%M')
        t_key = ts.strftime('%Y%m%d%H%M%S%f')
    else:
        date_str = "Unknown Date"
        t_key = "unknown"

    if st.sidebar.button(f"📅 {date_str}\n{h['target']}", key=f"btn_{t_key}"):
        st.session_state.history_data = h

# メイン画面
st.title("Intel-Scope: Personal News Scanner")
st.markdown("再生医療・バイオテック企業の最新動向をリアルタイムでスキャンします。")
target_input = st.text_input("Target Entity", placeholder="企業名を入力...")

# --- 4. スキャン実行処理 ---
if st.button("EXECUTE SCAN", type="primary"):
    if not target_input:
        st.warning("社名を入力してください。")
    elif remaining <= 0:
        st.error("本日の検索枠上限です。")
    else:
        # 使用量カウントアップ
        usage_ref.set({"count": current_usage + 1}, merge=True)
        remaining -= 1
        
        with st.spinner(f"Scanning latest news for {target_input}..."):
            news_results = []
            try:
                # 2025年の最新情報を狙い撃ち
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
                history_data = {
                    "target": target_input,
                    "ai_summary": f"{target_input} に関する最新ニュースを {len(news_results)} 件取得しました。",
                    "news": news_results[:6],
                    "timestamp": datetime.now()
                }
                # Firestore保存 & セッション更新
                history_ref.add(history_data)
                st.session_state.history_data = history_data
                st.success("スキャン完了！履歴に保存しました。")
                st.rerun() # 履歴を即座にサイドバーに反映させるため
            else:
                st.warning("最新のニュースが見つかりませんでした。")

# --- 5. 結果表示エリア ---
if "history_data" in st.session_state:
    d = st.session_state.history_data
    st.divider()
    
    ts_display = d['timestamp']
    date_display = ts_display.strftime('%Y年%m月%d日 %H:%M') if hasattr(ts_display, 'strftime') else str(ts_display)
        
    st.subheader(f"📁 {d['target']}（{date_display} の結果）")
    
    cols = st.columns(2)
    for idx, n in enumerate(d['news']):
        with cols[idx % 2].expander(f"📌 {n['title']}", expanded=True):
            st.write(n['body'])
            st.markdown(f"[記事全文を読む]({n['url']})")























































