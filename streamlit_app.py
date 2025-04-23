import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import openai
import datetime

# --- 1. 讀取並驗證 Secrets (在 cache decorator 外) ---
# 取得 OpenAI API Key
openai_key = st.secrets.get('openai_api_key') or st.secrets.get('openai', {}).get('api_key')
if not openai_key:
    st.error("錯誤：未設定 OpenAI API Key。請於 Streamlit Cloud Secrets 中新增 openai_api_key 或 [openai] api_key。")
    st.stop()
openai.api_key = openai_key

# 取得並解析 Google Sheets 憑證
creds_raw = st.secrets.get('google_sheets', {}).get('credentials', '')
# 提示：credentials 必須是有效的 JSON，使用三重引號並無多餘縮排或空格
if not creds_raw:
    st.error("錯誤：未設定 Google Sheets credentials。請於 Secrets 中填入 credentials。示例：
```toml
[google_sheets]
credentials = '''{"type":"service_account","project_id":"...","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}'''```
請注意：1) 三重引號不應有額外縮排；2) private_key 換行以雙斜線+`n`表示。")
    st.stop()
try:
    creds_dict = json.loads(creds_raw)
except json.JSONDecodeError as e:
    st.error(f"錯誤：Google Sheets credentials JSON 解析失敗。請檢查格式與轉義：{e}")
    st.stop()

# 取得試算表名稱
sheet_name = st.secrets.get('google_sheets', {}).get('sheet_name', '').strip()
if not sheet_name:
    st.error("錯誤：未設定 Google Sheets sheet_name。請於 Secrets 中填入 sheet_name，例如：`sheet_name = \"SmartMeds_DB\"`。")
    st.stop()

# --- Streamlit 頁面設定 ---
st.set_page_config(page_title="智藥照護小幫手 v2", layout="wide")
st.title("🧠 智藥照護小幫手 SmartMeds-AI v2")
st.markdown("系統自動偵測並同步老年人用藥風險與交互作用，支援藥師審核並自動上傳至 Google Sheets。")
st.set_page_config(page_title="智藥照護小幫手 v2", layout="wide")
st.title("🧠 智藥照護小幫手 SmartMeds-AI v2")
st.markdown("系統自動偵測並同步老年人用藥風險與交互作用，支援藥師審核並自動上傳至 Google Sheets。")

# --- 2. 建立 Google Sheets 連線 (cache 裝飾器內不使用 UI) ---
@st.cache_resource
def connect_to_sheet(creds_dict, sheet_name):
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

# --- 3. 讀取 Google Sheets 資料 ---
@st.cache_data
def load_data(sheet):
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    # 藥品名稱欄位：逗號分隔轉 list
    df['藥品名稱'] = df['藥品名稱'].apply(
        lambda x: [d.strip() for d in x.split(',')] if isinstance(x, str) else []
    )
    # 初始化必要欄位
    for col in ['用藥風險','可能交互作用','審核藥師','藥師風險判讀','修正意見','審核時間']:
        df[col] = df.get(col, '')
    return df

# --- 4. 寫回 Google Sheets ---
def append_to_sheet(sheet, row_dict: dict):
    row = [
        row_dict.get('姓名',''),
        row_dict.get('年齡',''),
        row_dict.get('疾病',''),
        ','.join(row_dict.get('藥品名稱',[])),
        row_dict.get('用藥風險',''),
        row_dict.get('可能交互作用',''),
        row_dict.get('審核藥師',''),
        row_dict.get('藥師風險判讀',''),
        row_dict.get('修正意見',''),
        row_dict.get('審核時間','')
    ]
    sheet.append_row(row)

# --- 5. OpenAI: 風險與交互作用判讀 ---
@st.cache_data
def gen_risk(meds: list) -> str:
    if not meds:
        return ''
    prompt = f"請根據Beers標準，說明以下藥物對老年人的潛在用藥風險：{', '.join(meds)}。簡要列點說明。"
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()

@st.cache_data
def gen_interactions(meds: list) -> str:
    if len(meds) < 2:
        return ''
    prompt = f"以下藥物列表中，請判斷是否存在交互作用並說明：{', '.join(meds)}。若無交互作用請回覆「無」。"
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()

# --- 6. 主程式執行流程 ---
# 連線與讀資料
sheet = connect_to_sheet(creds_dict, sheet_name)
df = load_data(sheet)

# AI 偵測按鈕
if st.button('🔄 AI 偵測所有風險與交互作用'):
    for idx, row in df.iterrows():
        meds = row['藥品名稱']
        df.at[idx, '用藥風險'] = gen_risk(meds)
        df.at[idx, '可能交互作用'] = gen_interactions(meds)
    st.success('AI 偵測完成，請至下方審核並同步至 Google Sheets')

# 藥師審核互動
st.subheader('🩺 藥師審核互動區')
col1, col2 = st.columns([2,3])
with col1:
    selected = st.selectbox('選擇住民：', df['姓名'])
    row = df[df['姓名']==selected].iloc[0]
    st.markdown(f"**基本資料**：{row['姓名']}，{row['年齡']}歲，疾病：{row['疾病']}")
    st.markdown(f"**用藥清單**：{','.join(row['藥品名稱'])}")
    st.markdown(f"**AI 風險**：{row['用藥風險']}")
    st.markdown(f"**AI 交互作用**：{row['可能交互作用']}")
with col2:
    pharmacist = st.text_input('審核藥師姓名')
    risk_level = st.radio('藥師風險判讀', ['高','中','低'], horizontal=True)
    correction = st.text_area('修正意見')
    if st.button('✅ 提交並同步'):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df.loc[df['姓名']==selected, ['審核藥師','藥師風險判讀','修正意見','審核時間']] = [pharmacist, risk_level, correction, now]
        append_to_sheet(sheet, df[df['姓名']==selected].iloc[0].to_dict())
        st.success('審核已同步至 Google Sheets')

# 篩選顯示
with st.sidebar:
    st.header('🔍 篩選條件')
    show_inter = st.checkbox('僅顯示有交互作用')

if show_inter:
    disp = df[df['可能交互作用'].str.strip()!='']
else:
    disp = df
report = disp.copy()
report['藥品名稱'] = report['藥品名稱'].apply(lambda x: ','.join(x))

st.subheader('📋 綜合報表')
st.dataframe(report)

# 匯出
csv = report.to_csv(index=False).encode('utf-8-sig')
st.download_button('📤 匯出 CSV', csv, 'smartmeds_report.csv', 'text/csv')







