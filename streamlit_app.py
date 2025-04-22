import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("💊 SmartMeds-AI 藥品照護小幫手")

# Google Sheets 認證
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["GSPREAD_CREDENTIALS"], scope)
client = gspread.authorize(creds)

# 讀取 Google Sheets
SHEET_NAME = "SmartMeds_DB"
worksheet = client.open(SHEET_NAME).sheet1

# 轉換為 pandas dataframe
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 顯示資料
st.subheader("📋 最新照護用藥資料")
st.dataframe(df)

# 簡單搜尋功能
query = st.text_input("🔍 搜尋藥品名稱")
if query:
    filtered = df[df["藥品名稱"].str.contains(query, case=False, na=False)]
    st.dataframe(filtered)
import openai
import streamlit as st

openai.api_key = st.secrets["OPENAI"]["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"]

def get_drug_advice(drug_name, age=None, condition=None):
    prompt = f"""
你是一位藥師。請提供藥品「{drug_name}」的基本資訊、常見用途、副作用，並針對年齡 {age} 歲、有「{condition}」病史的病人提供注意事項與劑量建議。
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response["choices"][0]["message"]["content"]

# Streamlit 互動
st.title("用藥建議小幫手")
drug = st.text_input("請輸入藥品名稱")
age = st.number_input("年齡", min_value=1, step=1)
condition = st.text_input("既往病史 / 疾病")

if st.button("查詢建議") and drug:
    result = get_drug_advice(drug, age, condition)
    st.markdown(result)

