import streamlit as st
import base64
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os, json, pytz, jpholiday
import altair as alt

st.set_page_config(page_title="【めちゃいいツール】ミナミエリア 空室＆平均価格カレンダー", layout="wide")

# --- PC/スマホ兼用 カスタムボタンCSS ---
st.markdown("""
<style>
.custom-button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 9px 0px;
    min-width: 80px;
    max-width: 220px;
    border: 1.8px solid #b9b9c9;
    border-radius: 10px;
    background: #fff;
    color: #1a1a1a;
    text-decoration: none;
    font-size: 1.0rem;
    font-weight: 500;
    margin: 0 10px 10px 0;
    box-shadow: 0 1.5px 7px rgba(0,0,0,0.03);
    transition: background 0.18s, color 0.18s, border 0.18s;
}
.custom-button, .custom-button:visited, .custom-button:active {
    text-decoration: none !important;
    color: #1a1a1a !important;
}
.custom-button .icon {
    font-size: 1.0em;
    margin-right: 11px;
    line-height: 1;
    display: inline-block;
}
.custom-button:hover {
    background: #f3f3fa;
    border-color: #e53939;
    color: #e53939 !important;
}
.nav-button-container, .graph-button-container {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
    width: 100%;
    margin-bottom: 1.6rem;
}
@media (max-width: 700px) {
    .nav-button-container, .graph-button-container {
        gap: 3.5px;
        margin-bottom: 0.65rem;
    }
    .custom-button {
        min-width: 56px !important;
        max-width: 90vw !important;
        padding: 4.2px 1 !important;
        font-size: 0.7rem !important;
    }
    .custom-button .icon {
        font-size: 1.09em !important;
        margin-right: 8px !important;
    }
    .calendar-wrapper td, .calendar-wrapper th {
        min-width: 32px !important; max-width: 38px !important;
        font-size: 9px !important; padding: 1px 0 1px 0 !important;
    }
    .calendar-wrapper td div, .calendar-wrapper td span {
        font-size: 9px !important; line-height: 1.05 !important;
    }
    .calendar-wrapper td > div > div:nth-child(2), .calendar-wrapper td > div > div:nth-child(3) {
        display: block !important; width: 100% !important; text-align: left !important;
    }
    .main-banner {
        width: 100% !important; max-width: 98vw !important; height: auto !important;
        display: block; margin: 0 auto;
    }
    .spike-flex-row { flex-direction: column !important; align-items: stretch !important; }
    .spike-chip { width: 100% !important; margin-bottom: 4px !important;}
}
</style>
""", unsafe_allow_html=True)

# --- バナー表示 ---
if os.path.exists("バナー画像3.png"):
    with open("バナー画像3.png", "rb") as f:
        img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    st.markdown(f"""
        <div style="width: 100%; background-color: #e4f0f4; padding: 5px 0; text-align: left;">
            <img class="main-banner" src="data:image/png;base64,{img_base64}" style="max-width: 1000px; height: auto;">
        </div><br>
    """, unsafe_allow_html=True)

APP_ID = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"
HISTORICAL_FILE = "historical_data.json"
EVENT_EXCEL = "event_data.xlsx"
SPIKE_HISTORY_FILE = "demand_spike_history.json"  # 履歴ファイル

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
    if not os.path.exists(filepath): return {}
    df = pd.read_excel(filepath).dropna(subset=["date", "icon", "name"])
    ev = {}
    for _, row in df.iterrows():
        key = pd.to_datetime(row["date"]).date().isoformat()
        ev.setdefault(key, []).append({"icon": row["icon"], "name": row["name"]})
    return ev

event_data = load_event_data_from_excel()
cache_data = load_json(CACHE_FILE)

# --- demand_spike_history.json 履歴読み込み＆表示 ---
# --- demand_spike_history.json 履歴読み込み ---
def load_spike_history(filepath=SPIKE_HISTORY_FILE):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def format_spike_chip(spike, up_date):
    price_txt = f"<span style='color:#d35400;'>単価{'↑' if spike['price_diff'] > 0 else '↓'} {abs(spike['price_diff']):,.0f}円</span>（{spike['price_ratio']*100:.1f}%）"
    vac_txt = f"<span style='color:#2980b9;'>客室{'減' if spike['vacancy_diff'] < 0 else '増'} {abs(spike['vacancy_diff'])}件</span>（{spike['vacancy_ratio']*100:.1f}%）"
    # MM/DD表記（検知日）
    up_md = dt.datetime.strptime(up_date, "%Y-%m-%d").strftime("%-m/%-d")
    # 右側必ず閉じカッコ
    return (
        f"<span class='spike-chip' style='background:transparent;border-radius:6px;padding:1px 7px 1px 0;display:inline-block;font-size:14.0px;line-height:1.4;margin-right:20px;margin-bottom:3px;'>"
        f"【{up_md} UP 該当日 {spike['spike_date']}　{price_txt}　{vac_txt}　"
        f"<span style='color:#555;font-size:11.5px;'>平均￥{spike['price']:,}／残{spike['vacancy']}</span>】"
        f"</span>"
    )

