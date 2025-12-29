import streamlit as st
import requests
from docx import Document
from io import BytesIO
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
import json

# --- 1. セキュリティ設定（Secretsから読み込み） ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX = st.secrets["GOOGLE_CX"]
    
    # Firestoreの認証情報を読み込み
    key_dict = json.loads(st.secrets["FIRESTORE_KEY"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
except Exception as e:
    st.error(f"システム設定エラー: Secretsを確認してください。 ({e})")
    st.stop()

# --- 2. データベース（Firestore）から今日の使用回数を取得 ---
# 毎日日本時間のAM0時にリセットしたい場合は、日付をキーにします
today_str = datetime.now().strftime('%Y-%m-%d')
doc_ref = db.collection("daily_usage").document(today_str)

try:
    doc = doc_ref.get()
    if not doc.exists:
        doc_ref.set({"count": 0})
        current_usage = 0
    else:
        current_usage = doc.to_dict().get("count", 0)
except Exception:
    current_usage = 0

remaining = 100 - current_usage

# --- 3. 画面レイアウト ---
st.set_page_config(page_title="Corporation-Scope Pro", layout="wide")

# サイドバー：更新しても減ったままのクレジットを表示
st.sidebar.title("🔐 Authentication")
password = st.sidebar.text_input("Enter Passcode", type="password")

st.sidebar.title("💳 Global Quota")
st.sidebar.metric(label="Today's Remaining", value=f"{remaining} / 100")
st.sidebar.caption("※この数字は全ユーザーで共有・同期されています。")

st.title("Corporation-Scope: Strategic Intelligence")
st.caption("Firestore & Google Search API 連動：更新しても利用状況を完全維持するプロ仕様。")

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ, ENCell)...")

if st.button("EXECUTE"):
    if password != "crc2025":
        st.error("パスワードが正しくありません。")
    elif not target_input:
        st.warning("社名を入力してください。")
    elif remaining <= 0:
        st.error("本日の無料検索枠（100回）を使い切りました。")
    else:
        with st.spinner(f"Querying Intelligence for '{target_input}'..."):
            
            # 🔍 検索実行
            news_results = []
            try:
                query = f'{target_input} 再生医療 ニュース 2025' if not target_input.isascii() else f'{target_input} "cell therapy" news'
                url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={query}"
                response = requests.get(url)
                data = response.json()
                
                if "items" in data:
                    for item in data["items"]:
                        news_results.append({
                            'title': item.get('title'),
                            'source': item.get('displayLink'),
                            'body': item.get('snippet'),
                            'url': item.get('link')
                        })
                    
                    # ✅ 検索成功時のみFirestoreのカウントを+1（更新しても戻らない！）
                    doc_ref.update({"count": firestore.Increment(1)})
                    # 画面表示用の数字も即座に更新
                    remaining -= 1
                    
            except Exception as e:
                st.error(f"API Error: {e}")

            st.divider()
            
            if not news_results:
                st.warning("関連情報が見つかりませんでした。")
            else:
                st.subheader(f"📡 Real-time Intelligence: {target_input}")
                cols = st.columns(2)
                for idx, item in enumerate(news_results[:10]):
                    with cols[idx % 2].expander(f"{item['title']}", expanded=True):
                        st.caption(f"🏢 Source: {item['source']}")
                        st.write(item['body'])
                        st.markdown(f"[記事全文を読む]({item['url']})")

            # Wordレポート作成
            doc = Document()
            doc.add_heading(f'Strategic Report: {target_input}', 0)
            doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d')}")
            for n in news_results[:10]:
                doc.add_heading(n['title'], level=2)
                doc.add_paragraph(n['body'])
                doc.add_paragraph(f"URL: {n['url']}")
            bio = BytesIO()
            doc.save(bio)
            st.download_button(label="💾 Download Summary Report", data=bio.getvalue(), file_name=f"{target_input}_Report.docx")














