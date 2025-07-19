import os
import json
import calendar
import pandas as pd
import datetime as dt

# ----- ファイルパス・基本設定 -----
CACHE_FILE = "vacancy_price_cache.json"
HISTORICAL_FILE = "historical_data.json"
EVENT_FILE = "event_data.xlsx"
OUT_HTML = "index.html"
BANNER_IMG = "バナー画像3.png"

# ----- 祝日判定 -----
try:
    import jpholiday
except ImportError:
    # Github Actions等でjpholiday未導入時
    os.system("pip install jpholiday")
    import jpholiday

# ----- データロード -----
def load_json(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_event_data(path):
    if not os.path.exists(path):
        return {}
    df = pd.read_excel(path).dropna(subset=["date", "icon", "name"])
    ev = {}
    for _, row in df.iterrows():
        key = pd.to_datetime(row["date"]).date().isoformat()
        ev.setdefault(key, []).append({"icon": row["icon"], "name": row["name"]})
    return ev

cache_data = load_json(CACHE_FILE)
historical_data = load_json(HISTORICAL_FILE)
event_data = load_event_data(EVENT_FILE)

# ----- バナー画像（base64） -----
def banner_base64():
    if not os.path.exists(BANNER_IMG): return ""
    import base64
    with open(BANNER_IMG, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
    return ""

banner64 = banner_base64()

# ----- 日付リスト生成 -----
def get_holidays(year, month):
    hol = set()
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        date = dt.date(year, month, d)
        if jpholiday.is_holiday(date):
            hol.add(d)
    return hol

# ----- 需要シンボル -----
def get_demand_icon(vac, price):
    if vac <= 70 or price >= 50000: return "🔥5"
    if vac <= 100 or price >= 40000: return "🔥4"
    if vac <= 150 or price >= 35000: return "🔥3"
    if vac <= 200 or price >= 30000: return "🔥2"
    if vac <= 250 or price >= 25000: return "🔥1"
    return ""

# ----- カレンダー1枚描画 -----
def draw_calendar(year, month, today, selected, holidays, cache_data, event_data):
    cal = calendar.Calendar(calendar.SUNDAY)
    weeks = cal.monthdatescalendar(year, month)
    html = f'''
    <div class="calendar-wrapper"><table>
    <thead><tr>
    <th class="sun">日</th><th>月</th><th>火</th><th>水</th><th>木</th><th>金</th><th class="sat">土</th>
    </tr></thead><tbody>
    '''
    for week in weeks:
        html += "<tr>"
        for day in week:
            style, txtcolor = "", ""
            # 月外日
            if day.month != month:
                html += '<td class="empty"></td>'
                continue
            dkey = day.isoformat()
            is_holiday = day.day in holidays
            is_sun = day.weekday() == 6
            is_sat = day.weekday() == 5

            # 色設定
            if is_holiday or is_sun:
                style = "background:#ffecec;"
                txtcolor = "color:#000;"
            elif is_sat:
                style = "background:#e0f7ff;"
                txtcolor = "color:#000;"
            else:
                style = "background:#fff;"
                txtcolor = "color:#000;"

            cellclass = ""
            if is_sun: cellclass = "sun"
            elif is_sat: cellclass = "sat"
            elif is_holiday: cellclass = "hol"

            # 選択日ハイライト
            if dkey == selected:
                style += "box-shadow:0 0 0 3px #ff9999;"

            rec = cache_data.get(dkey, {"vacancy": 0, "avg_price": 0})
            vac = rec.get("vacancy", 0)
            price = int(rec.get("avg_price", 0))
            diff_v = rec.get("vacancy_diff", 0)
            diff_p = rec.get("avg_price_diff", 0)

            # デマンド
            demand = get_demand_icon(vac, price)
            # イベント
            events = event_data.get(dkey, [])
            event_html = "<br>".join(f'{e["icon"]} {e["name"]}' for e in events)

            # cell
            html += f'''
            <td class="{cellclass}" style="{style}{txtcolor};position:relative;">
                <div class="daynum">{day.day}</div>
                <div class="vac">在庫: {vac}件{'<span class="diff_up">（+%d）</span>'%diff_v if diff_v>0 else (f'<span class="diff_down">（{diff_v}）</span>' if diff_v<0 else '')}</div>
                <div class="price">￥{price:,}{'<span class="arrow_up"> ↑</span>' if diff_p>0 else ('<span class="arrow_down"> ↓</span>' if diff_p<0 else '')}</div>
                <div class="demand">{demand}</div>
                <div class="event">{event_html}</div>
            </td>
            '''
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

# ----- グラフ（SVG2枚、在庫・価格） -----
def draw_graph(selected, historical_data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import io, base64
    if selected not in historical_data or not historical_data[selected]:
        return "<div>この日付の履歴データがありません</div>"
    df = pd.DataFrame([
        {"取得日": hist_date, "在庫数": rec["vacancy"], "平均単価": rec["avg_price"]}
        for hist_date, rec in historical_data[selected].items()
    ])
    df = df.sort_values("取得日")
    # 在庫グラフ
    buf1 = io.BytesIO()
    plt.figure(figsize=(5,2.2))
    plt.plot(pd.to_datetime(df["取得日"]), df["在庫数"], marker="o")
    plt.title("在庫数の推移")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(buf1, format="png")
    plt.close()
    g1 = base64.b64encode(buf1.getvalue()).decode()
    # 価格グラフ
    buf2 = io.BytesIO()
    plt.figure(figsize=(5,2.2))
    plt.plot(pd.to_datetime(df["取得日"]), df["平均単価"], marker="o", color="#e15759")
    plt.title("平均単価（円）の推移")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(buf2, format="png")
    plt.close()
    g2 = base64.b64encode(buf2.getvalue()).decode()
    return f'''
    <div class="graph">
      <img src="data:image/png;base64,{g1}" width="97%">
      <img src="data:image/png;base64,{g2}" width="97%">
    </div>
    '''

# ----- メインHTML生成 -----
def main():
    today = dt.date.today()
    # 選択日（初期値は当日 or 1日目）
    selected = today.isoformat()
    # 月送り（2か月分を表示）
    base_month = today.replace(day=1)
    months = [(base_month.year, base_month.month),
              ((base_month + pd.DateOffset(months=1)).year, (base_month + pd.DateOffset(months=1)).month)]
    holidays = [get_holidays(y, m) for y, m in months]

    # 最終更新
    try:
        mtime = os.path.getmtime(CACHE_FILE)
        last_run = dt.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    except:
        last_run = "取得できませんでした"

    # --- HTML出力 ---
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(f'''
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8" />
<title>ミナミエリア 空室＆平均価格カレンダー【本番版】</title>
<style>
body {{ font-family: 'Segoe UI', 'Hiragino Sans', 'Meiryo', sans-serif; background:#f5f5f8; }}
.main-banner {{
    width:98%; max-width:1800px; display:block; margin:32px auto 18px auto; background:#e4f0f4; border-radius:30px;
}}
.calendar-wrapper table {{
    border-collapse:collapse; width:100%; table-layout:fixed; background:#fff; border-radius:24px; box-shadow:0 4px 16px #eee;
    margin-bottom:18px;
}}
.calendar-wrapper th, .calendar-wrapper td {{
    font-size:16px; padding:6px 0 6px 0; border:1px solid #ccc; text-align:center; min-width:48px; position:relative;
}}
.calendar-wrapper th.sun, .calendar-wrapper td.sun {{ color:#d9534f; }}
.calendar-wrapper th.sat, .calendar-wrapper td.sat {{ color:#2176d3; }}
.calendar-wrapper td.hol {{ color:#d9534f; }}
.calendar-wrapper td.empty {{ background:#f9f9fb; border:none; }}
.daynum {{ font-size:20px; font-weight:bold; margin-bottom:2px; }}
.vac, .price, .event {{ font-size:15px; line-height:1.25; }}
.demand {{ position:absolute; bottom:2px; right:8px; font-size:21px; }}
.diff_up {{ color:blue; font-size:12px; }}
.diff_down {{ color:red; font-size:12px; }}
.arrow_up {{ color:red; font-size:16px; font-weight:bold; }}
.arrow_down {{ color:blue; font-size:16px; font-weight:bold; }}
.graph img {{ margin: 14px auto; display: block; border-radius:10px; box-shadow:0 2px 8px #e7e7f7; background:#fff; }}
@media (max-width: 900px) {{
    .main-banner {{ max-width:95vw; }}
    .calendar-wrapper th, .calendar-wrapper td {{ font-size:13px; min-width:24px; }}
    .daynum {{ font-size:14px; }}
    .vac, .price, .event {{ font-size:12px; }}
    .demand {{ font-size:15px; right:2px; }}
}}
</style>
</head>
<body>
<div style="width:100%;text-align:left;">
    <img class="main-banner" src="data:image/png;base64,{banner64}" />
</div>
<div style="margin:8px 0 18px 0; color:#555; font-size:18px;">
    <b>最終更新日：</b>{last_run}
</div>
<div style="display:flex;gap:30px;flex-wrap:wrap;">
  <div style="width:48%;min-width:340px;">
    <div style="font-size:22px;font-weight:bold;margin-bottom:4px;">{months[0][0]}年{months[0][1]}月</div>
    {draw_calendar(months[0][0], months[0][1], today, selected, holidays[0], cache_data, event_data)}
  </div>
  <div style="width:48%;min-width:340px;">
    <div style="font-size:22px;font-weight:bold;margin-bottom:4px;">{months[1][0]}年{months[1][1]}月</div>
    {draw_calendar(months[1][0], months[1][1], today, selected, holidays[1], cache_data, event_data)}
  </div>
</div>
<div style="margin:32px 0 0 0;">
  <div style="font-size:20px;font-weight:bold;color:#2176d3;margin-bottom:2px;">日付を選択すると推移グラフが表示されます（今後拡張）</div>
  {draw_graph(selected, historical_data)}
</div>
<hr>
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
</body></html>
        ''')

if __name__ == "__main__":
    main()
