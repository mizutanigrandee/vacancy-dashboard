# vacancy_app.py

import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import calendar
import re

# --- 0. カレンダーを日曜始まりに設定 ---
calendar.setfirstweekday(calendar.SUNDAY)

# --- 1. データ取得ロジック（HTMLスクレイピング版） ---
def fetch_vacancy_count(checkin_date: str):
    """
    画面から「なんば・心斎橋・天王寺・阿倍野・長居」エリアの
    指定日の空室ホテル数を取得し、
    (count, fetch_time) を返す
    """
    url = "https://travel.rakuten.co.jp/vacancy/"
    params = {"l-id": "vacancy_test_c_map_osaka", "checkinDate": checkin_date}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 1-1) 最終取得時刻をパース
    fetch_time = None
    info = soup.select_one("div.rp-update")  # classは要確認
    if info:
        txt = info.get_text(strip=True)
        m = re.search(r"(\d{1,2}月\d{1,2}日\d{2}:\d{2})", txt)
        if m:
            tm = datetime.datetime.strptime(m.group(1), "%m月%d日%H:%M")
            fetch_time = tm.replace(year=datetime.datetime.now().year)

    # 1-2) 対象行を探して、先頭<td>の数値を取得
    count = 0
    table = soup.find("table")  # ページ内最初のテーブル
    if table:
        for tr in table.find_all("tr"):
            th = tr.find("th")
            if th and "なんば・心斎橋・天王寺・阿倍野・長居" in th.get_text():
                tds = tr.find_all("td")
                if tds:
                    # 一番左の<td>がチェックイン日の在庫数
                    val = tds[0].get_text(strip=True)
                    # 数字だけ抽出
                    digits = re.search(r"(\d+)", val)
                    count = int(digits.group(1)) if digits else 0
                break

    return count, fetch_time

@st.cache_data(ttl=3600)
def get_vacancy_info(date: datetime.date):
    """日付を渡して (count, fetch_time) を返す"""
    return fetch_vacancy_count(date.strftime("%Y-%m-%d"))

# --- 2. 月ごとのデータフレーム作成 ---
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

# --- 3. カレンダー描画(HTMLテーブル) ---
def draw_month_html(df: pd.DataFrame, year: int, month: int):
    st.subheader(f"{year}年{month}月")
    # 取得時刻表示
    _, fetch_time = get_vacancy_info(datetime.date.today())
    if fetch_time:
        st.caption(f"最終取得: {fetch_time.strftime('%m/%d %H:%M')} 現在")

    # 進捗バー
    total = int(df["vacancy_count"].sum())
    target = 20 * len(df)
    st.caption("目標進捗率")
    st.progress(min(1.0, total / target) if target > 0 else 0)

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

    # 各週ごとの行
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
                    "<div style='position:absolute; top:4px; right:4px; font-size:12px;'>" + str(day) + "</div>"
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
