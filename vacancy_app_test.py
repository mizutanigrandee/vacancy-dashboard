import streamlit as st
import base64
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os, json, pytz, jpholiday
import altair as alt

st.set_page_config(page_title="テスト版【めちゃいいツール】ミナミエリア 空室＆平均価格カレンダー", layout="wide")

# --- 変更点①：ボタンレイアウト制御用のCSSを追加 ---
st.markdown("""
<style>
/* 共通ボタンスタイル */
.custom-button {
    display: inline-block;
    padding: 8px 12px;
    border: 1px solid #c9c9d1;
    border-radius: 8px;
    background-color: white;
    color: #0c0c0d;
    text-decoration: none;
    text-align: center;
    font-size: 1rem;
    font-weight: 400;
    transition: background-color 0.2s, color 0.2s;
}
.custom-button:hover {
    border-color: #ff4b4b;
    color: #ff4b4b;
}

/* スマホ表示 (max-width: 700px) の時のボタンコンテナ設定 */
@media (max-width: 700px) {
    .nav-button-container, .graph-button-container {
        display: flex;
        justify-content: space-between; /* ボタンを均等配置 */
        align-items: center;
        width: 100%;
        margin-bottom: 1rem;
        gap: 5px; /* ボタン間の隙間 */
    }
    .nav-button-container .custom-button, .graph-button-container .custom-button {
        flex-grow: 1; /* ボタンを均等に広げる */
    }

    /* 以下は既存のスマホ用CSS */
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
}
</style>
""", unsafe_allow_html=True)

# --- クエリ対応 (URLのパラメータを読み取る) ---
params = st.query_params
nav_action = params.get("nav")
if "month_offset" not in st.session_state: st.session_state.month_offset = 0
MAX_MONTH_OFFSET = 12

if nav_action:
    if nav_action == "prev":
        st.session_state.month_offset = max(st.session_state.month_offset - 1, -MAX_MONTH_OFFSET)
    elif nav_action == "today":
        st.session_state.month_offset = 0
    elif nav_action == "next":
        st.session_state.month_offset = min(st.session_state.month_offset + 1, MAX_MONTH_OFFSET)
    
    # 処理後にクエリパラメータを削除してURLをクリーンにする
    new_params = {k: v for k, v in params.items() if k != 'nav'}
    st.query_params.from_dict(new_params)
    st.rerun()


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
            
            # グラフ表示中はクエリパラメータを維持し、それ以外はクリア
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
selected_date = params.get("selected")
if isinstance(selected_date, list): selected_date = selected_date[0]

# --- 変更点②：PC/スマホ対応のHTMLボタンに置き換え ---
# PCでは中央寄せ、スマホでは横並びになる
nav_html = """
<div class="nav-button-container">
    <a href="?nav=prev" target="_self" class="custom-button">⬅️ 前月</a>
    <a href="?nav=today" target="_self" class="custom-button">📅 当月</a>
    <a href="?nav=next" target="_self" class="custom-button">➡️ 次月</a>
</div>
"""
# PC表示では中央のカラムに配置して元のレイアウトを再現
nav_left, nav_center, nav_right = st.columns([3, 4, 3])
with nav_center:
    st.markdown(nav_html, unsafe_allow_html=True)

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
    # グラフとカレンダーのレイアウト
    left, right = st.columns([3, 7])
    with left:
        # --- 変更点③：グラフ操作ボタンもHTMLボタンに置き換え ---
        prev_day = (pd.to_datetime(selected_date).date() - dt.timedelta(days=1)).isoformat()
        next_day = (pd.to_datetime(selected_date).date() + dt.timedelta(days=1)).isoformat()
        
        # 閉じるボタンはselectedパラメータを削除したURLに遷移する
        close_href = "?" + "&".join([f"{k}={v}" for k, v in params.items() if k != 'selected'])
        if close_href == "?": close_href = "."

        graph_nav_html = f"""
        <div class="graph-button-container">
            <a href="{close_href}" target="_self" class="custom-button">❌ 閉じる</a>
            <a href="?selected={prev_day}" target="_self" class="custom-button">＜前日</a>
            <a href="?selected={next_day}" target="_self" class="custom-button">翌日＞</a>
        </div>
        """
        st.markdown(graph_nav_html, unsafe_allow_html=True)
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
                                     y=alt.Y("在庫数:Q", axis=alt.Axis(title=None), scale=alt.Scale(zero=False)))
                             .properties(height=280))
                st.altair_chart(chart_vac, use_container_width=True)
                
                st.write("##### 平均単価 (円)")
                chart_price = (alt.Chart(df).mark_line(point=True, color="#e15759")
                               .encode(x=alt.X("取得日:T", axis=alt.Axis(title=None, format="%m/%d")),
                                       y=alt.Y("平均単価:Q", axis=alt.Axis(title=None), scale=alt.Scale(zero=False)))
                               .properties(height=280))
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
