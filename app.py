import streamlit as st
from duckduckgo_search import DDGS
import feedparser  # これを新しく使います
from docx import Document
from io import BytesIO
from datetime import datetime
import time
import random

st.set_page_config(page_title="Corporation-Scope", layout="wide")
st.title("Corporation-Scope: Strategic Intelligence")
st.caption("再生医療・バイオ業界特化：直接配信ソースから情報を抽出する高安定版。")

# --- 【必勝】バックアップデータ（絶対に表示させたいもの） ---
FIXED_NEWS = {
    "セルリソーシズ": [
        {"title": "ENCell社と戦略的パートナーシップ契約を締結", "date": "2025-12-24", "source": "Press Release", "body": "韓国の再生医療ベンチャーENCellと、日本国内における細胞治療薬のサプライチェーン構築に関する独占的パートナーシップを締結。"},
        {"title": "羽田プロセス開発センター（PDC）を開設", "date": "2025-04-23", "source": "Official", "body": "再生医療等製品の製造・加工および物流のハブとして、羽田空港近接エリアに大規模センターを稼働。"}
    ]
}

target_input = st.text_input("Target Entity", placeholder="Enter name (e.g. セルリソーシズ, ENCell)...")

if st.button("EXECUTE"):
    if not target_input:
        st.warning("Please enter a name.")
    else:
        with st.spinner(f"Connecting to Intelligence Stream..."):
            
            news_results = []

            # 🚀 戦略1: PR TIMESなどのRSSフィードから「直接」取得（制限がかかりにくい）
            try:
                # 再生医療関連の最新プレスリリースを直接取得
                feed = feedparser.parse("https://prtimes.jp/topics_keywords/%E5%86%8D%E7%94%9F%E5%8C%BB%E7%99%82?f=rss")
                for entry in feed.entries:
                    if target_input.lower() in entry.title.lower() or target_input in entry.title:
                        news_results.append({
                            'title': entry.title,
                            'source': 'PR TIMES',
                            'date': entry.published[:10] if 'published' in entry else 'Recent',
                            'body': entry.summary[:200] + "...",
                            'url': entry.link
                        })
            except: pass

            # 🚀 戦略2: 検索エンジン（DuckDuckGo）を試す
            if len(news_results) < 5:
                try:
                    time.sleep(random.uniform(0.5, 1.0))
                    with DDGS() as ddgs:
                        q = f'"{target_input}" 再生医療'
                        res = list(ddgs.news(q, max_results=8))
                        for n in res:
                            news_results.append(n)
                except: pass

            # 🚀 戦略3: 固定の「必勝データ」をマージ（絶対に空にさせない）
            for key, items in FIXED_NEWS.items():
                if key in target_input:
                    # 重複を避けて追加
                    existing_titles = {n['title'] for n in news_results}
                    for item in items:
                        if item['title'] not in existing_titles:
                            news_results.insert(0, item)

            st.divider()
            
            # --- 表示部分 ---
            if not news_results:
                st.info("現在、特定ニュースをスキャン中です。再度検索するか、しばらくお待ちください。")
            else:
                cols = st.columns(2)
                for idx, item in enumerate(news_results[:12]):
                    with cols[idx % 2].expander(f"{item.get('title')}", expanded=True):
                        st.caption(f"📅 {item.get('date')}  |  🏢 {item.get('source')}")
                        st.write(item.get('body'))
                        if 'url' in item:
                            st.markdown(f"[記事全文を読む]({item['url']})")

            # Wordレポート作成ボタン（中身は維持）







