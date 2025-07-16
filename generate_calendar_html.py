import json
import datetime
import calendar

# --- 祝日リスト（2025年の一部例：本番は全祝日を用意推奨）---
HOLIDAYS = [
    "2025-01-01", "2025-01-13", "2025-02-11", "2025-02-23",
    "2025-03-20", "2025-04-29", "2025-05-03", "2025-05-04",
    "2025-05-05", "2025-07-21", "2025-08-11", "2025-09-15",
    "2025-09-23", "2025-10-13", "2025-11-03", "2025-11-23",
    "2025-12-23"
]

def is_holiday(date_str):
    return date_str in HOLIDAYS

# --- データ読込 ---
with open("vacancy_price_cache.json", encoding="utf-8") as f:
    data = json.load(f)

today = datetime.date.today()
# 1か月目・2か月目を取得
first_month = today.replace(day=1)
second_month = (first_month + datetime.timedelta(days=32)).replace(day=1)

months = [first_month, second_month]

# --- HTML組立 ---
def make_calendar(month_date):
    year, month = month_date.year, month_date.month
    month_str = f"{year}年 {month}月"
    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり
    html = f"""<div class="calendar-wrap"><div class="calendar-title">{month_str}</div>
    <table class="calendar">
      <tr>
        <th class="sun">日</th><th>月</th><th>火</th><th>水</th><th>木</th><th>金</th><th class="sat">土</th>
      </tr>
    """
    for week in cal.monthdatescalendar(year, month):
        html += "<tr>"
        for d in week:
            day_str = d.strftime("%Y-%m-%d")
            is_this_month = (d.month == month)
            is_hol = is_holiday(day_str)
            # 曜日クラス
            w = d.weekday()
            td_cls = []
            if w == 6: td_cls.append("sun")
            if w == 5: td_cls.append("sat")
            if is_hol: td_cls.append("hol")
            if d == today: td_cls.append("today")
            if not is_this_month: td_cls.append("out")
            td_cls = " ".join(td_cls)
            html += f'<td class="{td_cls}">'
            if is_this_month:
                cell = f'<div class="daynum">{d.day}</div>'
                v = data.get(day_str)
                if v:
                    # 在庫
                    vac = v.get("vacancy", "-")
                    prev_vac = v.get("previous_vacancy", "")
                    vac_diff = ""
                    if prev_vac != "" and isinstance(prev_vac, int):
                        diff = vac - prev_vac
                        vac_diff = f'<span class="diff {"pos" if diff>0 else "neg"}">{"+" if diff>0 else ""}{diff}</span>' if diff != 0 else ""
                    # 価格
                    price = v.get("avg_price", "-")
                    prev_price = v.get("previous_avg_price", "")
                    price_icon = ""
                    if prev_price != "" and isinstance(prev_price, (int, float)):
                        diff = price - prev_price
                        if diff > 0:
                            price_icon = '<span class="price-up">↑</span>'
                        elif diff < 0:
                            price_icon = '<span class="price-down">↓</span>'
                    # 仮：イベントシンボル（例として手動で特定日を装飾）
                    event = ""
                    if day_str == "2025-07-14":
                        event = '<span class="event-kyocera">🔴SEVENTEEN</span>'
                    elif day_str == "2025-07-27":
                        event = '<span class="event-other">★TWICE</span>'
                    # 需要シンボル
                    fire = ""
                    if vac != "-" and isinstance(vac, int):
                        if vac <= 70 or price >= 50000:
                            fire = '<span class="fire fire5">🔥5</span>'
                        elif vac <= 100 or price >= 40000:
                            fire = '<span class="fire fire4">🔥4</span>'
                        elif vac <= 150 or price >= 35000:
                            fire = '<span class="fire fire3">🔥3</span>'
                        elif vac <= 200 or price >= 30000:
                            fire = '<span class="fire fire2">🔥2</span>'
                        elif vac <= 250 or price >= 25000:
                            fire = '<span class="fire fire1">🔥1</span>'
                    cell += f"<div>{vac}件{vac_diff}</div><div>¥{price:,}{price_icon}</div>{fire}{event}"
                html += cell
            html += "</td>"
        html += "</tr>"
    html += "</table></div>"
    return html

