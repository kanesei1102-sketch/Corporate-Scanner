import streamlit as st
import google.generativeai as genai  # 公式SDK：URL管理が不要になります
import requests
import json
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account

# ==========================================
# 1. 初期設定（リセット＆再構築）
# ==========================================
try:
    # 新しく発行したAPIキー（お支払い情報紐付け済み）
    GEMINI_API_KEY = "AIzaSyBKlGZlt8ou3k8Q2aKCMtjiZV1XWE-MyEI".strip()
    
    # 公式SDKを初期化：これにより404エラーを根本から防ぎます
    genai.configure(api_key=GEMINI_API_KEY)
    
    # その他の検索・DB設定（Streamlit Secretsから取得）
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX = st.secrets["GOOGLE_CX"]
    key_dict = json.loads(st.secrets["FIRESTORE_KEY"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
except Exception as e:
    st.error(f"設定エラー: {e}")
    st.stop()

# ==========================================
# 2. 画面レイアウト
# ==========================================
st.set_page_config(page_title="Intel-Scope 1.5-Flash", layout="wide")
st.title("🚀 Intel-Scope: Gemini 1.5 Flash Engine")
st.caption("お支払い設定済みの新プロジェクトで動作中")

target = st.text_input("分析対象（例：富士フイルム 再生医療）")

# ==========================================
# 3. 解析メイン処理
# ==========================================
if st.button("EXECUTE ANALYSIS"):
    if not target:
        st.warning("対象を入力してください。")
    else:
        with st.spinner("情報を収集し、Gemini 1.5 Flash が思考中..."):
            
            # --- A. 最新ニュースの収集 ---
            news_context = ""
            try:
                search_url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={target} 2025"
                items = requests.get(search_url).json().get("items", [])
                news_context = "\n".join([f"タイトル: {i['title']}\n概要: {i['snippet']}" for i in items[:5]])
            except:
                st.error("検索エラーが発生しました。Google Search APIの設定を確認してください。")

            # --- B. Gemini 1.5 Flash 解析（SDK版） ---
            if news_context:
                try:
                    # モデルを厳密に指名
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 生成実行（SDKが最適な通信経路を自動選択します）
                    response = model.generate_content(
                        f"あなたは再生医療の専門家です。以下の最新情報を3点要約し、今後の展望を述べてください。\n\n{news_context}"
                    )
                    
                    # 結果表示
                    st.divider()
                    st.success("解析成功")
                    st.markdown(response.text)
                    
                    # 履歴保存（Firestore）
                    db.collection("search_history").add({
                        "target": target,
                        "ai_summary": response.text,
                        "timestamp": datetime.now()
                    })
                    
                except Exception as ai_err:
                    # エラーが出た場合でも、SDKなら原因が詳細にわかります
                    st.error(f"AI解析エラー: {ai_err}")
                    if "429" in str(ai_err):
                        st.warning("無料枠制限です。お支払い設定が反映されるまで数分かかる場合があります。")
            else:
                st.warning("関連するニュースが見つかりませんでした。")

















































