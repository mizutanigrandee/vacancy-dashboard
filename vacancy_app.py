# vacancy_app.py

import streamlit as st
import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

BASE_URL = "https://travel.rakuten.co.jp/vacancy/"

@st.cache_data(ttl=3600)
def fetch_monthly_counts():
    """
    なんば〜長居エリアの月間在庫データをまとめて取得し、
    {day: count} の dict を返します。
    """
    # ここでは「今月＋来月」の両方を一度に取ってくる想定ですが、
    # まずは左カレンダー月だけ取得するシンプル版です。
    # 必要に応じて後でループで複数月対応してください。
    today = datetime.date.today()
    year, month = today.year, today.month

    # 取得したい2か月分をループ
    all_counts = {}
    for offset in [0, 1]:
        ym = (today + relativedelta(months=offset))
        y, m = ym.year, ym.month
        # 1日から月末まで回す
        start = datetime.date(y, m, 1)
        end = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
        for d in pd.date_range(start, end, freq="D"):
            day_str = d.strftime("%Y-%m-%d")
            # ページ取得
            resp = requests.get(
                BASE_URL,
                params={"l-id": "vacancy_test_c_map_osaka", "checkinDate": day_str},
                timeout=10
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # テーブルを１つだけ取る（ページ内で最初に出てくるテーブル）
            table = soup.find("table")
            if not table:
                all_counts[d.day] = 0
                continue
            tbody = table.find("tbody")
            if not tbody:
                all_counts[d.day] = 0
                continue

            # 行ヘッダに目的エリア名を含む行を探す
            count = 0
            for tr in tbody.find_all("tr"):
                th = tr.find("th")
                if th and "なんば・心斎橋・天王寺・阿倍野・長居" in th.get_text():
                    tds = tr.find_all("td")
                    # セルのテキストが数字になっているものを数える
                    for td in tds:
                        txt = td.get_text(strip=True)
                        if txt.isdigit():
                            count += 1
                    break
            all_counts[d.day] = count

    return all_counts

def make_month_df(year: int, month: int, counts: dict) -> pd.DataFrame:
    """
    year,month の全日を DataFrame にし、counts dict から在庫数を埋める
    """
    start = datetime.date(year, month, 1)
    end   = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")
    data = {"date": [], "vacancy": []}
    for d in dates:
        data["date"].append(d)
        data["vacancy"].append(counts.get(d.day, 0))
    df = pd.DataFrame(data).set_index("date")
    df["weekday"] = df.index.weekday  # 0=月…6=日
    df["week"]    = (df.index.day - 1 + df["weekday"]) // 7
    return df

def draw_month(df: pd.DataFrame, year: int, month: int):
    st.subheader(f"{year}年{month}月")
    # 曜日ヘッダー
    cols = st.columns(7)
    for i, wd in enumerate(["日","月","火","水","木","金","土"]):
        cols[i].markdown(f"**{wd}**")
    # 各週を描画
    weeks = int(df["week"].max()) + 1
    for w in range(weeks):
        cols = st.columns(7)
        wk   = df[df["week"] == w]
        for dow in range(7):
            with cols[dow]:
                cell = wk[wk["weekday"] == dow]
                if cell.empty:
                    st.markdown(
                        "<div style='background:#f5f5f5; border:1px solid #eee; height:80px;'></div>",
                        unsafe_allow_html=True
                    )
                else:
                    day = cell.index.day[0]
                    val = int(cell["vacancy"][0])
                    st.markdown(
                        f"<div style='border:1px solid #ccc; height:80px; padding:6px;'>"
                        f"<div style='text-align:right; font-size:14px;'>{day}</div>"
                        f"<div style='text-align:center; font-size:20px;'>{val}件</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )

# ── メイン ──
st.sidebar.title("カレンダー月選択")
year  = st.sidebar.number_input("左カレンダー 年", 2020, 2030, datetime.date.today().year)
month = st.sidebar.number_input("左カレンダー 月",  1,   12,   datetime.date.today().month)

# 1. まずは2か月合計でスクレイピングしてキャッシュ
counts = fetch_monthly_counts()

# 2. 左右の DataFrame を作成
left  = datetime.date(year, month, 1)
right = left + relativedelta(months=1)
df1 = make_month_df(left.year,  left.month,  counts)
df2 = make_month_df(right.year, right.month, counts)

# 3. 描画
st.title("なんば・心斎橋〜長居エリア 空室カレンダー (2か月ビュー)")
col1, col2 = st.columns(2)
with col1:
    draw_month(df1, left.year,  left.month)
with col2:
    draw_month(df2, right.year, right.month)
