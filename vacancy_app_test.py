# vacancy_app_test.py  – 2025-06-21 mobile-nav fix
import streamlit as st
import base64, datetime as dt, calendar, os, json, pytz
from dateutil.relativedelta import relativedelta
import pandas as pd, jpholiday, altair as alt

st.set_page_config(
    page_title="テスト版【めちゃいいツール】ミナミエリア 空室＆平均価格カレンダー",
    layout="wide",
)

# ────────────────────────── CSS
st.markdown(
    """
<style>
/* ===== 共通ボタン ===== */
.nav-btn{
    display:inline-flex;align-items:center;gap:4px;
    border:1px solid #ccc;border-radius:6px;background:#fff;
    padding:4px 10px;font-size:1.05rem;cursor:pointer;
    user-select:none;
}
.icon{font-size:1.2rem;}
/* ===== ボタン行 ===== */
.nav-bar{display:flex;justify-content:center;gap:16px;margin:6px 0 14px;}
/* ===== スマホ専用 ===== */
@media (max-width:700px){
    .icon{display:none;}                 /* 文字だけにする */
    .nav-bar{gap:10px;}
    .calendar-wrapper td,.calendar-wrapper th{
        min-width:32px!important;max-width:38px!important;font-size:9px!important;padding:1px 0!important;
    }
    .calendar-wrapper td div,
    .calendar-wrapper td span{font-size:9px!important;line-height:1.05!important;}
    .calendar-wrapper td>div>div:nth-child(2),
    .calendar-wrapper td>div>div:nth-child(3){display:block!important;width:100%!important;text-align:left!important;}
    .main-banner{width:100%!important;max-width:98vw!important;height:auto!important;display:block;margin:0 auto;}
}
</style>
""",
    unsafe_allow_html=True,
)

# ────────────────────────── クエリ（月送り）
MAX_MONTH_OFFSET = 12
nav_action = st.query_params.get("nav")
if nav_action == "prev":
    st.session_state.month_offset = max(st.session_state.month_offset - 1, -MAX_MONTH_OFFSET)
    st.query_params.pop("nav"); st.rerun()
elif nav_action == "today":
    st.session_state.month_offset = 0; st.query_params.pop("nav"); st.rerun()
elif nav_action == "next":
    st.session_state.month_offset = min(st.session_state.month_offset + 1, MAX_MONTH_OFFSET)
    st.query_params.pop("nav"); st.rerun()

