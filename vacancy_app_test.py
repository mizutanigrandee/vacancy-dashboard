import streamlit as st
import base64
import datetime as dt
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd
import os, json, pytz, jpholiday
import altair as alt

st.set_page_config(
    page_title="テスト版【めちゃいいツール】ミナミエリア 空室＆平均価格カレンダー",
    layout="wide",
)

# ───────────────────────────────────────── CSS
st.markdown(
    """
<style>
/* ========== 共通 ========== */
.nav-bar{
    display:flex;justify-content:center;align-items:center;
    gap:14px;margin:4px 0 12px;
}
.nav-btn{
    border:1px solid #ccc;border-radius:6px;padding:4px 10px;
    text-decoration:none;background:#fff;font-size:1.05rem;
}
.icon{font-size:1.2rem;margin-right:4px;}
.text{}

/* ---------- スマホ専用 ---------- */
@media (max-width:700px){
    .calendar-wrapper td,.calendar-wrapper th{
        min-width:32px!important;max-width:38px!important;
        font-size:9px!important;padding:1px 0!important;
    }
    .calendar-wrapper td div,
    .calendar-wrapper td span{font-size:9px!important;line-height:1.05!important;}
    .calendar-wrapper td>div>div:nth-child(2),
    .calendar-wrapper td>div>div:nth-child(3){
        display:block!important;width:100%!important;text-align:left!important;
    }
    .main-banner{width:100%!important;max-width:98vw!important;height:auto!important;display:block;margin:0 auto;}
    /* 👉 スマホ：アイコン非表示・テキストのみ */
    .icon{display:none!important;}
}

/* ---------- PC 専用 ---------- */
@media (min-width:701px){
    .nav-btn{min-width:80px!important;}
}
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────── クエリパラメータ（月送り）
nav_action = st.query_params.get("nav")
MAX_MONTH_OFFSET = 12
if nav_action == "prev":
    st.session_state.month_offset = max(
        st.session_state.month_offset - 1, -MAX_MONTH_OFFSET
    )
    st.query_params.pop("nav")
    st.rerun()
elif nav_action == "today":
    st.session_state.month_offset = 0
    st.query_params.pop("nav")
    st.rerun()
elif nav_action == "next":
    st.session_state.month_offset = min(
        st.session_state.month_offset + 1, MAX_MONTH_OFFSET
    )
    st.query_params.pop("nav")
    st.rerun()

# ─────────────────────────────── バナー
if os.path.exists("バナー画像3.png"):
    with open("バナー画像3.png", "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <div style="width:100%;background:#e4f0f4;padding:5px 0;text-align:left;">
          <img class="main-banner" src="data:image/png;base64,{img_b64}" style="max-width:1000px;height:auto;">
        </div><br>""",
        unsafe_allow_html=True,
    )

APP_ID = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE = "vacancy_price_cache.json"
HIST_FILE = "historical_data.json"
EVENT_EXCEL = "event_data.xlsx"

# ─────────────────────────────── 祝日テーブル
def generate_holidays(months=13):
    today = dt.date.today()
    return {
        today + dt.timedelta(days=i)
        for i in range(months * 31)
        if jpholiday.is_holiday(today + dt.timedelta(days=i))
    }


HOLIDAYS = generate_holidays()

# ─────────────────────────────── ユーティリティ
def load_json(p):
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_event_data_from_excel(fp=EVENT_EXCEL):
    if not os.path.exists(fp):
        return {}
    df = pd.read_excel(fp).dropna(subset=["date", "icon", "name"])
    ev = {}
    for _, r in df.iterrows():
        key = pd.to_datetime(r["date"]).date().isoformat()
        ev.setdefault(key, []).append({"icon": r["icon"], "name": r["name"]})
    return ev


event_data = load_event_data_from_excel()
cache_data = load_json(CACHE_FILE)

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

# ─────────────────────────────── カレンダー描画
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(calendar.SUNDAY)
    weeks = cal.monthdatescalendar(month_date.year, month_date.month)
    today = dt.date.today()
    html = (
        '<div class="calendar-wrapper"><table style="border-collapse:collapse;'
        'width:100%;table-layout:fixed;text-align:center;">'
    )
    html += """
    <style>
    .calendar-wrapper td{padding-top:30px!important;transition:background-color .2s}
    .calendar-wrapper td:hover{background:#f5faff!important;cursor:pointer;}
    </style>"""
    html += '<thead style="background:#f4f4f4;color:#333;font-weight:bold;"><tr>'
    html += "".join(
        f'<th style="border:1px solid #aaa;padding:4px;">{d}</th>'
        for d in "日月火水木金土"
    )
    html += "</tr></thead><tbody>"
    for week in weeks:
        html += "<tr>"
        for current in week:
            if current.month != month_date.month:
                html += '<td style="border:1px solid #aaa;padding:8px;background:#fff;"></td>'
                continue
            bg = (
                "#ddd"
                if current < today
                else (
                    "#ffecec"
                    if (current in HOLIDAYS or current.weekday() == 6)
                    else ("#e0f7ff" if current.weekday() == 5 else "#fff")
                )
            )
            iso = current.isoformat()
            rec = cache_data.get(iso, {"vacancy": 0, "avg_price": 0})
            vac, price = rec["vacancy"], int(rec["avg_price"])
            diff_v, diff_p = rec.get("vacancy_diff", 0), rec.get("avg_price_diff", 0)

            vac_html = f'<div style="font-size:16px;font-weight:bold;">{vac}件'
            if diff_v > 0:
                vac_html += f'<span style="color:blue;font-size:12px;">（+{diff_v}）</span>'
            elif diff_v < 0:
                vac_html += f'<span style="color:red;font-size:12px;">（{diff_v}）</span>'
            vac_html += "</div>"

            price_html = f'<div style="font-size:16px;font-weight:bold;">￥{price:,}'
            if diff_p > 0:
                price_html += '<span style="color:red;"> ↑</span>'
            elif diff_p < 0:
                price_html += '<span style="color:blue;"> ↓</span>'
            price_html += "</div>"

            icon_html = (
                f'<div style="position:absolute;top:2px;right:4px;font-size:16px;">{get_demand_icon(vac,price)}</div>'
                if current >= today
                else ""
            )
            event_html = (
                '<div style="font-size:12px;margin-top:4px;">'
                + "<br>".join(
                    f'{e["icon"]} {e["name"]}' for e in event_data.get(iso, [])
                )
                + "</div>"
            )
            html += (
                f'<td style="border:1px solid #aaa;padding:8px;background:{bg};position:relative;vertical-align:top;">'
                f'<a href="?selected={iso}" target="_self" style="display:block;width:100%;height:100%;text-decoration:none;color:inherit;">'
                f'{icon_html}'
                f'<div style="position:absolute;top:4px;left:4px;font-size:14px;font-weight:bold;">{current.day}</div>'
                f"{vac_html}{price_html}{event_html}"
                "</a></td>"
            )
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

