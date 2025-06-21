import streamlit as st
import base64
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os, json, pytz, jpholiday
import altair as alt

st.set_page_config(page_title="テスト版【めちゃいいツール】ミナミエリア 空室＆平均価格カレンダー", layout="wide")

# 🔻スマホ専用カレンダーCSS
st.markdown("""
<style>
@media (max-width: 700px) {
    .calendar-wrapper td, .calendar-wrapper th {
        min-width: 32px !important;
        max-width: 38px !important;
        font-size: 9px !important;
        padding: 1px 0 1px 0 !important;
    }
    .calendar-wrapper td div,
    .calendar-wrapper td span {
        font-size: 9px !important;
        line-height: 1.05 !important;
    }
    .calendar-wrapper td > div > div:nth-child(2),
    .calendar-wrapper td > div > div:nth-child(3) {
        display: block !important;
        width: 100% !important;
        text-align: left !important;
    }
}
</style>
""", unsafe_allow_html=True)


# --- バナー表示は本稼働のまま
if os.path.exists("バナー画像3.png"):
    with open("バナー画像3.png", "rb") as f:
        img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    st.markdown(f"""
        <div style="width: 100%; background-color: #e4f0f4; padding: 5px 0; text-align: left;">
            <img src="data:image/png;base64,{img_base64}" style="max-width: 1000px; height: auto;">
        </div><br>
    """, unsafe_allow_html=True)

APP_ID = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"
HISTORICAL_FILE = "historical_data.json"
EVENT_EXCEL = "event_data.xlsx"

def generate_holidays(months=13):
    today = dt.date.today()
    hol = set()
    for i in range(months * 31):
        d = today + dt.timedelta(days=i)
        if jpholiday.is_holiday(d):
            hol.add(d)
    return hol
HOLIDAYS = generate_holidays()

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

event_data = load_event_data_from_excel()
cache_data = load_json(CACHE_FILE)

# 祝日等の色分けロジック（draw_calendarは本稼働のまま）
def get_demand_icon(vac, price):
    if vac <= 70 or price >= 50000: return "🔥5"
    if vac <= 100 or price >= 40000: return "🔥4"
    if vac <= 150 or price >= 35000: return "🔥3"
    if vac <= 200 or price >= 30000: return "🔥2"
    if vac <= 250 or price >= 25000: return "🔥1"
    return ""

def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(calendar.SUNDAY)
    weeks = cal.monthdatescalendar(month_date.year, month_date.month)
    today = dt.date.today()
    html = '<div class="calendar-wrapper"><table style="border-collapse:collapse;width:100%;table-layout:fixed;text-align:center;">'
    html += """
    <style>
    .calendar-wrapper td {
        padding-top: 30px !important;
        transition: background-color 0.2s ease;
    }
    .calendar-wrapper td:hover {
        background-color: #f5faff !important;
        cursor: pointer;
    }
    </style>
    """
    html += '<thead style="background:#f4f4f4;color:#333;font-weight:bold;"><tr>'
    html += ''.join(f'<th style="border:1px solid #aaa;padding:4px;">{d}</th>' for d in "日月火水木金土")
    html += '</tr></thead><tbody>'
    for week in weeks:
        html += '<tr>'
        for current in week:
            if current.month != month_date.month:
                html += '<td style="border:1px solid #aaa;padding:8px;background:#fff;"></td>'
                continue
            bg = '#ddd' if current < today else ('#ffecec' if (current in HOLIDAYS or current.weekday() == 6) else ('#e0f7ff' if current.weekday() == 5 else '#fff'))
            iso = current.isoformat()
            rec = cache_data.get(iso, {"vacancy": 0, "avg_price": 0})
            vac = rec["vacancy"]
            price = int(rec["avg_price"])
            diff_v = rec.get("vacancy_diff", 0)
            diff_p = rec.get("avg_price_diff", 0)
            vac_html = f'<div style="font-size:16px;font-weight:bold;">{vac}件'
            if diff_v > 0:
                vac_html += f'<span style="color:blue;font-size:12px;">（+{diff_v}）</span>'
            elif diff_v < 0:
                vac_html += f'<span style="color:red;font-size:12px;">（{diff_v}）</span>'
            vac_html += '</div>'
            price_html = f'<div style="font-size:16px;font-weight:bold;">￥{price:,}'
            if diff_p > 0:
                price_html += '<span style="color:red;"> ↑</span>'
            elif diff_p < 0:
                price_html += '<span style="color:blue;"> ↓</span>'
            price_html += '</div>'
            icon_html = f'<div style="position:absolute;top:2px;right:4px;font-size:16px;">{get_demand_icon(vac, price)}</div>' if current >= today else ''
            event_html = '<div style="font-size:12px;margin-top:4px;">' + "<br>".join(f'{e["icon"]} {e["name"]}' for e in event_data.get(iso, [])) + '</div>'
            html += (
                f'<td style="border:1px solid #aaa;padding:8px;background:{bg};position:relative;vertical-align:top;">'
                f'<a href="?selected={iso}" target="_self" '
                f'style="display:block;width:100%;height:100%;text-decoration:none;color:inherit;">'
                f'{icon_html}'
                f'<div style="position:absolute; top:4px; left:4px; font-size:14px; font-weight:bold;">{current.day}</div>'
                f'{vac_html}{price_html}{event_html}'
                f'</a>'
                f'</td>'
            )
        html += '</tr>'
    html += '</tbody></table></div>'
    return html


