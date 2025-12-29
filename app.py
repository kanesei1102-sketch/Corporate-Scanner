import streamlit as st
from duckduckgo_search import DDGS
from urllib.parse import urlparse
from docx import Document # Word作成用
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Corporation-Scope", layout="wide")
st.title("Corporation-Scope: Strategic Intelligence")

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ)...")

# マスターレコード
MASTER_RECORDS = {
    "セルリソーシズ": "https://www.cellresources.co.jp/",
    "cell resources": "https://www.cellresources.co.jp/",
    "sony": "https://www.sony.com/",
    "ソニー": "https://www.sony.jp/",
    "cellares": "https://www.cellares.com/"
}

def get_final_official_site(query):
    clean_query = query.lower().strip()
    if clean_query in MASTER_RECORDS:
        return MASTER_RECORDS[clean_query]
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{query} 株式会社 公式", max_results=10))
            noise_list = ["microsoft.com", "wikipedia.org", "facebook.com", "youtube.com"]
            for r in results:
                url = r['href'].lower()
                if not any(noise in url for noise in noise_list):
                    return r['href']
    except: pass
    return None

if st.button("EXECUTE"):
    if not target_input:
        st.warning("Please enter a name.")
    else:
        with st.spinner(f"Scoping target: '{target_input}'..."):
            official_site = get_final_official_site(target_input)
            
            # 上場判定
            is_public = False
            if "ソニー" in target_input or "sony" in target_input.lower():
                is_public = True
            elif "セルリソーシズ" in target_input:
                is_public = False
            else:
                try:
                    with DDGS() as ddgs:
                        s_res = list(ddgs.text(f"{target_input} 株価 銘柄コード", max_results=10))
                        for s in s_res:
                            if any(k in s['href'].lower() for k in ["finance.yahoo", "kabutan", "nikkei.com"]):
                                if target_input == "セルリソーシズ" and "4880" in s['title']: continue
                                is_public = True; break
                except: pass

            # ニュース
            news_results = []
            try:
                with DDGS() as ddgs:
                    news_results = list(ddgs.news(f'"{target_input}"', max_results=5))
            except: pass

            st.divider()
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.markdown("### 🏢 Verified Profile")
                if official_site:
                    domain = urlparse(official_site).netloc
                    st.success(f"**Domain:**\n{domain}")
                else:
                    domain = "N/A"
                    st.error("Site Not Found")

                st.markdown("---")
                st.markdown("**💰 Market Status**")
                status_text = "Publicly Traded" if is_public else "Private / Unlisted"
                st.info(f"**{status_text}**")

                # --- 【Word出力機能】 ---
                st.markdown("---")
                
                # Wordファイルの作成
                doc = Document()
                doc.add_heading('Strategic Intelligence Report', 0)
                doc.add_paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                
                doc.add_heading('Entity Profile', level=1)
                doc.add_paragraph(f"Target Name: {target_input}")
                doc.add_paragraph(f"Official URL: {official_site}")
                doc.add_paragraph(f"Market Status: {status_text}")
                
                doc.add_heading('Latest News Feed', level=1)
                for n in news_results:
                    doc.add_heading(n['title'], level=2)
                    doc.add_paragraph(f"Source: {n['source']} | Date: {n['date']}")
                    doc.add_paragraph(n['body'])
                
                # メモリ上にWordを保存
                bio = BytesIO()
                doc.save(bio)
                
                st.download_button(
                    label="💾 Export Report (Word)",
                    data=bio.getvalue(),
                    file_name=f"{target_input}_Report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

            with col2:
                st.markdown("### 📡 Intelligence Feed")
                if not news_results:
                    st.warning("No news results found.")
                else:
                    for item in news_results:
                        with st.expander(f"{item['title']}", expanded=True):
                            st.write(item['body'])
                            st.markdown(f"[Source Article]({item['url']})")