# ─────────────────────────────── 画面描画
today = dt.date.today()
selected_date = st.query_params.get("selected")
if isinstance(selected_date, list):
    selected_date = selected_date[0]

if "month_offset" not in st.session_state:
    st.session_state.month_offset = 0

# ===== 月送りナビ =================================================
st.markdown(
    """
<div class="nav-bar">
  <a href="?nav=prev"  class="nav-btn"><span class="icon">⬅️</span><span class="text">前月</span></a>
  <a href="?nav=today" class="nav-btn"><span class="icon">📅</span><span class="text">当月</span></a>
  <a href="?nav=next"  class="nav-btn"><span class="icon">➡️</span><span class="text">次月</span></a>
</div>
""",
    unsafe_allow_html=True,
)

base_month = today.replace(day=1) + relativedelta(
    months=st.session_state.month_offset
)
month1, month2 = base_month, base_month + relativedelta(months=1)

# ─────────────────────────────── 履歴データ
def load_hist():
    return load_json(HIST_FILE)


hist = load_hist()

if "show_graph" not in st.session_state:
    st.session_state["show_graph"] = True

if selected_date and st.session_state["show_graph"]:
    left, right = st.columns([3, 7])

    # ---------- 左側（グラフ＋ナビ）
    with left:
        prev_dt = (
            pd.to_datetime(selected_date).date() - dt.timedelta(days=1)
        ).isoformat()
        next_dt = (
            pd.to_datetime(selected_date).date() + dt.timedelta(days=1)
        ).isoformat()

        st.markdown(
            f"""
        <div class="nav-bar" style="justify-content:flex-start;">
          <a href="?selected={prev_dt}" class="nav-btn"><span class="text">＜前日</span></a>
          <a href="?selected={next_dt}" class="nav-btn"><span class="text">翌日＞</span></a>
          <a href="."                     class="nav-btn"><span class="text">❌ 閉じる</span></a>
        </div>""",
            unsafe_allow_html=True,
        )

        st.markdown(f"#### {selected_date} の在庫・価格推移")

        if not hist.get(selected_date):
            st.info("この日付の履歴データがありません")
        else:
            df = pd.DataFrame(
                sorted(
                    (
                        {
                            "取得日": h_date,
                            "在庫数": r["vacancy"],
                            "平均単価": r["avg_price"],
                        }
                        for h_date, r in hist[selected_date].items()
                    ),
                    key=lambda x: x["取得日"],
                )
            )
            df["取得日"] = pd.to_datetime(df["取得日"])
            if df.empty:
                st.info("この日付の履歴データがありません")
            else:
                st.write("##### 在庫数")
                st.altair_chart(
                    alt.Chart(df)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("取得日:T", axis=alt.Axis(title=None, format="%m/%d")),
                        y=alt.Y(
                            "在庫数:Q",
                            axis=alt.Axis(title=None),
                            scale=alt.Scale(domain=[0, 350]),
                        ),
                    )
                    .properties(height=320, width=600),
                    use_container_width=True,
                )

                st.write("##### 平均単価 (円)")
                st.altair_chart(
                    alt.Chart(df)
                    .mark_line(point=True, color="#e15759")
                    .encode(
                        x=alt.X("取得日:T", axis=alt.Axis(title=None, format="%m/%d")),
                        y=alt.Y(
                            "平均単価:Q",
                            axis=alt.Axis(title=None),
                            scale=alt.Scale(domain=[0, 35000]),
                        ),
                    )
                    .properties(height=320, width=600),
                    use_container_width=True,
                )

    # ---------- 右側（カレンダー）
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

# ─────────────────────────────── フッター
st.markdown(
    "<div style='font-size:17px;color:#296;'>日付を選択すると推移グラフが表示されます</div>",
    unsafe_allow_html=True,
)

try:
    last_run = dt.datetime.fromtimestamp(
        os.path.getmtime(CACHE_FILE), pytz.timezone("Asia/Tokyo")
    )
    st.markdown(
        f"<p style='font-size:16px;color:gray;'>最終巡回時刻：{last_run:%Y-%m-%d %H:%M:%S}</p>",
        unsafe_allow_html=True,
    )
except Exception:
    st.markdown(
        "<p style='font-size:16px;color:gray;'>最終巡回時刻：取得できませんでした</p>",
        unsafe_allow_html=True,
    )

st.markdown(
    """
<div style='font-size:16px;color:#555;'><strong>《注釈》</strong><br>
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
</div>""",
    unsafe_allow_html=True,
)
