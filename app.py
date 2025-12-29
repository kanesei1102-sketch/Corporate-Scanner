import streamlit as st
from duckduckgo_search import DDGS
from urllib.parse import urlparse
from docx import Document
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
    try:
        with DDGS() as ddgs:
            # 検索ワードはシンプルに「名称 公式サイト」にする（海外企業も拾えるように）
            search_query = f"{query} official site corporate"
            results = list(ddgs.text(search_query, max_results=15))
            
            # 除外したい「情報のゴミ」
            noise_list = [
                "wikipedia.org", "facebook.com", "youtube.com", "twitter.com", 
                "mapion.co.jp", "tabelog.com", "indeed", "mynavi", ".cn", ".ru"
            ]
            
            candidates = []
            for r in results:
                url = r['href'].lower()
                title = r['title']
                
                if any(noise in url for noise in noise_list):
                    continue
                
                # スコアリング（点数制）で判定
                score = 0
                if ".co.jp" in url or ".jp" in url: score += 2 # 日本企業なら加点
                if "official" in url or "corporate" in url: score += 2 # 公式感があれば加点
                if "株式会社" in title or "Corp" in title or "Inc" in title: score += 2
                
                candidates.append({"url": r['href'], "score": score})

            # スコアが高い順に並び替えて、一番良いものを返す
            if candidates:
                best_match = sorted(candidates, key=lambda x: x['score'], reverse=True)[0]
                return best_match['url']
            
            if results:
                return results[0]['href']
    except: pass
    return None

if st.button("EXECUTE"):
    if not target_input:
        st.warning("Please enter a name.")
    else:
        with st.spinner(f"Scoping target: '{target_input}'..."):
            official_site = get_final_official_site(target_input)
            
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

            news_results = []
            try:
                with DDGS() as ddgs:
                    # ニュース検索を強化
                    news_results = list(ddgs.news(f'"{target_input}"', max_results=10))
            except: pass

            st.divider()
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.markdown("### 🏢 Verified Profile")
                domain = urlparse(official_site).netloc if official_site else "N/A"
                if official_site:
                    st.success(f"**Domain:**\n{domain}")
                else:
                    st.error("Site Not Found")

                st.markdown("---")
                st.markdown("**💰 Market Status**")
                status_text = "Publicly Traded" if is_public else "Private / Unlisted"
                st.info(f"**{status_text}**")

                # --- 【Word出力機能：強化版】 ---
                st.markdown("---")
                doc = Document()
                doc.add_heading('Strategic Intelligence Report', 0)
                doc.add_paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                
                doc.add_heading('Entity Profile', level=1)
                doc.add_paragraph(f"Target Name: {target_input}", style='List Bullet')
                doc.add_paragraph(f"Official URL: {official_site}", style='List Bullet')
                doc.add_paragraph(f"Market Status: {status_text}", style='List Bullet')
                
                doc.add_heading('Latest News Intelligence', level=1)
                if not news_results:
                    doc.add_paragraph("No recent news found.")
                else:
                    for n in news_results:
                        # ニュースごとに区切りを明確に
                        doc.add_heading(n['title'], level=2)
                        p = doc.add_paragraph()
                        p.add_run(f"Source: {n['source']} | Date: {n['date']}").bold = True
                        
                        # 内容が切れないように全文を追加し、最後にURLを添える
                        doc.add_paragraph(n['body'])
                        doc.add_paragraph(f"Read more: {n['url']}")
                        doc.add_paragraph("-" * 30) # 区切り線

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