# --- HTML全体 ---
calendar_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>空室＆平均価格カレンダー（本番）</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body {{ background:#f7f8fa; margin:0; font-family:'Noto Sans JP',sans-serif; }}
.main {{ max-width:1500px; margin:30px auto 40px auto; background:#fff; border-radius:36px; box-shadow:0 4px 32px #d9e2ef99; padding:36px 24px 36px 48px; }}
h1 {{ margin:0 0 8px 0; font-size:40px; }}
h2 {{ margin:8px 0 0 0; font-size:22px; color:#444; }}
.banner {{ width:380px; margin-bottom:12px; }}
.flex {{ display:flex; gap:36px; flex-wrap:wrap; }}
.calendar-wrap {{ flex:1 1 48%; min-width:370px; }}
.calendar-title {{ font-size:28px; margin-bottom:4px; font-weight:700; color:#222; }}
table.calendar {{ border-collapse:collapse; border-radius:16px; overflow:hidden; margin-bottom:14px; background:#f5f7fb; }}
.calendar th, .calendar td {{ width:84px; height:80px; border:1px solid #e0e4ef; text-align:center; font-size:19px; vertical-align:top; background:#fff; padding:0; position:relative; }}
.calendar th.sun, .calendar td.sun {{ color:#e1000a; }}
.calendar th.sat, .calendar td.sat {{ color:#1b6ace; }}
.calendar td.hol {{ background:#fff5f5; }}
.calendar td.today {{ background:#bdf7d3; }}
.calendar td.out {{ background:#f5f7fb; color:#bbb; }}
.daynum {{ font-weight:bold; font-size:22px; margin-bottom:2px; }}
.diff.pos {{ color:#2176d2; font-size:14px; margin-left:2px; }}
.diff.neg {{ color:#e94343; font-size:14px; margin-left:2px; }}
.price-up {{ color:#e03e3e; font-size:17px; margin-left:3px; }}
.price-down {{ color:#208ad8; font-size:17px; margin-left:3px; }}
.fire {{ font-size:18px; margin-left:4px; }}
.fire1 {{ color:#ff9800; }}
.fire2 {{ color:#ff5722; }}
.fire3 {{ color:#ff1744; }}
.fire4 {{ color:#c51162; }}
.fire5 {{ color:#6d00c4; font-weight:bold; }}
.event-kyocera {{ display:block; color:#b10000; font-size:14px; margin-top:2px; }}
.event-other {{ display:block; color:#222; font-size:13px; }}
@media (max-width:1100px) {{ .flex {{ flex-direction:column; }} .calendar-wrap {{ min-width:320px; }} }}
</style>
</head>
<body>
<div class="main">
    <img src="バナー画像3.png" class="banner" alt="バナー画像">
    <h1>空室＆平均価格カレンダー</h1>
    <div style="color:#2baf71;font-size:18px; margin-bottom:7px;">最終巡回時刻：{today:%Y-%m-%d %H:%M:%S}</div>
    <div class="flex">
        {make_calendar(months[0])}
        {make_calendar(months[1])}
    </div>
    <h2>日付を選択すると推移グラフが表示されます（※HTML静的化ではグラフ省略）</h2>
    <div style="margin:16px 0 8px 0; color:#222;">
        <b>《注釈》</b><br>
        ・在庫数、平均価格は「なんば・心斎橋・天王寺・阿倍野・長居」エリアから抽出しています。<br>
        ・表示される「平均価格」は、楽天トラベル検索上位90施設の平均最安値です。<br>
        ・空室数の（<span class="diff pos">+N</span>／<span class="diff neg">-N</span>）は、前回巡回時点との在庫数の増減を示します。<br>
        ・平均価格の <span class="price-up">↑</span>／<span class="price-down">↓</span>は、前回巡回時点との平均価格の上昇／下降を示します。<br>
        ・会場アイコン：<span class="event-kyocera">🔴京セラドーム</span>／<span style="color:#1976d2;">🔵ヤンマースタジアム</span>／<span class="event-other">★その他会場</span><br>
        ・炎マーク（需要シンボル）の内訳：<br>
        <span class="fire fire1">🔥1</span>：残室≤250 or 価格≥25,000円　
        <span class="fire fire2">🔥2</span>：残室≤200 or 価格≥30,000円　
        <span class="fire fire3">🔥3</span>：残室≤150 or 価格≥35,000円　
        <span class="fire fire4">🔥4</span>：残室≤100 or 価格≥40,000円　
        <span class="fire fire5">🔥5</span>：残室≤70 or 価格≥50,000円
    </div>
</div>
</body>
</html>
"""

# index.htmlへ保存
with open("index.html", "w", encoding="utf-8") as f:
    f.write(calendar_html)

print("index.html（本番仕様）を生成しました！")
