# vacancy_app.py

import streamlit as st
import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

URL = "https://travel.rakuten.co.jp/vacancy/?l-id=vacancy_test_c_map_osaka"

@st.cache_data(ttl=3600)
def fetch_namba_counts():
    """
    公式ページの一番上にある「大阪府 宿泊可能な施設数」テーブルを
    スクレイピングして、日付→在庫件数 を dict で返す。
    """
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 1) 一番最初に出てくる table を取得
    table = soup.find("table")
    if table is None:
        st.error("在庫テーブルが見つかりませんでした")
        return {}

    # 2) thead から日付情報をパース
    header_ths = table.find("thead").find_all("th")[1:]  # 先頭の「エリア」列を除外
    dates = []
    for th in header_ths:
        txt = th.get_text(strip=True)
        # たとえば "4/22(火)" なら日付部分だけ取り出す
        day = int(txt.split("/")[1].split("(")[0])
        dates.append(day)

    # 3) 対象行（「なんば・心斎橋…」）を tbody から探す
    counts = {}
    for tr in table.find("tbody").find_all("tr"):
        th = tr.find("th")
        if not th:
            continue
        if "なんば・心斎橋・天王寺・阿倍野・長居" in th.get_text():
            tds = tr.find_all("td")
            for day, td in zip(dates, tds):
                txt = td.get_text(strip=True)
                # 数値以外（－や空欄）は 0 とみなす
                counts[day] = int(txt) if txt.isdigit() else 0
            break

    return counts

def make_month_df(year: int, month: int, counts: dict) -> pd.DataFrame:
    """
    指定年月の全日を生成し、counts dict で在庫数を埋めた DataFrame を返す
    """
    start = datetime.date(year, month, 1)
    end   = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")

    data = {"date": [], "vacancy": []}
    for d in dates:
        data["date"].append(d)
        data["vacancy"].append(counts.get(d.day, 0))

    df = pd.DataFrame(data).set_index("date")
    df["weekday"] = df.index.weekday
    df["week"]    = (df.index.day - 1 + df["weekday"]) // 7
    return df

def draw_month(df: pd.DataFrame, year: int, month: int):
    st.subheader(f"{year}年{month}月")
    cols = st.columns(7)
    for i, wd in enumerate(["日","月","火","水","木","金","土"]):
        cols[i].markdown(f"**{wd}**")

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

# ── Streamlit レイアウト ──
st.sidebar.title("カレンダー月選択")
year  = st.sidebar.number_input("左カレンダー 年", 2020, 2030, datetime.date.today().year)
month = st.sidebar.number_input("左カレンダー 月",  1,   12,   datetime.date.today().month)

# キャッシュ付きで在庫を一度だけ取得
counts = fetch_namba_counts()

left  = datetime.date(year, month, 1)
right = left + relativedelta(months=1)

df1 = make_month_df(left.year,  left.month,  counts)
df2 = make_month_df(right.year, right.month, counts)

st.title("なんば・心斎橋〜長居エリア 空室カレンダー (2か月ビュー)")
col1, col2 = st.columns(2)
with col1:
    draw_month(df1, left.year,  left.month)
with col2:
    draw_month(df2, right.year, right.month)
