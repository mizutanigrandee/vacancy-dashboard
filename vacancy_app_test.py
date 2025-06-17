import streamlit as st
import json
import pandas as pd

HISTORICAL_FILE = "historical_data.json"

st.title("空室＆平均価格カレンダー グラフテスト用ページ")

selected_date = st.date_input("グラフを見たい日付を選択")

# 履歴データの読み込み
with open(HISTORICAL_FILE, "r", encoding="utf-8") as f:
    historical_data = json.load(f)

date_key = selected_date.isoformat()
if date_key in historical_data:
    df = pd.DataFrame([
        {"取得日": d, "在庫数": v["vacancy"], "平均単価": v["avg_price"]}
        for d, v in historical_data[date_key].items()
    ])
    df["取得日"] = pd.to_datetime(df["取得日"])
    st.line_chart(df.set_index("取得日")[["在庫数", "平均単価"]])
else:
    st.info("まだ履歴データがありません。")
