import streamlit as st
import datetime
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta
from requests.exceptions import HTTPError, RequestException

# ── 1. Secrets からAPIキーを取得 ──
APP_ID = st.secrets["RAKUTEN_APP_ID"]

def fetch_count(date: datetime.date) -> int:
    """
    VacantHotelSearch API を code=1/2/9 で呼び出し、
    1泊分の「空室ありホテル数」を返します。
    """
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    params = {
        "applicationId":    APP_ID,
        "format":           "json",
        "largeClassCode":   "1",    # 国内
        "middleClassCode":  "2",    # 大阪市内
        "smallClassCode":   "9",    # なんば〜長居
        "checkinDate":      date.strftime("%Y-%m-%d"),
        "checkoutDate":     (date + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum":         1,
        "hits":             30,
        "pageNo":           1,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return int(data.get("count", len(data.get("items", []))))
    except (HTTPError, RequestException, ValueError):
        return 0

@st.cache_data(ttl=3600)
def make_month_df(year: int, month: int) -> pd.DataFrame:
    """年月の全日在庫を取得して DataFrame にまとめる"""
    start = datetime.date(year, month, 1)
    end   = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end)

    rec = {"date": [], "vacancy_count": []}
    for d in dates:
        rec["date"].append(d)
        rec["vacancy_count"].append(fetch_count(d.date()))

    df = pd.DataFrame(rec).set_index("date")
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
                        "<div style='background:#f5f5f5;"
                        "border:1px solid #eee;height:80px;'></div>",
                        unsafe_allow_html=True
                    )
                else:
                    day = cell.index.day[0]
                    val = int(cell["vacancy_count"][0])
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
c1, c2 = st.columns(2)
with c1:
    draw_month(df1, left.year,  left.month)
with c2:
    draw_month(df2, right.year, right.month)
