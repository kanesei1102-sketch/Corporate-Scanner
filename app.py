import streamlit as st
import requests
from docx import Document
from io import BytesIO
from datetime import datetime

# --- セキュリティ設定（GitHub上には鍵を書きません） ---
# Streamlit Cloudの管理画面「Secrets」に保存した鍵を読み込みます
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX = st.secrets["GOOGLE_CX"]
except Exception:
    st.error("【管理者へ】StreamlitのSecrets設定で APIキー と CX を登録してください。")
    st.stop()

st.set_page_config(page_title="Corporation-Scope Pro", layout="wide")

# --- クレジット（残り回数）の管理 ---
# ※ブラウザを更新するとセッションが切れるため、カウントはリセットされます。
# 1月30日のランチ用には、あえて「セッション中の利用数」として提示するのがスマートです。
if 'search_count' not in st.session_state:
    st.session_state.search_count = 0

remaining = 100 - st.session_state.search_count

# サイドバー：実用性とプロフェッショナル感を両立した表示
st.sidebar.title("🔐 System Status")
st.sidebar.info("Connected to Google Search API")

st.sidebar.title("💳 Session Quota")
# リセットされることを逆手に取り、「このセッションでの残り」として表示
st.sidebar.metric(label="Available in this session", value=f"{remaining} / 100")

st.sidebar.caption("※Daily total limit: 100 searches (Google Standard)")

# パスワード機能（維持）
password = st.sidebar.text_input("Enter Passcode", type="password")
st.sidebar.title("💳 API Quota")
st.sidebar.metric(label="Remaining Searches (Today)", value=f"{remaining} / 100")

st.title("Corporation-Scope: Strategic Intelligence")
st.caption("Google Search API 搭載：再生医療・バイオ業界特化型スキャナー")

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ, ENCell)...")

# パスワードが一致するか確認（例として crc2025 にしています）
if st.button("EXECUTE"):
    if password != "crc2025":
        st.error("パスワードが正しくありません。")
    elif not target_input:
        st.warning("社名を入力してください。")
    elif remaining <= 0:
        st.error("本日の検索枠（100回）を使い切りました。")
    else:
        with st.spinner(f"Scanning Intelligence for '{target_input}'..."):
            st.session_state.search_count += 1
            
            news_results = []
            try:
                # 検索クエリの最適化
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