# ────────────────────────── バナー
if os.path.exists("バナー画像3.png"):
    with open("バナー画像3.png", "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""<div style="width:100%;background:#e4f0f4;padding:5px 0;">
              <img class="main-banner" src="data:image/png;base64,{b64}" style="max-width:1000px;height:auto;">
            </div><br>""",
        unsafe_allow_html=True,
    )

APP_ID            = st.secrets["RAKUTEN_APP_ID"]
CACHE_FILE        = "vacancy_price_cache.json"
HIST_FILE         = "historical_data.json"
EVENT_EXCEL       = "event_data.xlsx"

# ────────────────────────── 祝日セット
def gen_holidays(months=13):
    today = dt.date.today()
    return {today + dt.timedelta(days=i) for i in range(months * 31) if jpholiday.is_holiday(today + dt.timedelta(days=i))}

HOLIDAYS = gen_holidays()

# ────────────────────────── データ読み込み
def load_json(p): return json.load(open(p, "r", encoding="utf-8")) if os.path.exists(p) else {}

def load_events(fp=EVENT_EXCEL):
    if not os.path.exists(fp): return {}
    df = pd.read_excel(fp).dropna(subset=["date", "icon", "name"])
    ev = {}
    for _, r in df.iterrows():
        key = pd.to_datetime(r["date"]).date().isoformat()
        ev.setdefault(key, []).append({"icon": r["icon"], "name": r["name"]})
    return ev

cache_data  = load_json(CACHE_FILE)
event_data  = load_events()
hist_data   = load_json(HIST_FILE)

# ────────────────────────── 需要シンボル
def demand_icon(vac, price):
    if vac <= 70 or price >= 50000: return "🔥5"
    if vac <= 100 or price >= 40000: return "🔥4"
    if vac <= 150 or price >= 35000: return "🔥3"
    if vac <= 200 or price >= 30000: return "🔥2"
    if vac <= 250 or price >= 25000: return "🔥1"
    return ""

# ────────────────────────── カレンダー HTML
def draw_calendar(month_date: dt.date) -> str:
    cal = calendar.Calendar(calendar.SUNDAY)
    weeks = cal.monthdatescalendar(month_date.year, month_date.month)
    today = dt.date.today()
    html = '<div class="calendar-wrapper"><table style="border-collapse:collapse;width:100%;table-layout:fixed;text-align:center;">'
    html += '<thead style="background:#f4f4f4;font-weight:bold;"><tr>'
    html += ''.join(f'<th style="border:1px solid #aaa;padding:4px;">{d}</th>' for d in "日月火水木金土") + "</tr></thead><tbody>"
    for wk in weeks:
        html += "<tr>"
        for cur in wk:
            if cur.month != month_date.month:
                html += '<td style="border:1px solid #aaa;padding:8px;background:#fff;"></td>'; continue
            iso = cur.isoformat()
            rec = cache_data.get(iso, {"vacancy":0,"avg_price":0})
            vac, price = rec["vacancy"], int(rec["avg_price"])
            dv, dp     = rec.get("vacancy_diff",0), rec.get("avg_price_diff",0)
            bg = "#ddd" if cur < today else ("#ffecec" if (cur in HOLIDAYS or cur.weekday()==6) else ("#e0f7ff" if cur.weekday()==5 else "#fff"))
            v_html = f'<div style="font-weight:bold;">{vac}件'
            if dv>0: v_html += f'<span style="color:blue;font-size:12px;">（+{dv}）</span>'
            elif dv<0: v_html += f'<span style="color:red;font-size:12px;">（{dv}）</span>'
            v_html += '</div>'
            p_html = f'<div style="font-weight:bold;">￥{price:,}'
            if dp>0: p_html += '<span style="color:red;"> ↑</span>'
            elif dp<0: p_html += '<span style="color:blue;"> ↓</span>'
            p_html += '</div>'
            ev_html = '<div style="font-size:12px;margin-top:4px;">' + "<br>".join(f'{e["icon"]} {e["name"]}' for e in event_data.get(iso,[])) + '</div>'
            ico_html = f'<div style="position:absolute;top:2px;right:4px;">{demand_icon(vac,price)}</div>' if cur>=today else ''
            html += (f'<td style="border:1px solid #aaa;padding:8px;background:{bg};position:relative;vertical-align:top;">'
                     f'<a href="?selected={iso}" style="display:block;width:100%;height:100%;text-decoration:none;color:inherit;">'
                     f'{ico_html}<div style="position:absolute;top:4px;left:4px;font-weight:bold;">{cur.day}</div>'
                     f'{v_html}{p_html}{ev_html}</a></td>')
        html += "</tr>"
    return html + "</tbody></table></div>"

# ────────────────────────── ステート
if "month_offset" not in st.session_state: st.session_state.month_offset = 0
if "show_graph"  not in st.session_state: st.session_state.show_graph  = True

today = dt.date.today()
selected = st.query_params.get("selected")
if isinstance(selected, list): selected = selected[0]

# ────────────────────────── 月送りナビ（同一タブ遷移）
st.markdown(
    """
<div class="nav-bar">
  <button class="nav-btn" onclick="window.location.search='?nav=prev'"><span class="icon">⬅️</span>前月</button>
  <button class="nav-btn" onclick="window.location.search='?nav=today'"><span class="icon">📅</span>当月</button>
  <button class="nav-btn" onclick="window.location.search='?nav=next'"><span class="icon">➡️</span>次月</button>
</div>""",
    unsafe_allow_html=True,
)

base_month = today.replace(day=1) + relativedelta(months=st.session_state.month_offset)
month1, month2 = base_month, base_month + relativedelta(months=1)

# ────────────────────────── グラフ表示 or カレンダーのみ
if selected and st.session_state.show_graph:
    l_col, r_col = st.columns([3,7], gap="small")
    # ----- 左：ナビ＋グラフ
    with l_col:
        prev_d = (pd.to_datetime(selected).date() - dt.timedelta(days=1)).isoformat()
        next_d = (pd.to_datetime(selected).date() + dt.timedelta(days=1)).isoformat()
        st.markdown(
            f"""
        <div class="nav-bar" style="justify-content:flex-start;">
          <button class="nav-btn" onclick="window.location.search='?selected={prev_d}'">＜前日</button>
          <button class="nav-btn" onclick="window.location.search='?selected={next_d}'">翌日＞</button>
          <button class="nav-btn" onclick="window.location.href='.'">❌ 閉じる</button>
        </div>""",
            unsafe_allow_html=True,
        )
        st.markdown(f"#### {selected} の在庫・価格推移")
        if not hist_data.get(selected):
            st.info("この日付の履歴データがありません")
        else:
            df = pd.DataFrame(sorted(
                ({"取得日":d,"在庫数":r["vacancy"],"平均単価":r["avg_price"]} for d,r in hist_data[selected].items()),
                key=lambda x: x["取得日"]
            ))
            df["取得日"] = pd.to_datetime(df["取得日"])
            if df.empty:
                st.info("この日付の履歴データがありません")
            else:
                st.write("##### 在庫数")
                st.altair_chart(
                    alt.Chart(df).mark_line(point=True).encode(
                        x=alt.X("取得日:T", axis=alt.Axis(format="%m/%d", title=None)),
                        y=alt.Y("在庫数:Q", axis=alt.Axis(title=None), scale=alt.Scale(domain=[0,350]))
                    ).properties(height=320,width=600), use_container_width=True
                )
                st.write("##### 平均単価 (円)")
                st.altair_chart(
                    alt.Chart(df).mark_line(point=True,color="#e15759").encode(
                        x=alt.X("取得日:T", axis=alt.Axis(format="%m/%d", title=None)),
                        y=alt.Y("平均単価:Q", axis=alt.Axis(title=None), scale=alt.Scale(domain=[0,35000]))
                    ).properties(height=320,width=600), use_container_width=True
                )
    # ----- 右：2 か月カレンダー
    with r_col:
        c1, c2 = st.columns(2, gap="small")
        with c1:
            st.subheader(f"{month1.year}年 {month1.month}月")
            st.markdown(draw_calendar(month1), unsafe_allow_html=True)
        with c2:
            st.subheader(f"{month2.year}年 {month2.month}月")
            st.markdown(draw_calendar(month2), unsafe_allow_html=True)
else:
    # ── カレンダーのみ
    c1, c2 = st.columns(2, gap="small")
    with c1:
        st.subheader(f"{month1.year}年 {month1.month}月")
        st.markdown(draw_calendar(month1), unsafe_allow_html=True)
    with c2:
        st.subheader(f"{month2.year}年 {month2.month}月")
        st.markdown(draw_calendar(month2), unsafe_allow_html=True)

# ────────────────────────── フッター
st.markdown(
    "<div style='font-size:17px;color:#296;'>日付を選択すると推移グラフが表示されます</div>",
    unsafe_allow_html=True,
)
try:
    last = dt.datetime.fromtimestamp(os.path.getmtime(CACHE_FILE), pytz.timezone("Asia/Tokyo"))
    st.markdown(
        f"<p style='font-size:16px;color:gray;'>最終巡回時刻：{last:%Y-%m-%d %H:%M:%S}</p>",
        unsafe_allow_html=True,
    )
except Exception:
    st.markdown("<p style='font-size:16px;color:gray;'>最終巡回時刻：取得できませんでした</p>", unsafe_allow_html=True)

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
