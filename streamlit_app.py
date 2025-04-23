import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import openai
import datetime

# --- 配置 ---
# 取得 OpenAI API Key，支援兩種 Secrets 格式
openai_key = None
if 'openai' in st.secrets and 'api_key' in st.secrets['openai']:
    openai_key = st.secrets['openai']['api_key']
elif 'openai_api_key' in st.secrets:
    openai_key = st.secrets['openai_api_key']
if not openai_key:
    st.error("錯誤：未設定 OpenAI API Key。請於 Streamlit Cloud Secrets 中新增 `openai_api_key` 或 `[openai] api_key`。")
    st.stop()
openai.api_key = openai_key

# Streamlit 頁面設定
st.set_page_config(page_title="智藥照護小幫手 v2", layout="wide")
st.title("🧠 智藥照護小幫手 SmartMeds-AI v2")
st.markdown("系統自動偵測老年人用藥風險與交互作用，並可由藥師審核後自動同步至 Google Sheets。")

# --- Google Sheets 連線 ---
@st.cache_resource
def connect_to_sheet():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds_dict = json.loads(st.secrets['google_sheets']['credentials'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(st.secrets['google_sheets']['sheet_name']).sheet1
    return sheet

# --- 讀取 Google Sheets 資料 ---
@st.cache_data
def load_data():
    sheet = connect_to_sheet()
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    # 藥品名稱欄位：逗號分隔轉 list
    df['藥品名稱'] = df['藥品名稱'].apply(lambda x: [d.strip() for d in x.split(',')] if isinstance(x, str) else [])
    # 初始化欄位
    for col in ['用藥風險','可能交互作用','審核藥師','藥師風險判讀','修正意見','審核時間']:
        if col not in df.columns:
            df[col] = ''
    return df

# --- 寫回 Google Sheets ---
def append_to_sheet(row_dict: dict):
    sheet = connect_to_sheet()
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

# --- OpenAI 計算風險與交互作用 ---
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

# --- 主程式 ---
# 1. 載入資料
df = load_data()
# 確保 AI 欄位存在
for col in ['用藥風險','可能交互作用']:
    if col not in df.columns:
        df[col] = ''

# 2. 偵測按鈕
if st.button('🔄 AI 偵測所有風險與交互作用'):
    for idx, row in df.iterrows():
        meds = row['藥品名稱']
        df.at[idx, '用藥風險'] = gen_risk(meds)
        df.at[idx, '可能交互作用'] = gen_interactions(meds)
    st.success('已完成 AI 偵測，請至下方審核區提交並同步至 Google Sheets')

# 3. 藥師審核互動區
st.subheader('🩺 藥師審核互動區')
col1, col2 = st.columns([2,3])
with col1:
    selected = st.selectbox('選擇住民進行審核：', df['姓名'])
    review_data = df[df['姓名']==selected].iloc[0]
    st.markdown(f"**基本資料**：{review_data['姓名']}，{review_data['年齡']}歲，疾病：{review_data['疾病']}")
    st.markdown(f"**用藥清單**：{','.join(review_data['藥品名稱'])}")
    st.markdown(f"**AI 判定風險**：{review_data['用藥風險']}  ")
    st.markdown(f"**AI 交互作用**：{review_data['可能交互作用']}  ")
with col2:
    pharmacist = st.text_input('審核藥師姓名')
    risk_level = st.radio('藥師風險判讀', ['高','中','低'], horizontal=True)
    correction = st.text_area('修正意見（若無可留空）')
    if st.button('✅ 提交審核並同步'):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 更新本地 df
        df.loc[df['姓名']==selected, '審核藥師'] = pharmacist
        df.loc[df['姓名']==selected, '藥師風險判讀'] = risk_level
        df.loc[df['姓名']==selected, '修正意見'] = correction
        df.loc[df['姓名']==selected, '審核時間'] = now
        # 同步至 Google Sheets
        append_to_sheet(df[df['姓名']==selected].iloc[0].to_dict())
        st.success('審核記錄已同步至 Google Sheets')

# 4. 側邊欄篩選
with st.sidebar:
    st.header('🔍 篩選條件')
    show_inter = st.checkbox('僅顯示有交互作用的住民')

# 5. 顯示報表
if show_inter:
    disp = df[df['可能交互作用'].str.strip()!='']
else:
    disp = df
report = disp.copy()
report['藥品名稱'] = report['藥品名稱'].apply(lambda x: ','.join(x))

st.subheader('📋 綜合報表（含審核結果）')
st.dataframe(report)

# 6. 匯出 CSV
csv = report.to_csv(index=False).encode('utf-8-sig')
st.download_button('📤 匯出報表 (CSV)', csv, 'smartmeds_full_report.csv', 'text/csv')





