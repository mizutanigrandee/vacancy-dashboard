# vacancy_app.py

import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import calendar

# --- 1. データ取得ロジック ---
def fetch_vacancy_count(checkin_date: str) -> int:
    url = (
        "https://travel.rakuten.co.jp/vacancy/"
        "?l-id=vacancy_test_c_map_osaka"
        "#regular/normal/2/9/osaka/"
        f"?checkinDate={checkin_date}"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # 実際のセレクタ要確認
    items = soup.select(".hotelList_item .vacancy-available")
    return len(items)

@st.cache_data(ttl=3600)
def get_count(date: datetime.date) -> int:
    """1時間キャッシュ + 3回リトライ"""
    last_err = None
    for _ in range(3):
        try:
            return fetch_vacancy_count(date.strftime("%Y-%m-%d"))
        except Exception as e:
            last_err = e
    st.error(f"取得に失敗しました: {last_err}")
    return 0

# --- 2. 月ごとの DataFrame を作成する関数 ---
def make_month_df(year: int, month: int) -> pd.DataFrame:
    start = datetime.date(year, month, 1)
    end = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")
    data = {"date": [], "vacancy_count": []}
    for d in dates:
        data["date"].append(d)
        data["vacancy_count"].append(get_count(d))
    df = pd.DataFrame(data).set_index("date")
    return df

# --- 3. HTMLテーブルでカレンダーを描画 ---
def draw_month_html(df: pd.DataFrame, year: int, month: int):
    st.subheader(f"{year}年{month}月")
    # 目標進捗バー
    total = int(df["vacancy_count"].sum())
    target = 20 * len(df)
    progress = min(1.0, total / target) if target > 0 else 0
    st.caption("目標進捗率")
    st.progress(progress)

    # カレンダー構造
    cal = calendar.monthcalendar(year, month)  # 各週ごとに日付リスト（0は空セル）
    max_val = df["vacancy_count"].max() or 1

    html = "<table style='border-collapse: collapse; width: 100%;'>"
    # 曜日ヘッダー
    weekdays = ['日','月','火','水','木','金','土']
    html += "<tr>"
    for wd in weekdays:
        html += f"<th style='border:1px solid #ddd; padding:8px; background:#f0f0f0;'>{wd}</th>"
    html += "</tr>"

    # 日付セル
    for week in cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td style='border:1px solid #ddd; padding:8px;'></td>"
            else:
                val = int(df.loc[pd.Timestamp(year, month, day), 'vacancy_count'])
                intensity = min(255, int(255 * val / max_val))
                color = f"rgb(255, {255-intensity}, {255-intensity})"
                html += (
                    "<td style='border:1px solid #ddd; padding:8px; vertical-align:top;"
                    f"background:{color};'>"
                    f"<strong>{day}</strong><br>"
                    f"<small>{val}件</small>"
                    "</td>"
                )
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

# --- 4. サイドバー設定 ---
st.sidebar.title("カレンダー月選択")
col1_year = st.sidebar.number_input("左カレンダー 年", min_value=2020, value=datetime.date.today().year, step=1)
col1_month = st.sidebar.number_input("左カレンダー 月", min_value=1, max_value=12, value=datetime.date.today().month, step=1)
left_date = datetime.date(col1_year, col1_month, 1)
right_date = left_date + relativedelta(months=1)
col2_year, col2_month = right_date.year, right_date.month

# --- 5. メイン画面 ---
st.title("大阪・なんば〜長居エリア 空室カレンダー (2か月ビュー)")

df1 = make_month_df(col1_year, col1_month)
df2 = make_month_df(col2_year, col2_month)

col1, col2 = st.columns(2)
with col1:
    draw_month_html(df1, col1_year, col1_month)
with col2:
    draw_month_html(df2, col2_year, col2_month)