# --- 需要急騰履歴表示（横並び/色枠囲み/旧UI風） ---
spike_history = load_spike_history()
latest_n = 3   # 直近n日分
max_spikes = 10

sorted_dates = sorted(spike_history.keys(), reverse=True)[:latest_n]
chips = []
for up_date in sorted_dates:
    for spike in spike_history[up_date]:
        chips.append(format_spike_chip(spike, up_date))
chips = chips[:max_spikes]

if chips:
    st.markdown(
        f"""
        <div style="background:#fff8e6;border:2px solid #ffbf69;border-radius:10px;padding:15px 26px 13px 23px;max-width:900px;margin:18px 0 20px 0;">
          <div style="font-size:19px;color:#ff8000;font-weight:bold;letter-spacing:1.1px;margin-bottom:3px;">
            <span style="font-size:22px;vertical-align:middle;">🚀</span>
            <span style="margin-left:2px;">需要急騰検知日</span>
            <span style="font-size:13.5px;color:#c49029;font-weight:400;margin-left:13px;">（直近{latest_n}日分・最大{max_spikes}件）</span>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:0px 0px;align-items:center;margin-top:4px;">
            {"".join(chips)}
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )



# --- 以降はカレンダー・グラフ等の元のまま ---
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
    .calendar-wrapper td { padding-top: 30px !important; transition: background-color 0.2s ease; }
    .calendar-wrapper td:hover { background-color: #f5faff !important; cursor: pointer; }
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
            current_params = st.query_params.to_dict()
            new_params = {**current_params, "selected": iso}
            href = "?" + "&".join([f"{k}={v}" for k, v in new_params.items()])
            rec = cache_data.get(iso, {"vacancy": 0, "avg_price": 0})
            vac = rec["vacancy"]
            price = int(rec["avg_price"])
            diff_v = rec.get("vacancy_diff", 0)
            diff_p = rec.get("avg_price_diff", 0)
            vac_html = f'<div style="font-size:16px;font-weight:bold;">{vac}件'
            if diff_v > 0: vac_html += f'<span style="color:blue;font-size:12px;">（+{diff_v}）</span>'
            elif diff_v < 0: vac_html += f'<span style="color:red;font-size:12px;">（{diff_v}）</span>'
            vac_html += '</div>'
            price_html = f'<div style="font-size:16px;font-weight:bold;">￥{price:,}'
            if diff_p > 0: price_html += '<span style="color:red;"> ↑</span>'
            elif diff_p < 0: price_html += '<span style="color:blue;"> ↓</span>'
            price_html += '</div>'
            icon_html = f'<div style="position:absolute;top:2px;right:4px;font-size:16px;">{get_demand_icon(vac, price)}</div>' if current >= today else ''
            event_html = '<div style="font-size:12px;margin-top:4px;">' + "<br>".join(f'{e["icon"]} {e["name"]}' for e in event_data.get(iso, [])) + '</div>'
            html += (f'<td style="border:1px solid #aaa;padding:8px;background:{bg};position:relative;vertical-align:top;">'
                     f'<a href="{href}" target="_self" style="display:block;width:100%;height:100%;text-decoration:none;color:inherit;">'
                     f'{icon_html}<div style="position:absolute; top:4px; left:4px; font-size:14px; font-weight:bold;">{current.day}</div>'
                     f'{vac_html}{price_html}{event_html}</a></td>')
        html += '</tr>'
    html += '</tbody></table></div>'
    return html

# --- カレンダー描画ロジック ---
today = dt.date.today()
params = st.query_params
selected_date = params.get("selected")
if isinstance(selected_date, list): selected_date = selected_date[0]

if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0
MAX_MONTH_OFFSET = 12

nav_left, nav_center, nav_right = st.columns([3, 4, 3])
with nav_center:
    st.markdown('<div class="nav-button-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ 前月", key="btn_prev"):
            st.session_state.month_offset = max(st.session_state.month_offset - 1, -MAX_MONTH_OFFSET)
    with col2:
        if st.button("📅 当月", key="btn_today"):
            st.session_state.month_offset = 0
    with col3:
        if st.button("➡️ 次月", key="btn_next"):
            st.session_state.month_offset = min(st.session_state.month_offset + 1, MAX_MONTH_OFFSET)
    st.markdown('</div>', unsafe_allow_html=True)

base_month = today.replace(day=1) + relativedelta(months=st.session_state.month_offset)
month1 = base_month
month2 = base_month + relativedelta(months=1)

def load_historical_data():
    if os.path.exists(HISTORICAL_FILE):
        with open(HISTORICAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
historical_data = load_historical_data()

if "show_graph" not in st.session_state:
    st.session_state["show_graph"] = True

if selected_date and st.session_state["show_graph"]:
    left, right = st.columns([3, 7])
    with left:
        prev_day = (pd.to_datetime(selected_date).date() - dt.timedelta(days=1)).isoformat()
        next_day = (pd.to_datetime(selected_date).date() + dt.timedelta(days=1)).isoformat()

        st.markdown('<div class="graph-button-container">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("❌ グラフを閉じる", key="btn_close"):
                st.query_params.clear()
                st.session_state["show_graph"] = False
                st.rerun()
        with col2:
            if st.button("＜前日", key="btn_prev_day"):
                st.query_params["selected"] = prev_day
                st.rerun()
        with col3:
            if st.button("翌日＞", key="btn_next_day"):
                st.query_params["selected"] = next_day
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f"#### {selected_date} の在庫・価格推移")

        if (selected_date not in historical_data or not historical_data[selected_date] or len(historical_data[selected_date]) == 0):
            st.info("この日付の履歴データがありません")
        else:
            df = pd.DataFrame(sorted(({"取得日": hist_date, "在庫数": rec["vacancy"], "平均単価": rec["avg_price"]}
                                    for hist_date, rec in historical_data[selected_date].items()), key=lambda x: x["取得日"]))
            df["取得日"] = pd.to_datetime(df["取得日"])
            if df.empty:
                st.info("この日付の履歴データがありません")
            else:
                st.write("##### 在庫数")
                chart_vac = (alt.Chart(df).mark_line(point=True)
                             .encode(x=alt.X("取得日:T", axis=alt.Axis(title=None, format="%m/%d")),
                                     y=alt.Y("在庫数:Q", axis=alt.Axis(title=None), scale=alt.Scale(domain=[0, 350])))
                             .properties(height=320, width=600))
                st.altair_chart(chart_vac, use_container_width=True)
                st.write("##### 平均単価 (円)")
                chart_price = (alt.Chart(df).mark_line(point=True, color="#e15759")
                               .encode(x=alt.X("取得日:T", axis=alt.Axis(title=None, format="%m/%d")),
                                       y=alt.Y("平均単価:Q", axis=alt.Axis(title=None), scale=alt.Scale(domain=[0, 35000])))
                               .properties(height=320, width=600))
                st.altair_chart(chart_price, use_container_width=True)
    with right:
        cal1, cal2 = st.columns(2)
        with cal1:
            st.subheader(f"{month1.year}年 {month1.month}月")
            st.markdown(draw_calendar(month1), unsafe_allow_html=True)
        with cal2:
            st.subheader(f"{month2.year}年 {month2.month}月")
            st.markdown(draw_calendar(month2), unsafe_allow_html=True)
else:
    cal1, cal2 = st.columns(2)
    with cal1:
        st.subheader(f"{month1.year}年 {month1.month}月")
        st.markdown(draw_calendar(month1), unsafe_allow_html=True)
    with cal2:
        st.subheader(f"{month2.year}年 {month2.month}月")
        st.markdown(draw_calendar(month2), unsafe_allow_html=True)

# --- カレンダー下部の案内など ---
st.markdown("<hr>", unsafe_allow_html=True)
if not selected_date:
    st.markdown("<div style='font-size:17px; color:#296;'>日付を選択すると推移グラフが表示されます</div>", unsafe_allow_html=True)
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
        ・🔥1：残室 ≤250 または 価格 ≥25,000円<br>
        ・🔥2：残室 ≤200 または 価格 ≥30,000円<br>
        ・🔥3：残室 ≤150 または 価格 ≥35,000円<br>
        ・🔥4：残室 ≤100 または 価格 ≥40,000円<br>
        ・🔥5：残室 ≤70 または 価格 ≥50,000円<br>
    </div>
    """, unsafe_allow_html=True)
