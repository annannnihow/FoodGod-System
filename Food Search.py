import streamlit as st
import requests
import json
from google import genai

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="AI 全球美食探險家", page_icon="🍜", layout="centered")

# --- 2. 安全讀取 API Keys (從 Streamlit Secrets) ---
# 部署到 GitHub/Streamlit Cloud 後，請在後台 Secrets 設定這兩個變數
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GOOGLE_MAPS_API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
except:
    st.error("❌ 找不到 API Key，請確保已在 Streamlit Secrets 中設定。")
    st.stop()

# 初始化 Gemini 客戶端
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = 'gemini-2.5-flash' # 推薦使用 Flash，速度快且免費額度穩

# --- 3. 核心邏輯函式 (保留你最完整的邏輯) ---

def parse_user_intent(user_input):
    """解析使用者意圖，支援全球地點"""
    prompt = f"""
    你是一個專業的全球美食地圖搜尋助手。
    請從以下使用者的輸入中，提取出『地理位置』與『料理種類』。
    請務必只回傳 JSON 格式。
    使用者輸入：「{user_input}」
    輸出範例：{{"location": "東京新宿", "search_keywords": ["拉麵", "Ramen"]}}
    """
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    clean_text = response.text.replace('```json', '').replace('
```', '').strip()
    return json.loads(clean_text)

def search_google_places(location, keywords):
    """Google 地圖搜尋 (評分 4.0+ & 評論 100+)"""
    search_query = f"{location} {keywords[0]}"
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={search_query}&language=zh-TW&key={GOOGLE_MAPS_API_KEY}"
    res = requests.get(url).json()
    results = res.get('results', [])
    return [p for p in results if p.get('rating', 0) >= 4.0 and p.get('user_ratings_total', 0) >= 100][:3]

def get_place_details(place_id):
    """抓取評論、網址與營業時間"""
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,url,reviews,current_opening_hours&language=zh-TW&key={GOOGLE_MAPS_API_KEY}"
    res = requests.get(url).json().get('result', {})
    reviews = [r['text'] for r in res.get('reviews', []) if 'text' in r]
    hours = res.get('current_opening_hours', {}).get('weekday_text', [])
    return reviews, res.get('url', ''), hours

def summarize_with_ai(place_name, reviews):
    """AI 深度分析：含價格、付款方式、翻譯成繁體中文"""
    if not reviews: return "目前無足夠評論供 AI 分析。"
    reviews_text = "\n".join(f"- {text}" for text in reviews)
    prompt = f"""
    你是一個嚴謹的美食評論家。請根據以下真實評論總結【{place_name}】的特色。
    規則：
    1. 列出「3大特色/優點」。
    2. 列出「必點菜色與價格」(若有提到)。
    3. 列出「付款方式」(例如：現金、刷卡、Apple Pay)。
    4. 無論原文為何，一律使用「繁體中文」輸出。
    評論內容：\n{reviews_text}
    """
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    return response.text

# --- 4. Streamlit 前端介面 ---

st.title("🤖 終極 AI 美食導航員")
st.markdown("輸入任何地點與種類，AI 會為你翻遍全球 Google 評論並總結精華！")

# 使用者輸入區
user_query = st.text_input("你想去哪裡吃什麼？", placeholder="例如：永和 眷村菜、LA K-Town BBQ、東京 壽司")

if st.button("開始深度肉搜"):
    if user_query:
        with st.spinner("🚀 AI 正在跨國讀取評論並翻譯中..."):
            try:
                # 1. 解析
                intent = parse_user_intent(user_query)
                # 2. 搜尋
                places = search_google_places(intent['location'], intent['search_keywords'])
                
                if not places:
                    st.warning("⚠️ 找不到符合高標準 (4星+ & 100+評論) 的店家。")
                else:
                    for place in places:
                        # 3. 抓細節
                        reviews, maps_url, hours = get_place_details(place['place_id'])
                        # 4. AI 總結
                        ai_summary = summarize_with_ai(place['name'], reviews)
                        
                        # --- 網頁漂亮的排版 ---
                        with st.container(border=True):
                            st.subheader(f"🍴 {place['name']}")
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                st.write(f"⭐ **評分**：{place['rating']}")
                            with col2:
                                st.write(f"💬 **評論數**：{place['user_ratings_total']}")
                            
                            # 營業時間摺疊選單
                            with st.expander("📅 查看營業時間"):
                                for h in hours: st.write(h)
                            
                            # AI 點評區
                            st.markdown("#### 💡 AI 老饕深度點評")
                            st.write(ai_summary)
                            
                            # 📍 導航按鈕 (手機點擊會自動跳轉 APP)
                            st.link_button(f"🚩 導航至 {place['name']}", maps_url)
                            
            except Exception as e:
                st.error(f"發生小意外：{e}")
    else:
        st.info("請輸入地點後再按搜尋喔！")