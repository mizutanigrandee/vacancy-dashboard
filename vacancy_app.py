# vacancy_app.py

import streamlit as st
import datetime
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta

# あなたの Application ID に置き換えてください
APPLICATION_ID = "YOUR_APP_ID"

def fetch_vacant_count_api(date: datetime.date) -> int:
    """楽天トラベル VacantHotelSearch API を叩いて在庫数を返す"""
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    params = {
        "applicationId": APPLICATION_ID,
        "format": "json",
        "largeClassCode": "japan",
        "middleClassCode": "osaka",
        "smallClassCode": "osaka",  # 大阪市内
        # なんば・心斎橋周辺なら緯度経度＋半径で絞り込む方法もあります
        "checkinDate": date.strftime("%Y-%m-%d"),
        "checkoutDate": (date + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum": 1,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    # 返却 JSON のアイテム数が「空室ありホテル数」
    return len(data.get("items", []))

@st.cache_data(ttl=3600)
def make_month_df(year: int, month: int) -> pd.DataFrame:
    """指定の年月の全日在庫を API から取得し、DataFrame にまとめる"""
    start = datetime.date(year, month, 1)
    end = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")

    data = {"date": [], "vacancy_count": []}
    for d in dates:
        data["date"].append(d)
        data["vacancy_count"].append(fetch_vacant_count_api(d))

    df = pd.DataFrame(data).set_index("date")
    df["weekday"] = df.index.weekday
    df["week"] = (df.index.day - 1 + df["weekday"]) // 7
    return df

def draw_month(df: pd.DataFrame, year: int, month: int):
    st.subheader(f"{year}年{month}月")
    # ↓ 目標進捗は不要とのことなので削除 or コメントアウト
    # total = int(df["vacancy_count"].sum())
    # target = 20 * len(df)
    # st.caption("目標進捗率")
    # st.progress(min(1.0, total/target) if target>0 else 0.0)

    # 曜日ヘッダー
    cols = st.columns(7)
    for i, wd in enumerate(["日","月","火","水","木","金","土"]):
        cols[i].markdown(f"**{wd}**")

    # セル描画
    weeks = int(df["week"].max())+1
    for w in range(weeks):
        cols = st.columns(7)
        wk = df[df["week"]==w]
        for dow in range(7):
            with cols[dow]:
                cell = wk[wk["weekday"]==dow]
                if cell.empty:
                    st.write("") 
                else:
                    day = cell.index.day[0]
                    val = int(cell["vacancy_count"][0])
                    st.markdown(
                        f"<div style='"
                        f"padding:8px; border:1px solid #ddd; min-height:60px;'>"
                        f"<div style='text-align:right; font-size:14px;'>{day}</div>"
                        f"<div style='text-align:center; font-size:20px;'>{val}件</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

# ── Streamlit UI ──
st.sidebar.title("カレンダー月選択")
year = st.sidebar.number_input("左カレンダー 年", 2020, 2030, datetime.date.today().year)
month = st.sidebar.number_input("左カレンダー 月", 1, 12, datetime.date.today().month)

left = datetime.date(year, month, 1)
right = left + relativedelta(months=1)

df1 = make_month_df(left.year, left.month)
df2 = make_month_df(right.year, right.month)

st.title("大阪・なんば〜長居エリア 空室カレンダー (2か月ビュー)")
c1, c2 = st.columns(2)
with c1:
    draw_month(df1, left.year, left.month)
with c2:
    draw_month(df2, right.year, right.month)
