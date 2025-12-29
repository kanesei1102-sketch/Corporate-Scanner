import streamlit as st
import requests
from docx import Document
from io import BytesIO
from datetime import datetime

# --- 【最重要】ここに取得した「鍵」を貼り付けてください ---
GOOGLE_API_KEY = "AIzaSyAk2sfv67SGkZ4gAiKPLdSPgSWIAYYO0zo"
GOOGLE_CX = "<script async src="https://cse.google.com/cse.js?cx=43b6a568b52e34409">
</script>
<div class="gcse-search"></div>"

st.set_page_config(page_title="Corporation-Scope Pro", layout="wide")
st.title("Corporation-Scope: Strategic Intelligence")
st.caption("Google Search API 搭載：アクセス制限なしの業界特化スキャナー。")

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ, ENCell, Cellares)...")

if st.button("EXECUTE"):
    if not target_input:
        st.warning("Please enter a name.")
    else:
        with st.spinner(f"Querying Google Intelligence for '{target_input}'..."):
            
            news_results = []
            
            try:
                # 検索ワードの調整（ヒット率を高めるためにダブルクォーテーションを外しました）
                if target_input.isascii():
                    query = f'{target_input} "cell therapy" news'
                else:
                    query = f'{target_input} 再生医療 ニュース 2025'
                
                url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={query}"
                
                response = requests.get(url)
                data = response.json()
                
                # エラーチェック
                if "error" in data:
                    st.error(f"Google API Error: {data['error']['message']}")
                elif "items" in data:
                    for item in data["items"]:
                        news_results.append({
                            'title': item.get('title'),
                            'source': item.get('displayLink'),
                            'date': 'Recent',
                            'body': item.get('snippet'),
                            'url': item.get('link')
                        })
                
                # 1件も出ない場合のリトライ（社名のみで検索）
                if not news_results and "error" not in data:
                    url_retry = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={target_input}"
                    resp_retry = requests.get(url_retry)
                    data_retry = resp_retry.json()
                    if "items" in data_retry:
                        for item in data_retry["items"]:
                            news_results.append({
                                'title': item.get('title'),
                                'source': item.get('displayLink'),
                                'date': 'General Info',
                                'body': item.get('snippet'),
                                'url': item.get('link')
                            })

            except Exception as e:
                st.error(f"Connection Error: {e}")

            st.divider()
            
            # --- 画面表示 ---
            if not news_results:
                st.warning("関連情報が見つかりませんでした。設定を確認するか、別の社名をお試しください。")
            else:
                st.subheader(f"📡 Real-time Intelligence: {target_input}")
                cols = st.columns(2)
                for idx, item in enumerate(news_results[:12]):
                    with cols[idx % 2].expander(f"{item['title']}", expanded=True):
                        st.caption(f"🏢 Source: {item['source']}")
                        st.write(item['body'])
                        st.markdown(f"[記事全文を読む]({item['url']})")

            # --- Wordレポート作成 ---
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








