# vacancy_app.py

import streamlit as st
import datetime
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

# ── 1. いちどだけ HTML を取得してスクレイピング ──
@st.cache_data(ttl=3600)
def fetch_monthly_vacancies():
    """
    なんば〜長居エリアの月間在庫をページからスクレイピングし、
    {日付(day): 在庫件数} の dict を返します。
    """
    url = "https://travel.rakuten.co.jp/vacancy/"
    # Osaka map のパラメータ
    params = {"l-id": "vacancy_test_c_map_osaka"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 1) 適切なテーブルを探す（thead の th に「M/D」が含まれるもの）
    table = None
    for tbl in soup.find_all("table"):
        thead = tbl.find("thead")
        if not thead:
            continue
        headers = [th.get_text(strip=True) for th in thead.find_all("th")[1:]]
        # ヘッダに「4/」や「5/」など日付があるかで判定
        if any(re.match(r"\d{1,2}/\d{1,2}", h) for h in headers):
            table = tbl
            break
    if table is None:
        st.error("在庫テーブルが見つかりませんでした")
        return {}

    # 2) ヘッダの日付部分を {列インデックス: day} にマッピング
    idx_to_day = {}
    for idx, th in enumerate(table.find("thead").find_all("th")[1:]):
        txt = th.get_text(strip=True)
        m = re.match(r"(\d{1,2})/\d{1,2}", txt)
        if m:
            idx_to_day[idx] = int(m.group(1))

    # 3) 対象行を探す
    vacancies = {}
    for tr in table.find("tbody").find_all("tr"):
        th = tr.find("th")
        if th and "なんば・心斎橋・天王寺・阿倍野・長居" in th.get_text():
            tds = tr.find_all("td")
            for idx, td in enumerate(tds):
                day = idx_to_day.get(idx)
                if day:
                    text = td.get_text(strip=True)
                    # 数値以外はゼロとして扱う
                    vacancies[day] = int(text) if text.isdigit() else 0
            break

    return vacancies

# ── 2. 指定月の DataFrame を作成 ──
def make_month_df(year: int, month: int) -> pd.DataFrame:
    # その月の全日を生成
    start = datetime.date(year, month, 1)
    end = (start + datetime.timedelta(days=40)).replace(day=1) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")
    # 一度スクレイピングして全在庫を取得
    monthly = fetch_monthly_vacancies()

    data = {"date": [], "vacancy_count": []}
    for d in dates:
        data["date"].append(d)
        # スクレイピング結果に日付(day) があれば、なければ 0
        data["vacancy_count"].append(monthly.get(d.day, 0))

    df = pd.DataFrame(data).set_index("date")
    df["weekday"] = df.index.weekday  # 0=Mon,6=Sun
    df["week"]    = (df.index.day - 1 + df["weekday"]) // 7
    return df

# ── 3. カレンダー描画関数 ──
def draw_month(df: pd.DataFrame, year: int, month: int):
    st.subheader(f"{year}年{month}月")
    # 目標進捗バー（例：1日20件×日数 を目標値に）
    total = int(df["vacancy_count"].sum())
    target = 20 * len(df)
    progress = min(1.0, total / target) if target > 0 else 0.0
    st.caption("目標進捗率")
    st.progress(progress)

    # 曜日ヘッダ
    cols = st.columns(7)
    for i, wd in enumerate(["日", "月", "火", "水", "木", "金", "土"]):
        cols[i].markdown(f"**{wd}**")

    # 各週を描画
    weeks = int(df["week"].max()) + 1
    for w in range(weeks):
        cols = st.columns(7)
        wk = df[df["week"] == w]
        for dow in range(7):
            with cols[dow]:
                cell = wk[wk["weekday"] == dow]
                if not cell.empty:
                    day = cell.index.day[0]
                    val = int(cell["vacancy_count"][0])
                    max_val = df["vacancy_count"].max() or 1
                    intensity = min(255, int(255 * val / max_val))
                    bg = f"rgb(255, {255-intensity}, {255-intensity})"
                    # 日付は右上、在庫数は中央に
                    st.markdown(
                        f"<div style='position:relative;"
                        f"background:{bg}; border:1px solid #ccc; min-height:80px;'>"
                        f"<div style='position:absolute; top:4px; right:6px; font-size:14px;'>{day}</div>"
                        f"<div style='"
                        f"display:flex; align-items:center; justify-content:center;"
                        f"height:100%; font-size:20px;'>{val}件</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                else:
                    # 月外の日付セル
                    st.markdown(
                        "<div style='background:#f5f5f5; border:1px solid #eee; min-height:80px;'></div>",
                        unsafe_allow_html=True
                    )

# ── 4. サイドバーで年月を選択 & 2か月表示 ──
st.sidebar.title("カレンダー月選択")
year = st.sidebar.number_input("左カレンダー 年", min_value=2020, max_value=2030,
                               value=datetime.date.today().year, step=1)
month = st.sidebar.number_input("左カレンダー 月", min_value=1, max_value=12,
                                value=datetime.date.today().month, step=1)

left_date = datetime.date(year, month, 1)
right_date = left_date + datetime.timedelta(days=40)  # 翌月を自動計算
df1 = make_month_df(left_date.year, left_date.month)
df2 = make_month_df(right_date.year, right_date.month)

st.title("大阪・なんば〜長居エリア 空室カレンダー (2か月ビュー)")
col1, col2 = st.columns(2)
with col1:
    draw_month(df1, left_date.year, left_date.month)
with col2:
    draw_month(df2, right_date.year, right_date.month)
