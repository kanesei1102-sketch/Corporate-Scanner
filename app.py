import streamlit as st
import requests
from docx import Document
from io import BytesIO
from datetime import datetime

# --- 【最重要】取得した鍵をここに貼り付け ---
GOOGLE_API_KEY = "ここにAPIキーを貼る"
GOOGLE_CX = "ここに検索エンジンIDを貼る"

st.set_page_config(page_title="Corporation-Scope Pro", layout="wide")

# --- クレジット（残り回数）の計算機能 ---
# Google APIは一度の検索で情報を返しますが、無料枠は1日100件です。
# セッション内でカウントを管理します。
if 'search_count' not in st.session_state:
    st.session_state.search_count = 0

remaining = 100 - st.session_state.search_count

# サイドバーにクレジットを表示
st.sidebar.title("💳 API Quota")
st.sidebar.metric(label="Remaining Searches (Today)", value=f"{remaining} / 100")
if remaining < 10:
    st.sidebar.warning("残り回数がわずかです！本番に備えて温存してください。")

st.title("Corporation-Scope: Strategic Intelligence")
st.caption("Google Search API 搭載：高精度・制限なしの業界特化スキャナー。")

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ, ENCell)...")

if st.button("EXECUTE"):
    if not target_input:
        st.warning("Please enter a name.")
    elif remaining <= 0:
        st.error("本日の無料検索枠（100回）を使い切りました。明日までお待ちください。")
    else:
        with st.spinner(f"Querying Google Intelligence for '{target_input}'..."):
            # 検索実行時にカウントを増やす
            st.session_state.search_count += 1
            
            news_results = []
            try:
                # 検索精度の調整
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
            
            # --- ニュース表示 ---
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

            # Wordレポート作成（維持）
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









