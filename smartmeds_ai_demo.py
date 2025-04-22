import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 設定 Google Sheets 授權
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["GSPREAD_CREDENTIALS"], scope)
client = gspread.authorize(creds)

# 連接指定 Google Sheet
sheet = client.open("SmartMeds_DB").sheet1

# 讀取資料
data = sheet.get_all_records()
df = pd.DataFrame(data)

# 顯示資料表
st.title("🧠 智藥照護小幫手 SmartMeds-AI")
st.dataframe(df)

# 審核輸入
st.subheader("🩺 藥師審核")
selected = st.selectbox("選擇住民", df["姓名"])
row = df[df["姓名"] == selected].iloc[0]
st.write(f"年齡：{row['年齡']} 歲 | 疾病：{row['疾病']} | 用藥：{row['用藥']}")

risk_level = st.radio("風險等級", ["高", "中", "低"], horizontal=True)
agree = st.radio("是否同意AI判定", ["是", "否"], horizontal=True)
comment = ""
if agree == "否":
    comment = st.text_input("修正建議")

if st.button("✅ 提交審核"):
    sheet.append_row([row["姓名"], row["年齡"], row["疾病"], row["用藥"], row["用藥風險"], risk_level, agree, comment])
    st.success("審核紀錄已提交")