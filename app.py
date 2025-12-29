import streamlit as st
from duckduckgo_search import DDGS
from docx import Document
from io import BytesIO
from datetime import datetime
import time
import random

st.set_page_config(page_title="Corporation-Scope", layout="wide")
st.title("Corporation-Scope: Strategic Intelligence")
st.caption("再生医療・バイオ業界特化：最新ニュースと業界動向を一点突破で抽出します。")

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ, ENCell, Cellares)...")

if st.button("EXECUTE"):
    if not target_input:
        st.warning("Please enter a name.")
    else:
        with st.spinner(f"Scanning Intelligence for '{target_input}'..."):
            
            # ニュース検索（アクセス制限回避 & 必中仕様）
            news_results = []
            try:
                suffix = random.choice(["ニュース", "最新", "動向", "news"])
                # 英語か日本語かでキーワード切り替え
                lang_query = "cell therapy" if target_input.isascii() else f"再生医療 {suffix}"
                
                with DDGS() as ddgs:
                    # 検索前に待機してブロックを防ぐ
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    # ステップ1：業界キーワード付き検索
                    news_results = list(ddgs.news(f'"{target_input}" {lang_query}', max_results=12))
                    
                    # ステップ2：少なければ社名のみで再検索
                    if len(news_results) < 4:
                        time.sleep(0.5)
                        more_news = list(ddgs.news(f'"{target_input}"', max_results=10))
                        existing_urls = {n['url'] for n in news_results}
                        for n in more_news:
                            if n['url'] not in existing_urls:
                                news_results.append(n)
            except Exception:
                st.error("検索エンジンが混み合っています。少し時間をおいて再度お試しください。")

            st.divider()
            
            # --- 画面表示（ニュース全画面表示） ---
            st.subheader(f"📡 Latest Intelligence: {target_input}")
            
            if not news_results:
                st.warning("直近の関連ニュースは見つかりませんでした。")
            else:
                # 2カラムでニュースを並べて、一度にたくさんの情報が見えるようにする
                cols = st.columns(2)
                for idx, item in enumerate(news_results):
                    with cols[idx % 2].expander(f"{item['title']}", expanded=True):
                        st.caption(f"📅 {item['date']}  |  🏢 {item['source']}")
                        st.write(item['body'])
                        st.markdown(f"[記事全文を読む]({item['url']})")

            # --- Wordレポート（ニュースのみのシンプル版） ---
            doc = Document()
            doc.add_heading(f'Strategic Intelligence Report: {target_input}', 0)
            doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d')}")
            
            doc.add_heading('Latest News & Actions', level=1)
            for n in news_results[:12]:
                doc.add_heading(n['title'], level=2)
                doc.add_paragraph(f"Date: {n['date']} | Source: {n['source']}")
                doc.add_paragraph(n['body'])
                doc.add_paragraph(f"URL: {n['url']}")

            bio = BytesIO()
            doc.save(bio)
            st.download_button(
                label="💾 Download Summary Report",
                data=bio.getvalue(),
                file_name=f"{target_input}_Intelligence.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )






