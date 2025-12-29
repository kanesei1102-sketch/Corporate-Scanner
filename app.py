import streamlit as st
from duckduckgo_search import DDGS
from docx import Document
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Corporation-Scope", layout="wide")
st.title("Corporation-Scope: Strategic Intelligence")

# サイドバーまたはトップに説明
st.caption("再生医療・バイオ業界の動向スキャナー：ニュースと市場状況をダイレクトに抽出します。")

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ, Cellares)...")

if st.button("EXECUTE"):
    if not target_input:
        st.warning("Please enter a name.")
    else:
        with st.spinner(f"Analyzing '{target_input}'..."):
            
            # 1. 上場判定（マーケットステータス）
            is_public = False
            # 大手企業や特定のキーワードで判定を強化
            public_keywords = ["sony", "ソニー", "トヨタ", "toyota", "terumo", "テルモ"]
            if any(k in target_input.lower() for k in public_keywords):
                is_public = True
            else:
                try:
                    with DDGS() as ddgs:
                        # 銘柄コードや株価を検索して判定
                        s_res = list(ddgs.text(f"{target_input} 株価 銘柄コード 証券", max_results=5))
                        for s in s_res:
                            # ニュースサイトや証券サイトに銘柄情報があれば上場とみなす
                            if any(k in s['href'].lower() for k in ["finance.yahoo", "kabutan", "nikkei.com", "shikiho.jp"]):
                                # セルリソーシズなど、親会社が上場しているが自社は非上場のケースを除外
                                if "セルリソーシズ" in target_input and "4880" in s['title']: continue
                                is_public = True
                                break
                except: pass

            # 2. ニュース検索（ここを一番厚くする）
            news_results = []
            try:
                with DDGS() as ddgs:
                    # 再生医療の文脈を少し混ぜて精度を上げる
                    search_query = f'"{target_input}" 再生医療 細胞治療 news'
                    news_results = list(ddgs.news(search_query, max_results=10))
                    
                    # ニュースが少ない場合は、広めに再検索
                    if len(news_results) < 3:
                        news_results += list(ddgs.news(f'"{target_input}"', max_results=5))
            except: pass

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
                st.caption("※ ニュースに基づいた自動判定です。")

            with col2:
                st.subheader("📡 Intelligence Feed")
                if not news_results:
                    st.warning("直近の関連ニュースは見つかりませんでした。")
                else:
                    for item in news_results:
                        # ニュースカードの表示
                        with st.expander(f"{item['title']}", expanded=True):
                            st.write(f"**Source:** {item['source']} | **Date:** {item['date']}")
                            st.write(item['body'])
                            st.markdown(f"[記事全文を読む]({item['url']})")

            # --- Word出力（シンプル版） ---
            doc = Document()
            doc.add_heading(f'Strategic Report: {target_input}', 0)
            doc.add_paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d')}")
            
            doc.add_heading('Market Status', level=1)
            doc.add_paragraph("Publicly Traded" if is_public else "Private / Unlisted")
            
            doc.add_heading('Latest News', level=1)
            for n in news_results[:8]:
                doc.add_heading(n['title'], level=2)
                doc.add_paragraph(f"Source: {n['source']} | Date: {n['date']}")
                doc.add_paragraph(n['body'])
                doc.add_paragraph(f"URL: {n['url']}")

            bio = BytesIO()
            doc.save(bio)
            st.download_button(
                label="💾 Download Summary Report",
                data=bio.getvalue(),
                file_name=f"{target_input}_Intelligence.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )






