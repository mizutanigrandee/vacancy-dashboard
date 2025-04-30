import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os, json, pytz, jpholiday

st.set_page_config(page_title="【超いいツール】ミナミエリア 空室＆平均価格カレンダー", layout="wide")
st.title("【超いいツール】ミナミエリア 空室＆平均価格カレンダー")

APP_ID      = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE  = "vacancy_price_cache.json"
EVENT_EXCEL = "event_data.xlsx"

# ───────── 祝日生成 ─────────
def generate_holidays(months=6):
    today = dt.date.today()
    hol   = set()
    for i in range(months*31):
        d = today + dt.timedelta(days=i)
        if jpholiday.is_holiday(d):
            hol.add(d)
    return hol
HOLIDAYS = generate_holidays()

# ───────── データ読み込み ─────────
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_event_data_from_excel(filepath=EVENT_EXCEL):
    if not os.path.exists(filepath):
        return {}
    df = pd.read_excel(filepath).dropna(subset=["date", "icon", "name"])
    ev = {}
    for _, row in df.iterrows():
        key = pd.to_datetime(row["date"]).date().isoformat()
        ev.setdefault(key, []).append({"icon": row["icon"], "name": row["name"]})
    return ev

cache_data = load_json(CACHE_FILE)
event_data = load_event_data_from_excel()

# ───────── ナビゲーション ─────────
today = dt.date.today()
if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0

nav1, nav2, nav3 = st.columns(3)
with nav1:
    st.button("◀ 前月", on_click=lambda: st.session_state.__setitem__("month_offset", st.session_state.month_offset-1))
with nav2:
    st.button("🗓 当月", on_click=lambda: st.session_state.__setitem__("month_offset", 0))
with nav3:
    st.button("▶ 次月", on_click=lambda: st.session_state.__setitem__("month_offset", st.session_state.month_offset+1))

base_month = today.replace(day=1) + relativedelta(months=st.session_state.month_offset)
month1     = base_month
month2     = base_month + relativedelta(months=1)

# ───────── 需要アイコン ─────────
def get_demand_icon(vac, price):
    if vac<=70 or price>=50000:   return "🔥5"
    if vac<=100 or price>=40000:  return "🔥4"
    if vac<=150 or price>=35000:  return "🔥3"
    if vac<=200 or price>=30000:  return "🔥2"
    if vac<=250 or price>=25000:  return "🔥1"
    return ""

# ───────── カレンダー描画 ─────────
def draw_calendar(month_date: dt.date) -> str:
    cal   = calendar.Calendar(calendar.SUNDAY)
    weeks = cal.monthdatescalendar(month_date.year, month_date.month)
    today = dt.date.today()

    html  = '<div class="calendar-wrapper"><table style="border-collapse:collapse;width:100%;table-layout:fixed;text-align:center;">'
    html += '<style> .calendar-wrapper td { padding-top: 30px !important; } </style>'

    html += '<thead><tr>' + ''.join(f'<th style="border:1px solid #aaa;padding:4px;background:#f0f0f0;">{d}</th>' for d in "日月火水木金土") + '</tr></thead><tbody>'

    for week in weeks:
        html += '<tr>'
        for current in week:
            if current.month != month_date.month:
                html += '<td style="border:1px solid #aaa;padding:8px;background:#fff;"></td>'
                continue

            bg = '#ddd' if current < today else (
                 '#ffecec' if (current in HOLIDAYS or current.weekday()==6) else (
                 '#e0f7ff' if current.weekday()==5 else '#fff'))

            iso = current.isoformat()
            rec = cache_data.get(iso, {"vacancy":0, "avg_price":0})
            vac = rec["vacancy"]
            price = int(rec["avg_price"])

            # 差分値（キャッシュから取得）
            diff_v = rec.get("vacancy_diff", 0)
            diff_p = rec.get("avg_price_diff", 0)

            vac_html  = f'<div style="font-size:16px;font-weight:bold;">{vac}件'
            if diff_v>0:  vac_html += f'<span style="color:blue;font-size:12px;">（+{diff_v}件）</span>'
            elif diff_v<0:vac_html += f'<span style="color:red;font-size:12px;">（{diff_v}件）</span>'
            vac_html += '</div>'

            price_html = f'<div style="font-size:16px;font-weight:bold;">￥{price:,}'
            if diff_p>0:  price_html += '<span style="color:red;"> ↑</span>'
            elif diff_p<0:price_html += '<span style="color:blue;"> ↓</span>'
            price_html += '</div>'

            icon_html = ''
            if current >= today:
                icon_html = f'<div style="position:absolute;top:2px;right:4px;font-size:16px;">{get_demand_icon(vac, price)}</div>'

            event_html = ''
            if iso in event_data:
                event_html = '<div style="font-size:12px;margin-top:4px;">' + "<br>".join(f'{e["icon"]} {e["name"]}' for e in event_data[iso]) + '</div>'

            html += (
                f'<td style="border:1px solid #aaa;padding:8px;background:{bg};position:relative;vertical-align:top;">'
                f'{icon_html}'
                f'<div style="position:absolute; top:4px; left:4px; font-size:14px; color:gray; font-weight:bold;">{current.day}</div>'
                f'{vac_html}{price_html}{event_html}'
                '</td>'
            )
        html += '</tr>'
    html += '</tbody></table></div>'
    return html

# 表示
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)

# 最終巡回時刻表示

try:
    mtime = os.path.getmtime(CACHE_FILE)
    last_run = dt.datetime.fromtimestamp(mtime, pytz.timezone('Asia/Tokyo'))
    st.markdown(
        f"<p style='font-size:16px; color:gray;'>最終巡回時刻：{last_run:%Y-%m-%d %H:%M:%S}</p>",
        unsafe_allow_html=True
    )
except Exception:
    st.markdown(
        "<p style='font-size:20px; color:gray;'>最終巡回時刻：取得できませんでした</p>",
        unsafe_allow_html=True
    )


# ───────── 注釈 ─────────
st.markdown(
    """
    <div style='font-size:16px; color:#555;'>
    <strong>《注釈》</strong><br>
    - 在庫数、平均価格は『なんば・心斎橋・天王寺・阿倍野・長居』エリアから抽出しています。<br>
    - 表示される「平均価格」は、楽天トラベル検索上位90施設の平均最低価格です。<br>
    - 会場アイコン：🔴京セラドーム / 🔵ヤンマースタジアム / ★その他会場<br>
    - 炎マーク（需要シンボル）の内訳：<br>
      &nbsp;&nbsp;・🔥1：残室 ≤250 または 価格 ≥25,000円<br>
      &nbsp;&nbsp;・🔥2：残室 ≤200 または 価格 ≥30,000円<br>
      &nbsp;&nbsp;・🔥3：残室 ≤150 または 価格 ≥35,000円<br>
      &nbsp;&nbsp;・🔥4：残室 ≤100 または 価格 ≥40,000円<br>
      &nbsp;&nbsp;・🔥5：残室 ≤70 または 価格 ≥50,000円<br>

    </div>
    """,
    unsafe_allow_html=True
)
