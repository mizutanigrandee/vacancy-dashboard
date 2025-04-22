# vacancy_app.py

import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import calendar
\# --- 0. カレンダーの曜日を日曜始まりに設定 ---
calendar.setfirstweekday(calendar.SUNDAY)

# --- 1. データ取得ロジック（ページネーション対応 & 取得時間記録） ---
def fetch_vacancy_count(checkin_date: str) -> (int, datetime.datetime):
    """
    指定日の在庫ありホテル数を、全ページから合計して取得し、
    (count, fetch_time) のタプルで返す。
    """
    base_url = "https://travel.rakuten.co.jp/vacancy/"
    params = {
        "l-id": "vacancy_test_c_map_osaka",
        "checkinDate": checkin_date
    }
    session = requests.Session()
    # --- 1.1 初回取得 ---
    resp = session.get(base_url, params=params, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # ページ数を調べる（数字リンクを収集）
    pager_links = soup.select("ul.rp-pagenavi li a")
    pages = [int(a.text) for a in pager_links if a.text.isdigit()]
    max_page = max(pages) if pages else 1

    total_count = 0
    # 各ページを巡回
    for p in range(1, max_page+1):
        if p == 1:
            sp = soup
        else:
            resp = session.get(base_url, params={**params, "page": p}, timeout=10)
            resp.raise_for_status()
            sp = BeautifulSoup(resp.text, "html.parser")
        # 在庫ありアイテムをカウント（要セレクタ確認）
        items = sp.select(".hotelList_item .vacancy-available")
        total_count += len(items)

    fetch_time = datetime.datetime.now()
    return total_count, fetch_time

@st.cache_data(ttl=3600)
def get_vacancy_info(date: datetime.date):
    """
    checkinDate パラメータで全ページを取得し、
    (count, fetch_time) を返すラッパー関数
    """
    return fetch_vacancy_count(date.strftime("%Y-%m-%d"))

# --- 2. 月ごとの DataFrame を作成する関数 ---
def make_month_df(year: int, month: int) -> pd.DataFrame:
    start = datetime.date(year, month, 1)
    end = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")
    data = {"date": [], "vacancy_count": []}
    for d in dates:
        count, _ = get_vacancy_info(d)
        data["date"].append(d)
        data["vacancy_count"].append(count)
    df = pd.DataFrame(data).set_index("date")
    return df

# --- 3. HTMLテーブルでカレンダーを描画 ---
def draw_month_html(df: pd.DataFrame, year: int, month: int):
    st.subheader(f"{year}年{month}月")
    # 取得時間を表示
    today = datetime.date.today()
    _, fetch_time = get_vacancy_info(today)  # 当日取得時刻を取得例
    st.caption(f"最終取得: {fetch_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 目標進捗バー
    total = int(df["vacancy_count"].sum())
    target = 20 * len(df)
    progress = min(1.0, total / target) if target > 0 else 0
    st.caption("目標進捗率")
    st.progress(progress)

    # カレンダー構造（日曜始まり）
    cal = calendar.monthcalendar(year, month)
    max_val = df["vacancy_count"].max() or 1

    html = "<table style='border-collapse: collapse; width: 100%;'>"
    # 曜日ヘッダー
    weekdays = ['日','月','火','水','木','金','土']
    html += "<tr>"
    for wd in weekdays:
        html += f"<th style='border:1px solid #ccc; padding:4px; background:#f5f5f5;'>{wd}</th>"
    html += "</tr>"

    # 日付セル
    for week in cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td style='border:1px solid #ccc; padding:4px; background:#fafafa;'></td>"
            else:
                val = int(df.loc[pd.Timestamp(year, month, day), 'vacancy_count'])
                intensity = min(255, int(255 * val / max_val))
                color = f"rgb(255, {255-intensity}, {255-intensity})"
                html += (
                    "<td style='border:1px solid #ccc; padding:0; position:relative; height:80px; background:" + color + ";'>"
                    # 日付を右上に配置
                    "<div style='position:absolute; top:4px; right:4px; font-size:12px;'>" + str(day) + "</div>"
                    # 残室数を中央下部に配置
                    "<div style='position:absolute; bottom:4px; left:50%; transform:translateX(-50%); font-size:14px;'>" + str(val) + "件</div>"
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
