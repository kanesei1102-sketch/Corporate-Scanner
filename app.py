import streamlit as st
from duckduckgo_search import DDGS
from docx import Document
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Corporation-Scope", layout="wide")
st.title("Corporation-Scope: Strategic Intelligence")

st.caption("再生医療・バイオ業界特化：最新ニュースと上場状況をダイレクトに抽出します。")

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ, Cellares)...")

if st.button("EXECUTE"):
    if not target_input:
        st.warning("Please enter a name.")
    else:
        with st.spinner(f"Analyzing '{target_input}'..."):
            
            # 1. 上場判定
            is_public = False
            public_keywords = ["sony", "ソニー", "トヨタ", "toyota", "terumo", "テルモ"]
            if any(k in target_input.lower() for k in public_keywords):
                is_public = True
            else:
                try:
                    with DDGS() as ddgs:
                        s_res = list(ddgs.text(f"{target_input} 株価 銘柄コード 証券", max_results=5))
                        for s in s_res:
                            if any(k in s['href'].lower() for k in ["finance.yahoo", "kabutan", "nikkei.com", "shikiho.jp"]):
                                if "セルリソーシズ" in target_input: continue # 自社は非上場
                                is_public = True
                                break
                except: pass

            # 2. ニュース検索（段階的検索でヒット率を最大化）
            news_results = []
            try:
                with DDGS() as ddgs:
                    # ステップ1：業界キーワードを付けて検索
                    lang_query = "cell therapy" if target_input.isascii() else "再生医療"
                    news_results = list(ddgs.news(f'"{target_input}" {lang_query}', max_results=10))
                    
                    # ステップ2：少なければ社名のみで検索
                    if len(news_results) < 3:
                        existing_urls = {n['url'] for n in news_results}
                        for n in list(ddgs.news(f'"{target_input}"', max_results=10)):
                            if n['url'] not in existing_urls:
                                news_results.append(n)
            except: pass

            st.divider()
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("📊 Market Status")
                if is_public:
                    st.success("### **Publicly Traded**\n(上場企業/グループ傘下)")
                else:
                    st.info("### **Private / Unlisted**\n(非上場 / スタートアップ)")
                st.caption("※ 公開情報に基づいた自動判定です。")

            with col2:
                st.subheader("📡 Intelligence Feed")
                if not news_results:
                    st.warning("直近の関連ニュースは見つかりませんでした。")
                else:
                    # ニュースを新しい順に表示
                    for item in news_results:
                        with st.expander(f"{item['title']}", expanded=True):
                            st.write(f"**Source:** {item['source']} | **Date:** {item['date']}")
                            st.write(item['body'])
                            st.markdown(f"[記事全文を読む]({item['url']})")

            # Wordレポート作成
            doc = Document()
            doc.add_heading(f'Strategic Report: {target_input}', 0)
            doc.add_paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d')}")
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


