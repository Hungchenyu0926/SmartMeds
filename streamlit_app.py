import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import datetime

# --- 1. 連線 Google Sheets ---
@st.cache_resource
def connect_to_sheet():
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(st.secrets["google_sheets"]["credentials"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(st.secrets["google_sheets"]["sheet_name"]).sheet1
    return sheet

# --- 2. 其餘程式保持不變，只是在提交時呼叫 append_review_to_sheet ---
def append_review_to_sheet(sheet, review_data: dict):
    row = [
        review_data['姓名'],
        review_data['年齡'],
        review_data['疾病'],
        '、'.join(review_data['用藥']),
        review_data['用藥風險'],
        review_data['藥師名稱'],
        review_data['藥師風險判讀'],
        review_data['是否同意AI'],
        review_data['修正意見'],
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ]
    sheet.append_row(row)

# … 介面與互動程式碼 …
if st.button("✅ 提交審核紀錄"):
    # … 更新本地 df …
    review_dict = df[df['姓名'] == selected_row].iloc[0].to_dict()
    review_dict['藥師名稱'] = pharmacist_name
    sheet = connect_to_sheet()
    append_review_to_sheet(sheet, review_dict)
    st.success("審核結果已同步至 Google Sheets")



