import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import time

# --- ページ設定 ---
st.set_page_config(
    page_title="空室カレンダー（2か月表示）",
    layout="wide"
)

# --- シークレット情報 ---
APP_ID = st.secrets["RAKUTEN_APP_ID"]

# --- タイトル ---
st.title("楽天トラベル 空室カレンダー（2か月表示）")

# --- 祝日リスト（2025年4月〜5月） ---
HOLIDAYS = {
    dt.date(2025, 4, 29),  # 昭和の日
    dt.date(2025, 5, 3),   # 憲法記念日
    dt.date(2025, 5, 4),   # みどりの日
    dt.date(2025, 5, 5),   # こどもの日
}

# --- VacantHotelSearch API 呼び出し（デバッグ付き） ---
@st.cache_data(ttl=24*60*60)
def fetch_vacancy_count(date: dt.date) -> int:
    # 過去日は API 呼び出しせず 0 件
    if date < dt.date.today():
        return 0

    # パラメータを組み立て
    params = {
        "applicationId": APP_ID,
        "format": "json",
        "checkinDate": date.strftime("%Y-%m-%d"),
        "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum": 1,
        "largeClassCode":  "japan",
        "middleClassCode": "osaka",
        "smallClassCode":  "osaka_namba_shinsaibashi"
    }
    # デバッグ出力: 日付とパラメータ
    st.sidebar.write(f"▶ fetch_vacancy_count({date}): {params}")

    url = (
        "https://app.rakuten.co.jp/services/api/"
        "Travel/VacantHotelSearch/20170426"
    )
    # リクエスト実行
    r = requests.get(url, params=params, timeout=10)
    # デバッグ出力: ステータスコード
    st.sidebar.write(f"  status: {r.status_code}")
    try:
        data = r.json()
        st.sidebar.write(f"  resp: {data}")
    except ValueError:
        st.sidebar.write("  response not JSON")
        return 0

    # 404はデータ無しとみなす
    if r.status_code == 404:
        return 0
    # 200以外はエラー扱い
    if r.status_code != 200:
        st.sidebar.write(f"  API ERROR status {r.status_code}")
        return 0

    # 成功時はrecordCountを返却
    return data.get("pagingInfo", {}).get("recordCount", 0)

# --- カレンダー描画関数 ---
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)
    today = dt.date.today()

    html = '<table style="border-collapse:collapse;width:100%;text-align:center;">'
    html += '<thead><tr>' + ''.join(
        f'<th style="border:1px solid #aaa;padding:4px;background:#f0f0f0;">{d}</th>'
        for d in ["日","月","火","水","木","金","土"]
    ) + '</tr></thead><tbody>'

    for week in weeks:
        html += '<tr>'
        for day in week:
            if day == 0:
                # 当月外
                html += '<td style="border:1px solid #aaa;padding:8px;background:#fff;"></td>'
            else:
                current = dt.date(month_date.year, month_date.month, day)
                # 背景色判定
                if current < today:
                    bg = '#ddd'  # 過去日
                elif current in HOLIDAYS or current.weekday() == 6:
                    bg = '#ffecec'  # 日祝
                elif current.weekday() == 5:
                    bg = '#e0f7ff'  # 土曜
                else:
                    bg = '#fff'

                count = fetch_vacancy_count(current)
                count_html = f'<div>{count} 件</div>' if count > 0 else ''
                html += (
                    f'<td style="border:1px solid #aaa;padding:8px;background:{bg};">'
                    f'<div><strong>{day}</strong></div>'
                    f'{count_html}'
                    '</td>'
                )
        html += '</tr>'
    html += '</tbody></table>'
    return html

# --- メイン: 2か月表示 ---
today = dt.date.today()
baseline = st.sidebar.date_input("基準月を選択", today.replace(day=1))
month1 = baseline.replace(day=1)
month2 = (month1 + relativedelta(months=1)).replace(day=1)

col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)
