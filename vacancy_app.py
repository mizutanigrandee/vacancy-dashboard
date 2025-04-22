# vacancy_app.py

import streamlit as st
import datetime
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta
from requests.exceptions import HTTPError, RequestException

# ── 1. Secrets から楽天APIのApplication IDを読み込む ──
APP_ID = st.secrets.get("RAKUTEN_APP_ID", "")

def fetch_vacant_count_api(checkin: datetime.date) -> int:
    """
    VacantHotelSearch API を緯度・経度＋半径で呼び出し、
    checkin→翌日チェックアウト分の空室ありホテル数を返却します。
    APP_ID未設定またはエラー時は0を返し、画面に警告／エラーを表示。
    """
    if not APP_ID:
        st.warning("APIキー未設定のため、在庫数を0件で表示します。")
        return 0

    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    params = {
        "applicationId": APP_ID,
        "format": "json",
        "datumType": 1,
        "latitude": 34.667,
        "longitude": 135.502,
        "searchRadius": 2,
        "checkinDate": checkin.strftime("%Y-%m-%d"),
        "checkoutDate": (checkin + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum": 1,
        # hits must be <= 30
        "hits": 30,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        # count フィールドを返す
        return data.get("count", len(data.get("items", [])))
    except HTTPError as e:
        st.error(f"API HTTPError: {e}")
    except RequestException as e:
        st.error(f"API RequestException: {e}")
    except ValueError:
        st.error("API レスポンスの JSON 解析に失敗しました。")
    return 0

@st.cache_data(ttl=3600)
def make_month_df(year: int, month: int) -> pd.DataFrame:
    """
    指定年月の全日在庫を API から取得し、DataFrame にまとめる
    """
    start = datetime.date(year, month, 1)
    end = (start + relativedelta(months=1)) - datetime.timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")

    data = {"date": [], "vacancy": []}
    for d in dates:
        data["date"].append(d)
        data["vacancy"].append(fetch_vacant_count_api(d))

    df = pd.DataFrame(data).set_index("date")
    df["weekday"] = df.index.weekday
    df["week"]    = (df.index.day - 1 + df["weekday"]) // 7
    return df

def draw_month(df: pd.DataFrame, year: int, month: int):
    """
    DataFrame の在庫数をカレンダー形式で描画する
    """
    st.subheader(f"{year}年{month}月")

    # 曜日ヘッダー
    cols = st.columns(7)
    for i, wd in enumerate(["日","月","火","水","木","金","土"]):
        cols[i].markdown(f"**{wd}**")

    # 各週を描画
    weeks = int(df["week"].max()) + 1
    for w in range(weeks):
        cols = st.columns(7)
        wk = df[df["week"] == w]
        for dow in range(7):
            with cols[dow]:
                cell = wk[wk["weekday"] == dow]
                if cell.empty:
                    # 月の前後で空のセル
                    st.markdown(
                        "<div style='background:#f5f5f5; border:1px solid #eee; height:80px;'></div>",
                        unsafe_allow_html=True
                    )
                else:
                    day = cell.index.day[0]
                    val = int(cell["vacancy"][0])
                    st.markdown(
                        f"<div style='border:1px solid #ddd; height:80px; padding:4px;'>"
                        f"<div style='text-align:right; font-size:14px;'>{day}</div>"
                        f"<div style='text-align:center; font-size:20px;'>{val}件</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

# ── Streamlit レイアウト設定 ──
st.sidebar.title("カレンダー月選択")
year = st.sidebar.number_input(
    "左カレンダー 年", min_value=2020, max_value=2030,
    value=datetime.date.today().year, step=1
)
month = st.sidebar.number_input(
    "左カレンダー 月", min_value=1, max_value=12,
    value=datetime.date.today().month, step=1
)

left = datetime.date(year, month, 1)
right = left + relativedelta(months=1)

df1 = make_month_df(left.year, left.month)
df2 = make_month_df(right.year, right.month)

st.title("大阪・なんば〜長居エリア 空室カレンダー (2か月ビュー)")
col1, col2 = st.columns(2)
with col1:
    draw_month(df1, left.year, left.month)
with col2:
    draw_month(df2, right.year, right.month)
