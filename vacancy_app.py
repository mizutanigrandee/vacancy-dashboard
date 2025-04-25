import streamlit as st
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os
import json
import pytz
import jpholiday

# --- ページ設定 ---
st.set_page_config(
    page_title="ミナミエリア 空室＆平均価格カレンダー",
    layout="wide"
)

st.title("ミナミエリア 空室＆平均価格カレンダー")

APP_ID = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"
EVENT_FILE = "event_data.json"

def generate_holidays(months: int = 6) -> set:
    today = dt.date.today()
    future = today + relativedelta(months=months)
    holidays = set()
    d = today
    while d <= future:
        if jpholiday.is_holiday(d):
            holidays.add(d)
        d += dt.timedelta(days=1)
    return holidays

HOLIDAYS = generate_holidays()

# --- データ読み書き ---
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

cache_data = load_json(CACHE_FILE)
event_data = load_json(EVENT_FILE)

# --- ナビゲーション ---
today = dt.date.today()
if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0

nav1, nav2, nav3 = st.columns([2, 2, 2])
with nav1:
    if st.button("◀ 前月"):
        st.session_state.month_offset -= 1
with nav2:
    if st.button("🗓 当月"):
        st.session_state.month_offset = 0
with nav3:
    if st.button("▶ 次月"):
        st.session_state.month_offset += 1

base_month = today.replace(day=1) + relativedelta(months=st.session_state.month_offset)
month1 = base_month
month2 = base_month + relativedelta(months=1)

# --- 需要シンボル ---
def get_demand_icon(vacancy, price):
    level = 0
    if (vacancy <= 70 or price >= 50000):
        level = 5
    elif (vacancy <= 100 or price >= 40000):
        level = 4
    elif (vacancy <= 150 or price >= 35000):
        level = 3
    elif (vacancy <= 200 or price >= 30000):
        level = 2
    elif (vacancy <= 250 or price >= 25000):
        level = 1
    return f"🔥{level}" if level > 0 else ""

# --- カレンダー描画 ---
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(month_date.year, month_date.month)
    today = dt.date.today()

    html = '<div class="calendar-wrapper">'
    html += '<table style="border-collapse:collapse;width:100%;text-align:center;">'
    html += '<thead><tr>' + ''.join(
        f'<th style="border:1px solid #aaa;padding:4px;background:#f0f0f0;">{d}</th>'
        for d in ["日","月","火","水","木","金","土"]
    ) + '</tr></thead><tbody>'

    for week in weeks:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td style="border:1px solid #aaa;padding:8px;background:#fff;"></td>'
                continue

            current = dt.date(month_date.year, month_date.month, day)
            bg = '#fff'
            if current < today:
                bg = '#ddd'
            elif current in HOLIDAYS or current.weekday() == 6:
                bg = '#ffecec'
            elif current.weekday() == 5:
                bg = '#e0f7ff'

            iso = current.isoformat()
            record = cache_data.get(iso, {"vacancy": 0, "avg_price": 0.0})
            count_html = f'<div>{record["vacancy"]}件</div>'
            price_html = f'<div>￥{int(record["avg_price"]):,}</div>'

            icon = get_demand_icon(record["vacancy"], record["avg_price"]) if current >= today else ""
            icon_html = f'<div style="position:absolute;top:2px;right:4px;font-size:14px;">{icon}</div>'

            event_html = ""
            events = event_data.get(iso, [])
            if isinstance(events, list):
for ev in event_data[iso]:
    event_html += f'<div style="margin-top:2px;">{ev["icon"]} {ev["name"]}</div>'
event_html = f'<div style="font-size: 12px; word-wrap: break-word; text-align: left;">{event_html}</div>'


            html += (
                f'<td style="border:1px solid #aaa;padding:8px;background:{bg};position:relative;">'
                f'{icon_html}'
                f'<div><strong>{day}</strong></div>'
                f'{count_html}{price_html}{event_html}'
                '</td>'
            )
        html += '</tr>'
    html += '</tbody></table></div>'
    return html


# --- 表示 ---
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{month1.year}年 {month1.month}月")
    st.markdown(draw_calendar(month1), unsafe_allow_html=True)
with col2:
    st.subheader(f"{month2.year}年 {month2.month}月")
    st.markdown(draw_calendar(month2), unsafe_allow_html=True)

# --- サイドバーでイベント登録 ---
with st.sidebar:
    st.markdown("### 📅 イベント登録")
    input_date = st.date_input("日付を選択", key="event_date_input")
    venue = st.selectbox("会場を選択", ["🔴 京セラドーム", "🔵 ヤンマースタジアム", "⚫ その他会場"], key="event_venue")
    event_name = st.text_input("イベント名", key="event_name_input")

    if st.button("➕ イベント追加"):
        iso_date = input_date.isoformat()
        entry = {"icon": venue.split()[0], "name": event_name}
        event_data.setdefault(iso_date, []).append(entry)
        save_json(EVENT_FILE, event_data)
        st.success(f"{iso_date} にイベントを追加しました")

# --- サイドバーでイベント削除モード ---
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🗑 登録済みイベントの削除")
    del_mode = st.checkbox("イベント削除モード", key="delete_mode")

    if del_mode:
        del_date = st.date_input("削除する日付を選択", key="del_event_date")
        iso_date = del_date.isoformat()
        events = event_data.get(iso_date, [])

        if not events:
            st.info("選択した日付にはイベントが登録されていません。")
        else:
            try:
                # ドロップダウン表示用の選択肢（番号 + アイコン + 名称）
                event_labels = [f"{i+1}. {ev.get('icon', '')} {ev.get('name', '')}" for i, ev in enumerate(events)]
                selected = st.selectbox("削除するイベントを選択", event_labels, key="del_event_select")
                index = int(selected.split(".")[0]) - 1

                if st.button("🚫 削除する"):
                    events.pop(index)
                    if events:
                        event_data[iso_date] = events
                    else:
                        del event_data[iso_date]
                    save_json(EVENT_FILE, event_data)
                    st.success(f"{iso_date} のイベントを削除しました")
            except Exception as e:
                st.error(f"イベントデータの読み込みで問題が発生しました: {e}")


# --- 注釈 ---
jst = pytz.timezone('Asia/Tokyo')
now_jst = dt.datetime.now(jst)
st.caption(f"最終更新時刻：{now_jst.strftime('%Y-%m-%d %H:%M:%S')}")

st.markdown("""
**《注釈》**  
- 在庫数、平均価格は『なんば・心斎橋・天王寺・阿倍野・長居』エリアから抽出しています  
- 表示される「平均価格」は、楽天トラベル上位90施設の平均最低価格です  
- 炎マーク（需要シンボル）は以下のルールで表示されます：  
  - 🔥1：残室数 ≤250 または 平均価格 ≥25,000円  
  - 🔥2：残室数 ≤200 または 平均価格 ≥30,000円  
  - 🔥3：残室数 ≤150 または 平均価格 ≥35,000円  
  - 🔥4：残室数 ≤100 または 平均価格 ≥40,000円  
  - 🔥5：残室数 ≤70 または 平均価格 ≥50,000円  
- 🔴：京セラドーム  
- 🔵：ヤンマースタジアム  
- ⚫：その他会場
""")
