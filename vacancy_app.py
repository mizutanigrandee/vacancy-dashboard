# vacancy_app.py

import streamlit as st
import datetime
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta
from requests.exceptions import HTTPError, RequestException

# ── 1. Streamlit Secrets から Application ID を読み込む ──
APP_ID = st.secrets["RAKUTEN_APP_ID"]

def fetch_count(date: datetime.date) -> int:
    """
    VacantHotelSearch API (1泊分) を呼び出し、
    指定日 (date) の空室ありホテル数を返します。
    """
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    params = {
        "applicationId": APP_ID,
        "format": "json",
        "largeClassCode": "japan",   # 国内
        "middleClassCode": "osaka",  # 大阪市内
        "smallClassCode":  "osaka",  # 小エリア（お好みで変更可）
        "checkinDate":  date.strftime("%Y-%m-%d"),
        "checkoutDate": (date + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum": 1,
        "hits":     30,  # 1ページあたり最大30件
        "pageNo":   1,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return int(data.get("count", len(data.get("items", []))))
    except (HTTPError, RequestException, ValueError):
        # エラー時は 0 件とみなします
        return 0

@st.cache_data(ttl=3600)
def make_month_df(year: int, month: int) -> pd.DataFrame:
    """
    指定の年月の全日を fetch_count で取得し、
    DataFrame(date→vacancy_count) にまとめる
    """
    start = datetime.date(year, month, 1)
    end   = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")

    records = {"date": [], "vacancy_count": []}
    for d in dates:
        records["date"].append(d)
        records["vacancy_count"].append(fetch_count(d.date()))

    df = pd.DataFrame(records).set_index("date")
    df["weekday"] = df.index.weekday  # 0=月曜…6=日曜
    df["week"]    = (df.index.day - 1 + df["weekday"]) // 7
    return df

def draw_month(df: pd.DataFrame, year: int, month: int):
    """DataFrame の vacancy_count をカレンダー形式で描画"""
    st.subheader(f"{year}年{month}月")

    # 曜日ヘッダ
    cols = st.columns(7)
    for i, wd in enumerate(["日","月","火","水","木","金","土"]):
        cols[i].markdown(f"**{wd}**")

    # 各週のセルを描画
    weeks = int(df["week"].max()) + 1
    for w in range(weeks):
        cols = st.columns(7)
        wk   = df[df["week"] == w]
        for dow in range(7):
            with cols[dow]:
                cell = wk[wk["weekday"] == dow]
                if cell.empty:
                    # 月外の日付
                    st.markdown(
                        "<div style='background:#f5f5f5;"
                        "border:1px solid #eee; height:80px;'></div>",
                        unsafe_allow_html=True
                    )
                else:
                    day = cell.index.day[0]
                    val = int(cell["vacancy_count"][0])
                    # f-string で変数を埋め込むこと！
                    st.markdown(
                        f"<div style='border:1px solid #ccc;"
                        " height:80px; padding:6px;'>"
                        f"<div style='text-align:right; font-size:14px;'>{day}</div>"
                        f"<div style='text-align:center; font-size:20px;'>{val}件</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )

# ── Streamlit レイアウト ──
st.sidebar.title("カレンダー月選択")
year  = st.sidebar.number_input("左カレンダー 年", 2020, 2030, datetime.date.today().year)
month = st.sidebar.number_input("左カレンダー 月",  1,   12,   datetime.date.today().month)

left  = datetime.date(year, month, 1)
right = left + relativedelta(months=1)

df1 = make_month_df(left.year,  left.month)
df2 = make_month_df(right.year, right.month)

st.title("なんば・心斎橋〜長居エリア 空室カレンダー (2か月ビュー)")
col1, col2 = st.columns(2)
with col1:
    draw_month(df1, left.year,  left.month)
with col2:
    draw_month(df2, right.year, right.month)