# --- カレンダー描画ロジック ---
today = dt.date.today()
params = st.query_params
selected_date = params.get("selected")
if isinstance(selected_date, list): selected_date = selected_date[0]

# ナビゲーションUI
if "month_offset" not in st.session_state: st.session_state.month_offset = 0
MAX_MONTH_OFFSET = 12
nav_left, nav_center, nav_right = st.columns([3, 2, 3])
with nav_center:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ 前月"):
            st.session_state.month_offset = max(st.session_state.month_offset - 1, -MAX_MONTH_OFFSET)
    with col2:
        if st.button("📅 当月"):
            st.session_state.month_offset = 0
    with col3:
        if st.button("➡️ 次月"):
            st.session_state.month_offset = min(st.session_state.month_offset + 1, MAX_MONTH_OFFSET)

base_month = today.replace(day=1) + relativedelta(months=st.session_state.month_offset)
month1 = base_month
month2 = base_month + relativedelta(months=1)

# --- グラフ履歴 ---
def load_historical_data():
    if os.path.exists(HISTORICAL_FILE):
        with open(HISTORICAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
historical_data = load_historical_data()

if "show_graph" not in st.session_state:
    st.session_state["show_graph"] = True

# --- 日付未選択 または グラフ閉じた場合 → カレンダーのみ
if not selected_date or not st.session_state["show_graph"]:
    st.session_state["show_graph"] = True
    cal1, cal2 = st.columns(2)
    with cal1:
        st.subheader(f"{month1.year}年 {month1.month}月")
        st.markdown(draw_calendar(month1), unsafe_allow_html=True)
    with cal2:
        st.subheader(f"{month2.year}年 {month2.month}月")
        st.markdown(draw_calendar(month2), unsafe_allow_html=True)
# --- 日付選択中 → 推移グラフ＋カレンダー2枚
else:
    left, right = st.columns([3, 7])
    with left:
        button_cols = st.columns([5, 5, 5])
        with button_cols[0]:
            if st.button("❌ 閉じる"):
                st.query_params.clear()
                st.session_state["show_graph"] = False
                st.rerun()
        with button_cols[1]:
            if st.button("＜前日"):
                new_dt = pd.to_datetime(selected_date).date() - dt.timedelta(days=1)
                st.query_params["selected"] = new_dt.isoformat()
                st.rerun()
        with button_cols[2]:
            if st.button("翌日＞"):
                new_dt = pd.to_datetime(selected_date).date() + dt.timedelta(days=1)
                st.query_params["selected"] = new_dt.isoformat()
                st.rerun()
        st.markdown(f"#### {selected_date} の在庫・価格推移")
        if selected_date not in historical_data:
            st.info("この日付の履歴データがありません")
        else:
            df = pd.DataFrame(
                sorted(
                    (
                        {
                            "取得日": hist_date,
                            "在庫数": rec["vacancy"],
                            "平均単価": rec["avg_price"],
                        }
                        for hist_date, rec in historical_data[selected_date].items()
                    ),
                    key=lambda x: x["取得日"]
                )
            )
            df["取得日"] = pd.to_datetime(df["取得日"])
        st.write("##### 在庫数")
        chart_vac = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X("取得日:T", axis=alt.Axis(title=None, format="%m/%d")),
                y=alt.Y("在庫数:Q", axis=alt.Axis(title=None), scale=alt.Scale(domain=[0, 350]))
            )
            .properties(height=320, width=600)
        )
        st.altair_chart(chart_vac, use_container_width=True)

        st.write("##### 平均単価 (円)")
        chart_price = (
            alt.Chart(df)
            .mark_line(point=True, color="#e15759")
            .encode(
                x=alt.X("取得日:T", axis=alt.Axis(title=None, format="%m/%d")),
                y=alt.Y("平均単価:Q", axis=alt.Axis(title=None), scale=alt.Scale(domain=[0, 35000]))
            )
            .properties(height=320, width=600)
        )
        st.altair_chart(chart_price, use_container_width=True)

            
    with right:
        cal1, cal2 = st.columns(2)
        with cal1:
            st.subheader(f"{month1.year}年 {month1.month}月")
            st.markdown(draw_calendar(month1), unsafe_allow_html=True)
        with cal2:
            st.subheader(f"{month2.year}年 {month2.month}月")
            st.markdown(draw_calendar(month2), unsafe_allow_html=True)

