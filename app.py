import streamlit as st
import google.generativeai as genai
import requests
import json
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account

# ==========================================
# 1. 接続・認証設定（Secretsから完全自動取得）
# ==========================================
try:
    # 1.5 Flash 専用APIキーの設定
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Google検索用設定
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX = st.secrets["GOOGLE_CX"]
    
    # Firestore設定（JSON文字列をパース）
    key_dict = json.loads(st.secrets["FIRESTORE_KEY"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
except Exception as e:
    st.error(f"【設定エラー】Secretsの読み込みに失敗しました。設定内容（キー名やJSON形式）を再確認してください。: {e}")
    st.stop()

# ==========================================
# 2. クォータ（利用枠）の管理
# ==========================================
today_str = datetime.now().strftime('%Y-%m-%d')
usage_ref = db.collection("daily_usage").document(today_str)
try:
    usage_doc = usage_ref.get()
    current_usage = usage_doc.to_dict().get("count", 0) if usage_doc.exists else 0
except:
    current_usage = 0
remaining = 100 - current_usage

# ==========================================
# 3. 画面レイアウト
# ==========================================
st.set_page_config(page_title="Intel-Scope 1.5 Flash", layout="wide")
st.title("🛡️ Intel-Scope: Gemini 1.5 Flash Engine")
st.sidebar.metric("本日の残り検索枠", f"{remaining} / 100")

target_input = st.text_input("分析対象を入力してください（企業名・技術名など）")

# ==========================================
# 4. 解析メインロジック（SDK版・最新仕様）
# ==========================================
if st.button("EXECUTE ANALYSIS"):
    if not target_input:
        st.warning("対象を入力してください。")
    elif remaining <= 0:
        st.error("本日の解析上限に達しました。")
    else:
        with st.spinner(f"「{target_input}」の最新情報を検索し、1.5 Flashが解析中..."):
            
            # --- A. 最新ニュースの収集 ---
            news_context = ""
            news_list = []
            try:
                search_url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={target_input} 2025"
                res = requests.get(search_url, timeout=10).json()
                if "items" in res:
                    for item in res["items"][:5]:
                        news_list.append({'title': item['title'], 'link': item['link']})
                        news_context += f"【{item['title']}】\n{item['snippet']}\n\n"
            except Exception as e:
                st.error(f"検索エラー: {e}")

            # --- B. Gemini 1.5 Flash 解析 ---
            if news_context:
                try:
                    # モデルを厳密に指名。SDKが正しいエンドポイントへ接続します。
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 生成実行（お支払い情報が紐付いていれば、404や429は起きません）
                    response = model.generate_content(
                        f"あなたは再生医療の専門コンサルタントです。以下の最新情報を3つの重要ポイントで要約してください。\n最後に、今後の展望を1文で添えてください。\n\n{news_context}"
                    )
                    
                    # 結果の表示
                    st.divider()
                    st.subheader(f"📊 分析結果: {target_input}")
                    st.info(response.text)
                    
                    # ニュースソースの表示
                    with st.expander("参照したニュースソース（上位5件）"):
                        for n in news_list:
                            st.markdown(f"- [{n['title']}]({n['link']})")

                    # 履歴の保存
                    db.collection("search_history").add({
                        "target": target_input,
                        "ai_summary": response.text,
                        "timestamp": datetime.now()
                    })
                    usage_ref.set({"count": current_usage + 1}, merge=True)
                    st.sidebar.success("解析成功・履歴を保存しました")
                    
                except Exception as ai_err:
                    # 詳細なエラーを出力して原因を突き止めやすくします
                    st.error(f"AI解析エラー: {ai_err}")
                    if "404" in str(ai_err):
                        st.warning("Google Cloudコンソールで 'Generative Language API' が有効になっているか確認してください。")
            else:
                st.warning("有効なニュース情報が見つかりませんでした。")


















































