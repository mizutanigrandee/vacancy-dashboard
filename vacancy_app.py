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

# --- smallClassCode のリストを取得（GetAreaClass API） ---
@st.cache_data(ttl=24*60*60)
def get_small_codes() -> list[tuple[str,str]]:
    url = "https://app.rakuten.co.jp/services/api/Travel/GetAreaClass/20131024"
    params = {"applicationId": APP_ID, "format": "json", "formatVersion": 2}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    # ネストされたlargeClasses/middleClasses/smallClassesを正しくパース
    for large_wrap in data.get("areaClasses", {}).get("largeClasses", []):
        large = large_wrap.get("largeClass", {})
        if large.get("code") == "japan":
            for mid_wrap in large.get("middleClasses", []):
                middle = mid_wrap.get("middleClass", {})
                if middle.get("code") == "osaka":
                    # smallClasses内のsmallClassを抽出
                    return [
                        (sw.get("smallClass", {}).get("code", ""),
                         sw.get("smallClass", {}).get("name", ""))
                        for sw in middle.get("smallClasses", [])
                    ]
    return []

small_codes = get_small_codes()
# サイドバーに小エリアコード一覧を表示
st.sidebar.write("DEBUG ▶ Osaka smallClassCodes:", small_codes)

# --- タイトル ---
st.title("楽天トラベル 空室カレンダー（2か月表示）")

# --- 祝日リスト（2025年4月〜5月） ---
HOLIDAYS = {
    dt.date(2025, 4, 29),  # 昭和の日
    dt.date(2025, 5, 3),   # 憲法記念日
    dt.date(2025, 5, 4),   # みどりの日
    dt.date(2025, 5, 5),   # こどもの日
}

# --- VacantHotelSearch API 呼び出し ---
@st.cache_data(ttl=24*60*60)
def fetch_vacancy_count(date: dt.date) -> int:
    if date < dt.date.today():
        return 0
    params = {
        "applicationId": APP_ID,
        "format": "json",
        "checkinDate": date.strftime("%Y-%m-%d"),
        "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum": 1,
        # ここにサイドバーで確認した smallClassCode を設定してください
        "largeClassCode":  "japan",
        "middleClassCode": "osaka",
        "smallClassCode":  "osaka_namba_shinsaibashi"
    }
    url = (
        "https://app.rakuten.co.jp/services/api/"
        "Travel/VacantHotelSearch/20170426"
    )
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("pagingInfo", {}).get("recordCount", 0)
    except Exception:
        return 0
    finally:
        time.sleep(0.6)

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
                html += '<td style="border:1px solid #aaa;padding:8px;background:#fff;"></td>'
            else:
                current = dt.date(month_date.year, month_date.month, day)
                if current < today:
                    bg = '#ddd'
                elif current in HOLIDAYS or current.weekday() == 6:
                    bg = '#ffecec'
                elif current.weekday() == 5:
                    bg = '#e0f7ff'
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

# --- メイン：2か月分表示 ---
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