# --- カレンダー下部の案内・注釈・巡回時刻 ---
st.markdown(
    "<div style='font-size:17px; color:#296;'>日付を選択すると推移グラフが表示されます</div>",
    unsafe_allow_html=True
)
try:
    mtime = os.path.getmtime(CACHE_FILE)
    last_run = dt.datetime.fromtimestamp(mtime, pytz.timezone('Asia/Tokyo'))
    st.markdown(f"<p style='font-size:16px; color:gray;'>最終巡回時刻：{last_run:%Y-%m-%d %H:%M:%S}</p>", unsafe_allow_html=True)
except Exception:
    st.markdown("<p style='font-size:20px; color:gray;'>最終巡回時刻：取得できませんでした</p>", unsafe_allow_html=True)
st.markdown("""
    <div style='font-size:16px; color:#555;'><strong>《注釈》</strong><br>
    - 在庫数、平均価格は『なんば・心斎橋・天王寺・阿倍野・長居』エリアから抽出しています。<br>
    - 表示される「平均価格」は、楽天トラベル検索上位90施設の平均最低価格です。<br>
    - 空室数の<span style="color:blue;">（+N）</span>／<span style="color:red;">（−N）</span>は、前回巡回時点との在庫数の増減を示します。<br>
    - 平均価格の<span style="color:red;">↑</span>／<span style="color:blue;">↓</span>は、前回巡回時点との平均価格の上昇／下降を示します。<br>
    - 会場アイコン：🔴京セラドーム / 🔵ヤンマースタジアム / ★その他会場<br>
    - 炎マーク（需要シンボル）の内訳：<br>
      &nbsp;&nbsp;・🔥1：残室 ≤250 または 価格 ≥25,000円<br>
      &nbsp;&nbsp;・🔥2：残室 ≤200 または 価格 ≥30,000円<br>
      &nbsp;&nbsp;・🔥3：残室 ≤150 または 価格 ≥35,000円<br>
      &nbsp;&nbsp;・🔥4：残室 ≤100 または 価格 ≥40,000円<br>
      &nbsp;&nbsp;・🔥5：残室 ≤70 または 価格 ≥50,000円<br>
    </div>
    """, unsafe_allow_html=True)
