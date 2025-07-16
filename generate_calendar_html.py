# ファイル名: generate_calendar_html.py

import json
import calendar
import datetime

# 設定
JSON_PATH = "vacancy_price_cache.json"
HTML_PATH = "index.html"
TARGET_MONTHS = 2   # 表示するカレンダー月数

# 読み込み
with open(JSON_PATH, encoding="utf-8") as f:
    cache = json.load(f)

today = datetime.date.today()
year = today.year
month = today.month

def get_months(year, month, count):
    result = []
    for i in range(count):
        m = (month + i - 1) % 12 + 1
        y = year + (month + i - 1) // 12
        result.append((y, m))
    return result

def make_calendar_html(cache):
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>空室＆平均価格カレンダー</title>
<style>
body { background:#f8f8fb; font-family:sans-serif; }
.main { margin:40px auto; background:white; max-width:1100px; border-radius:36px; padding:48px 48px 48px 48px; box-shadow:0 4px 28px #ddd;}
h1 { margin-top:0; }
table.calendar { border-collapse:collapse; margin:24px 28px 24px 0; box-shadow:0 2px 10px #eee; border-radius:12px; overflow:hidden;}
.calendar th, .calendar td { width:92px; height:70px; text-align:center; vertical-align:top; border:1px solid #dde2ec; font-size:18px; background:#f5f7fb;}
.calendar th { background:#ecf1f8; color:#222; font-weight:700; font-size:20px;}
.calendar td.sunday { color:#df2a2a; }
.calendar td.saturday { color:#2866d9; }
.calendar td.holiday { background:#fff0f3; }
.calendar td.today { background:#b7f7d3; }
</style>
</head>
<body>
<div class="main">
<img src="バナー画像.png" style="height:54px;vertical-align:middle;margin-bottom:12px;" alt="バナー"><br>
<h1>空室＆平均価格カレンダー</h1>
<p style="color:#12b66a; font-size:18px;">最終巡回時刻：{now}</p>
""".format(now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for y, m in get_months(year, month, TARGET_MONTHS):
        html += f'<div style="display:inline-block;vertical-align:top;">'
        html += f"<h2 style='margin-bottom:8px;'>{y}年 {m}月</h2>"
        html += "<table class='calendar'>\n<tr>"
        for wd in "日月火水木金土":
            html += f"<th>{wd}</th>"
        html += "</tr>\n"

        cal = calendar.monthcalendar(y, m)
        for week in cal:
            html += "<tr>"
            for i, day in enumerate(week):
                key = f"{y}-{m:02d}-{day:02d}"
                cellcls = ""
                if i == 0: cellcls = "sunday"
                if i == 6: cellcls = "saturday"
                val = ""
                if day == 0:
                    html += "<td></td>"
                    continue
                if key in cache:
                    v = cache[key]
                    vcount = v.get("vacancy", 0)
                    avgp = v.get("avg_price", 0)
                    prev_v = v.get("previous_vacancy", 0)
                    prev_p = v.get("previous_avg_price", 0)
                    # 前日比
                    diff_v = vcount - prev_v
                    diff_p = avgp - prev_p
                    dstr = ""
                    if diff_v > 0:
                        dstr = f"<span style='color:#0074ff'>(+{diff_v})</span>"
                    elif diff_v < 0:
                        dstr = f"<span style='color:#df2a2a'>({diff_v})</span>"
                    # 価格上下アイコン
                    icon = ""
                    if diff_p > 0:
                        icon = "<span style='color:#e95d3d'>↑</span>"
                    elif diff_p < 0:
                        icon = "<span style='color:#357cf6'>↓</span>"
                    # メイン表示
                    val = f"{day}<br><span style='font-weight:700;'>{vcount}件 {dstr}</span><br>￥{avgp:,.0f} {icon}"
                else:
                    val = str(day)
                # 今日ハイライト
                today_str = today.strftime("%Y-%m-%d")
                if key == today_str:
                    cellcls += " today"
                html += f'<td class="{cellcls}">{val}</td>'
            html += "</tr>\n"
        html += "</table></div>\n"

    html += """
<p style="color:#12b66a;margin:30px 0 8px 0;font-size:17px;">
日付を選択すると推移グラフが表示されます（上部テキストボックスに日付を入力してください）
</p>
<ul style="font-size:15px;margin-top:0;">
<li>在庫数、平均価格は「なんば・心斎橋・天王寺・阿倍野・長居」エリアから抽出しています。</li>
<li>表示される「平均価格」は、楽天トラベル検索上位90施設の平均最低価格です。</li>
<li>空室数の <span style='color:#0074ff;'>(+N)</span> / <span style='color:#df2a2a;'>(-N)</span> は、前回巡回時点との在庫数の増減を示します。</li>
<li>平均価格の <span style='color:#e95d3d;'>↑</span> / <span style='color:#357cf6;'>↓</span> は、前回巡回時点との平均価格の上昇／下降を示します。</li>
</ul>
</div>
</body>
</html>
"""
    return html

# 実行
with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(make_calendar_html(cache))

print("index.html を生成しました！")
