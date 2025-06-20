import streamlit as st
import base64
from PIL import Image
import requests
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os, json, pytz, jpholiday
import matplotlib.pyplot as plt
import altair as alt


st.set_page_config(page_title="テスト版【めちゃいいツール】ミナミエリア 空室＆平均価格カレンダー", layout="wide")

st.markdown("""
    <style>
    /* 既存の全体設定など */
    .main .block-container {
        max-width: 1600px;
        padding-left: 2vw;
        padding-right: 2vw;
    }
    h1, h2, h3, h4 {
        font-size: 2vw;
    }
    .stButton > button {
        font-size: 1.2vw !important;
        padding: 0.6em 1.5em;
    }
    .calendar-wrapper {
        overflow-x: auto;
        width: 100%;
    }
    @media screen and (max-width: 700px) {
        h1, h2, h3, h4 { font-size: 4vw !important; }
        .main .block-container { padding-left: 2vw; padding-right: 2vw; }
        .stButton > button { font-size: 2vw !important; }
    }

    /* ここからカレンダーセルのスリム化を追加！！ */
    .calendar-col {
        min-width: 54px !important;
        max-width: 60px !important;
        padding: 2px 2px !important;
        font-size: 16px !important;
        word-break: keep-all;
    }
    @media (max-width: 600px) {
        .calendar-col {
            min-width: 36px !important;
            max-width: 42px !important;
            font-size: 11px !important;
            padding: 1px 1px !important;
        }
        .calendar-col span, .calendar-col div {
            font-size: 10px !important;
        }
    }
    /* PC版：中央寄せ＆最大幅設定 */
@media (min-width: 700px) {
    .calendar-wrapper {
        margin: 0 auto !important;
        max-width: 1500px !important;
        min-width: 980px !important;
        width: 92vw !important;  /* 画面幅の92% */
        display: flex;
        justify-content: center;
    }
    .calendar-wrapper table {
        margin-left: auto !important;
        margin-right: auto !important;
        width: 100% !important;
        max-width: 1500px !important;
    }
}
@media (min-width: 700px) {
    .calendar-wrapper {
        margin: 0 auto !important;
        max-width: 1100px !important;  /* ←ここを広げすぎず1100px程度に */
        min-width: 900px !important;
        width: 100% !important;
        display: flex;
        justify-content: center;
    }
    .calendar-wrapper table {
        margin-left: auto !important;
        margin-right: auto !important;
        width: 100% !important;
        max-width: 1100px !important; /* テーブル幅も同じに */
        table-layout: fixed !important;
    }
    .calendar-wrapper td {
        min-width: 65px !important;  /* ←セル幅は1日あたりこのくらいが推奨 */
        max-width: 85px !important;
        height: 85px !important;
    }
}


    </style>
""", unsafe_allow_html=True)


