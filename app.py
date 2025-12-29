import streamlit as st
from duckduckgo_search import DDGS
from docx import Document
from io import BytesIO
from datetime import datetime
import time
import random

st.set_page_config(page_title="Corporation-Scope", layout="wide")
st.title("Corporation-Scope: Strategic Intelligence")
st.caption("再生医療・バイオ業界特化：最新ニュースと上場状況をダイレクトに抽出します。")

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ, Cellares)...")

if st.button("EXECUTE"):
    if not target_input:
        st.warning("Please enter a name.")
    else:
        with st.spinner(f"Analyzing '{target_input}'..."):
            
          # 1. 上場判定（グローバル市場対応版）
            is_public = False
            # 明らかな上場企業キーワード
            public_keywords = ["sony", "ソニー", "トヨタ", "toyota", "terumo", "テルモ", "encell"]
            
            if any(k in target_input.lower() for k in public_keywords):
                is_public = True
            else:
                try:
                    with DDGS() as ddgs:
                        # 英語圏の証券用語「Stock Price」「Ticker」を混ぜて検索
                        s_res = list(ddgs.text(f"{target_input} stock price ticker 銘柄コード", max_results=8))
                        for s in s_res:
                            # 判定用ドメインに海外勢（Investing.com, Reuters, Bloomberg等）を追加
                            if any(k in s['href'].lower() for k in [
                                "finance.yahoo", "kabutan", "nikkei.com", "shikiho.jp", 
                                "investing.com", "reuters.com", "bloomberg.com", "marketwatch"
                            ]):
                                # セルリソーシズ自体の非上場判定は維持
                                if "セルリソーシズ" in target_input: continue 
                                is_public = True
                                break
                except: pass

            # 2. ニュース検索（アクセス制限回避 & 必中仕様）
            news_results = []
            try:
                # 検索エンジンを飽きさせないための「揺らぎ」
                suffix = random.choice(["ニュース", "最新", "動向", "news"])
                lang_query = "cell therapy" if target_input.isascii() else f"再生医療 {suffix}"
                
                with DDGS() as ddgs:
                    # 検索前に少し待機してブロックを防ぐ
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    # 検索
                    news_results = list(ddgs.news(f'"{target_input}" {lang_query}', max_results=8))
                    
                    # ヒットが少なければ、条件を緩めて再検索
                    if len(news_results) < 3:
                        time.sleep(0.5)
                        more_news = list(ddgs.news(f'"{target_input}"', max_results=8))
                        existing_urls = {n['url'] for n in news_results}
                        for n in more_news:
                            if n['url'] not in existing_urls:
                                news_results.append(n)
            except Exception:
                st.error("検索制限がかかりました。少し時間をおいて再度お試しください。")

            st.divider()
            
            # --- 画面表示 ---
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("📊 Market Status")
                if is_public:
                    st.success("### **Publicly Traded**\n(上場企業/グループ傘下)")
                else:
                    st.info("### **Private / Unlisted**\n(非上場 / スタートアップ)")
                st.markdown("---")
                st.caption("※ 公開情報に基づいた判定です。")

            with col2:
                st.subheader("📡 Intelligence Feed")
                if not news_results:
                    st.warning("直近のニュースは見つかりませんでした。")
                else:
                    for item in news_results:
                        with st.expander(f"{item['title']}", expanded=True):
                            st.write(f"**Source:** {item['source']} | **Date:** {item['date']}")
                            st.write(item['body'])
                            st.markdown(f"[記事全文を読む]({item['url']})")

            # --- Word出力（報告書作成） ---
            doc = Document()
            doc.add_heading(f'Strategic Report: {target_input}', 0)
            doc.add_paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d')}")
            doc.add_heading('Market Status', level=1)
            doc.add_paragraph("Publicly Traded" if is_public else "Private / Unlisted")
            doc.add_heading('Latest News', level=1)
            for n in news_results[:10]:
                doc.add_heading(n['title'], level=2)
                doc.add_paragraph(f"Source: {n['source']} | Date: {n['date']}")
                doc.add_paragraph(n['body'])
                doc.add_paragraph(f"URL: {n['url']}")

            bio = BytesIO()
            doc.save(bio)
            st.download_button(label="💾 Download Summary Report", data=bio.getvalue(), file_name=f"{target_input}_Report.docx")





