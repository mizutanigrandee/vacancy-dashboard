# vacancy_app.py

import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd

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
    # ※ 実際のクラス名を要確認
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
    # 月初～月末の日付リスト
    start = datetime.date(year, month, 1)
    end = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")
    data = {"date": [], "vacancy_count": []}
    for d in dates:
        data["date"].append(d)
        data["vacancy_count"].append(get_count(d))
    df = pd.DataFrame(data).set_index("date")
    df["weekday"] = df.index.weekday  # 0=Mon,6=Sun
    df["week"]    = (df.index.day - 1 + df["weekday"]) // 7
    return df

# --- 3. カレンダーを描画する関数 ---
def draw_month(df: pd.DataFrame, year: int, month: int):
    # ヘッダー：年月と進捗バー
    month_str = f"{year}年{month}月"
    st.subheader(month_str)
    total = int(df["vacancy_count"].sum())
    # ここで「目標」を定義（例：1日あたり20件×日数）
    target = 20 * len(df)
    progress = min(1.0, total / target) if target > 0 else 0.0
    st.caption("目標進捗率")
    st.progress(progress)

    # カレンダー本体
    weeks = int(df["week"].max()) + 1
    for w in range(weeks):
        cols = st.columns(7)
        for dow in range(7):
            with cols[dow]:
                cell = df[(df["week"] == w) & (df["weekday"] == dow)]
                if not cell.empty:
                    day = cell.index.day[0]
                    val = int(cell["vacancy_count"][0])
                    # 色の濃淡（最大値を基準）
                    max_val = df["vacancy_count"].max() or 1
                    intensity = min(255, int(255 * val / max_val))
                    color = f"rgb(255, {255-intensity}, {255-intensity})"
                    st.markdown(
                        f"<div style='"
                        f"background:{color}; padding:8px; border-radius:4px;"
                        f"text-align:center; min-height:60px;'>"
                        f"<strong>{day}</strong><br>"
                        f"<span style='font-size:18px;'>{val}件</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.write("")

# --- 4. サイドバーで表示月を選択 ---
st.sidebar.title("カレンダー月選択")
col1_year = st.sidebar.number_input("左カレンダー 年", min_value=2020, value=datetime.date.today().year, step=1)
col1_month = st.sidebar.number_input("左カレンダー 月", min_value=1, max_value=12, value=datetime.date.today().month, step=1)

# 右カレンダーは左の翌月に固定
left_date = datetime.date(col1_year, col1_month, 1)
right_date = left_date + relativedelta(months=1)
col2_year, col2_month = right_date.year, right_date.month

# --- 5. メイン画面 ---
st.title("大阪・なんば〜長居エリア 空室カレンダー (2か月ビュー)")

df1 = make_month_df(col1_year, col1_month)
df2 = make_month_df(col2_year, col2_month)

col1, col2 = st.columns(2)
with col1:
    draw_month(df1, col1_year, col1_month)
with col2:
    draw_month(df2, col2_year, col2_month)