# 🔻 base64埋め込みバナー
if os.path.exists("バナー画像3.png"):
    with open("バナー画像3.png", "rb") as f:
        img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    banner_html = f"""
        <div style="width: 100%; background-color: #e4f0f4; padding: 5px 0; text-align: left;">
            <img src="data:image/png;base64,{img_base64}" style="max-width: 1000px; height: auto;">
        </div>
    """
    st.markdown(banner_html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# 定数
APP_ID = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"
HISTORICAL_FILE = "historical_data.json"
EVENT_EXCEL = "event_data.xlsx"

# ───────── 祝日生成 ─────────
def generate_holidays(months=13):
    today = dt.date.today()
    hol = set()
    for i in range(months * 31):
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

# データ読み込み実行
event_data = load_event_data_from_excel()
cache_data = load_json(CACHE_FILE)

# --- ナビゲーション ---
today = dt.date.today()

# ▼▼▼ ここを新しく修正！ ▼▼▼
params = st.query_params
selected_date = params.get("selected")
if isinstance(selected_date, list):
    selected_date = selected_date[0]

# 選択された日付があればその月を基準に、なければ今日
if selected_date:
    try:
        base_month = pd.to_datetime(selected_date).date().replace(day=1)
    except Exception:
        base_month = today.replace(day=1)
else:
    base_month = today.replace(day=1)

# 月移動はセッションに保持（なければ0）
if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0

MAX_MONTH_OFFSET = 12

# ボタンUI
nav_left, nav_center, nav_right = st.columns([3, 2, 3])
with nav_center:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ 前月"):
            st.session_state.month_offset -= 1
    with col2:
        if st.button("📅 当月"):
            st.session_state.month_offset = 0
    with col3:
        if st.button("➡️ 次月"):
            st.session_state.month_offset += 1

# ▼▼▼ ここも修正（カレンダー月をオフセット） ▼▼▼
month1 = base_month + relativedelta(months=st.session_state.month_offset)
month2 = month1 + relativedelta(months=1)


# ───────── 需要アイコン ─────────
def get_demand_icon(vac, price):
    if vac <= 70 or price >= 50000:
        return "🔥5"
    if vac <= 100 or price >= 40000:
        return "🔥4"
    if vac <= 150 or price >= 35000:
        return "🔥3"
    if vac <= 200 or price >= 30000:
        return "🔥2"
    if vac <= 250 or price >= 25000:
        return "🔥1"
    return ""

# ───────── カレンダー描画 ─────────
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(calendar.SUNDAY)
    weeks = cal.monthdatescalendar(month_date.year, month_date.month)
    today = dt.date.today()
    html = '<div class="calendar-wrapper"><table style="border-collapse:collapse;width:100%;table-layout:fixed;text-align:center;">'
    html += """
    <style>
    .calendar-wrapper td {
        padding: 0 !important;
        vertical-align: top !important;
        min-width: 46px !important;
        max-width: 64px !important;
        height: 92px !important;
        position: relative;
    }
    .calendar-cell-inner {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        justify-content: flex-start;
        height: 100%;
        width: 100%;
        padding: 3px 2px 2px 2px;
        box-sizing: border-box;
    }
    .calendar-date-row {
        width: 100%;
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        justify-content: space-between;
    }
    .calendar-date-day {
        font-size: 13px;
        font-weight: bold;
        color: #222;
    }
    .calendar-demand-icon {
        font-size: 15px;
        font-weight: bold;
        color: #e9743a;
        margin-left: auto;
    }
    .calendar-vac-row, .calendar-price-row {
        font-size: 12px;
        font-weight: bold;
        width: 100%;
        line-height: 1.1;
        display: flex;
        flex-direction: row;
        justify-content: flex-start;
        align-items: baseline;
        margin-top: 1px;
    }
    .calendar-price-row {
        font-size: 12px;
        color: #111;
        margin-bottom: 2px;
    }
    .calendar-vac-diff, .calendar-price-diff {
        font-size: 10px;
        margin-left: 2px;
    }
    .calendar-price-diff-up {
        color: red;
    }
    .calendar-price-diff-down {
        color: blue;
    }
    .calendar-vac-diff-up {
        color: blue;
    }
    .calendar-vac-diff-down {
        color: red;
    }
    .calendar-event-row {
        font-size: 10px;
        color: #444;
        width: 100%;
        margin-top: 2px;
        word-break: break-all;
        line-height: 1.1;
    }
    @media (max-width: 600px) {
        .calendar-wrapper td {
            min-width: 38px !important;
            max-width: 40px !important;
            height: 92px !important;
        }
        .calendar-date-day { font-size: 11px !important; }
        .calendar-demand-icon { font-size: 13px !important; }
        .calendar-vac-row, .calendar-price-row { font-size: 11px !important; }
        .calendar-event-row { font-size: 9px !important; }
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
            # 日付・需要
            date_row = (
                f'<div class="calendar-date-row">'
                f'<span class="calendar-date-day">{current.day}</span>'
                f'<span class="calendar-demand-icon">{get_demand_icon(vac, price) if current >= today else ""}</span>'
                f'</div>'
            )
            # 在庫＋前日比
            vac_row = (
                f'<div class="calendar-vac-row">'
                f'{vac}件'
                f'<span class="calendar-vac-diff {"calendar-vac-diff-up" if diff_v > 0 else "calendar-vac-diff-down" if diff_v < 0 else ""}">'
                f'{f"（{("+" if diff_v > 0 else "")}{diff_v}）" if diff_v != 0 else ""}'
                f'</span>'
                f'</div>'
            )
            # 価格＋上下
            price_row = (
                f'<div class="calendar-price-row">'
                f'¥{price:,}'
                f'<span class="calendar-price-diff {"calendar-price-diff-up" if diff_p > 0 else "calendar-price-diff-down" if diff_p < 0 else ""}">'
                f'{"↑" if diff_p > 0 else "↓" if diff_p < 0 else ""}'
                f'</span>'
                f'</div>'
            )
            # イベント
            events = event_data.get(iso, [])
            event_row = (
                '<div class="calendar-event-row">' +
                '<br>'.join(f'{e["icon"]} {e["name"]}' for e in events) +
                '</div>' if events else ''
            )
            # 全体ラップ
            html += (
                f'<td style="position:relative;vertical-align:top;border:1px solid #aaa;background:{bg};padding:0;">'
                f'<a href="?selected={iso}" target="_self" style="display:block;width:100%;height:100%;text-decoration:none;color:inherit;">'
                f'<div class="calendar-cell-inner">'
                f'{date_row}{vac_row}{price_row}{event_row}'
                f'</div>'
                f'</a></td>'
            )
        html += '</tr>'
    html += '</tbody></table></div>'
    return html



# 履歴データ読込
def load_historical_data():
    if os.path.exists(HISTORICAL_FILE):
        with open(HISTORICAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

historical_data = load_historical_data()  # ←これでデータが読み込まれます





# ───────── グラフ＋カレンダー表示分岐 ─────────
params = st.query_params
selected_date = params.get("selected")
if isinstance(selected_date, list):
    selected_date = selected_date[0]

# グラフの表示管理（初期値はTrue）
if "show_graph" not in st.session_state:
    st.session_state["show_graph"] = True

# 日付未選択 または グラフ閉じた場合→カレンダー全画面
if not selected_date or not st.session_state["show_graph"]:
    st.session_state["show_graph"] = True  # リセット
    cal1, cal2 = st.columns([1, 1])
    with cal1:
        st.subheader(f"{month1.year}年 {month1.month}月")
        st.markdown(draw_calendar(month1), unsafe_allow_html=True)
    with cal2:
        st.subheader(f"{month2.year}年 {month2.month}月")
        st.markdown(draw_calendar(month2), unsafe_allow_html=True)

# 日付選択中＆グラフ表示 → 3:7レイアウト
elif selected_date and st.session_state["show_graph"]:
    left, right = st.columns([3, 7])
    with left:
        # タイトル下に3ボタンを横並び・左寄せで配置
        button_cols = st.columns([5, 5, 5])  # [閉じる][前日][翌日]
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
        # ボタン下にグラフタイトルと内容
        st.markdown(f"#### {selected_date} の在庫・価格推移")
        if selected_date not in historical_data:
            st.info("この日付の履歴データがありません")
        else:
            # DataFrame からグラフ生成
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
                    y=alt.Y("在庫数:Q", axis=alt.Axis(title=None))
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
                    y=alt.Y("平均単価:Q", axis=alt.Axis(title=None))
                )
                .properties(height=320, width=600)
            )
            st.altair_chart(chart_price, use_container_width=True)

    with right:
        cal1, cal2 = st.columns([1, 1])
        with cal1:
            st.subheader(f"{month1.year}年 {month1.month}月")
            st.markdown(draw_calendar(month1), unsafe_allow_html=True)
        with cal2:
            st.subheader(f"{month2.year}年 {month2.month}月")
            st.markdown(draw_calendar(month2), unsafe_allow_html=True)


    # ───────────────────────────────

# --- 最終巡回時刻の直前 ---
st.markdown(
    "<div style='font-size:17px; color:#296;'>"
    "日付を選択すると推移グラフが表示されます"
    "</div>",
    unsafe_allow_html=True
)

# 最終巡回時刻表示
try:
    mtime = os.path.getmtime(CACHE_FILE)
    last_run = dt.datetime.fromtimestamp(mtime, pytz.timezone('Asia/Tokyo'))
    st.markdown(f"<p style='font-size:16px; color:gray;'>最終巡回時刻：{last_run:%Y-%m-%d %H:%M:%S}</p>", unsafe_allow_html=True)
except Exception:
    st.markdown("<p style='font-size:20px; color:gray;'>最終巡回時刻：取得できませんでした</p>", unsafe_allow_html=True)

# 注釈
st.markdown(
    """
    <div style='font-size:16px; color:#555;'>
    <strong>《注釈》</strong><br>
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
    """,
    unsafe_allow_html=True
)
