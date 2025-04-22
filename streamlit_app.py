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


