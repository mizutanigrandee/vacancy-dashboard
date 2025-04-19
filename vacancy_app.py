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
    # 実際のクラス名は要確認。以下は例です。
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

# --- 3. メイン画面表示 ---
st.title("大阪・なんば〜長居エリア 空室カレンダー")

if st.button("在庫数を取得"):
    # 当日の在庫取得
    count = get_count(date)
    if count is not None:
        st.success(f"【{date}】残室ありホテル数：**{count} 件**")

        # 過去7日分の履歴を取得して DataFrame に格納
        days = [date - datetime.timedelta(days=i) for i in range(7)]
        data = {"date": [], "vacancy_count": []}
        for d in sorted(days):
            c = get_count(d)
            data["date"].append(d)
            data["vacancy_count"].append(c if c is not None else 0)
        df = pd.DataFrame(data).set_index("date")

        # テーブル＆折れ線グラフ
        st.write("### 過去7日間の推移", df)
        st.line_chart(df["vacancy_count"])

        # ── カレンダー形式で今月の残室数を表示 ──
        df_cal = df.copy()
        # カレンダー配置に必要な曜日・週番号を算出
        df_cal["weekday"] = df_cal.index.weekday  # 0=Mon,6=Sun
        df_cal["week"]    = (df_cal.index.day - 1 + df_cal["weekday"]) // 7

        st.write("### 今月の空室カレンダー")
        weeks = int(df_cal["week"].max()) + 1
        for w in range(weeks):
            cols = st.columns(7)
            wk = df_cal[df_cal["week"] == w]
            for dow in range(7):
                with cols[dow]:
                    cell = wk[wk["weekday"] == dow]
                    if not cell.empty:
                        day = cell.index.day[0]
                        val = int(cell["vacancy_count"][0])
                        # 色の濃淡は vacancy_count の最大値で正規化
                        max_val = df_cal["vacancy_count"].max() or 1
                        intensity = min(255, int(255 * val / max_val))
                        color = f"rgb(255, {255-intensity}, {255-intensity})"
                        st.markdown(
                            f"<div style='background:{color};"
                            " padding:8px; border-radius:4px; text-align:center;'>"
                            f"<strong>{day}</strong><br>"
                            f"<span style='font-size:20px;'>{val}件</span>"
                            "</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.write("")  # 空セル

