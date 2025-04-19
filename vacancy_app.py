# vacancy_app.py

import streamlit as st
import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd

# --- 1. データ取得ロジック ---
def fetch_vacancy_count(checkin_date: str) -> int:
    """
    楽天トラベル マップ画面から
    大阪・なんば〜長居エリアの残室ありホテル数を取得
    """
    url = (
        "https://travel.rakuten.co.jp/vacancy/"
        "?l-id=vacancy_test_c_map_osaka"
        "#regular/normal/2/9/osaka/"
        f"?checkinDate={checkin_date}"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # HTMLの実際のクラス名が変わる可能性があるので、要確認
    items = soup.select(".hotelList_item .vacancy-available")
    return len(items)

@st.cache_data(ttl=3600)
def get_count(checkin_date: datetime.date) -> int:
    """
    1時間キャッシュ＋取得時に3回リトライ
    """
    last_err = None
    for _ in range(3):
        try:
            return fetch_vacancy_count(checkin_date.strftime("%Y-%m-%d"))
        except Exception as e:
            last_err = e
    st.error(f"取得に失敗しました: {last_err}")
    return None

# --- 2. サイドバー設定 ---
st.sidebar.title("設定")
date = st.sidebar.date_input("チェックイン日", datetime.date.today())
st.sidebar.markdown("---")
st.sidebar.write("※データは楽天トラベル マップ画面より取得")

# --- 3. メイン画面 ---
st.title("大阪・なんば〜長居エリア 空室カレンダー")

if st.button("在庫数を取得"):
    count = get_count(date)
    if count is not None:
        st.success(f"【{date}】残室ありホテル数：**{count} 件**")

        # 過去7日分の履歴データを集めてテーブル＆グラフ表示
        days = [date - datetime.timedelta(days=i) for i in range(7)]
        data = {"date": [], "vacancy_count": []}
        for d in sorted(days):
            c = get_count(d)
            data["date"].append(d)
            data["vacancy_count"].append(c if c is not None else 0)
        df = pd.DataFrame(data).set_index("date")

        st.write("### 過去7日間の推移", df)
        st.line_chart(df["vacancy_count"])
