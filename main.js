// main.js
const VACANCY_URL = "vacancy_price_cache.json";
const HISTORICAL_URL = "historical_data.json";
const EVENT_URL = "event_data.json"; // 必要に応じて "event_data.xlsx"→json化

const MONTH_LABEL = ["日", "月", "火", "水", "木", "金", "土"];
const MAX_MONTH_OFFSET = 12; // 前後何ヶ月分まで月送り

let vacancyData = {}, eventData = {}, historicalData = {};
let monthOffset = 0, selectedDate = null;

window.onload = async function() {
  await loadAllData();
  renderAll();
};

async function loadAllData() {
  // vacancy/priceデータ
  vacancyData = await fetch(VACANCY_URL).then(r=>r.json());
  // イベントデータ(json推奨)
  eventData = {};
  try {
    eventData = await fetch(EVENT_URL).then(r=>r.json());
  } catch {}
  // 履歴データ
  historicalData = {};
  try {
    historicalData = await fetch(HISTORICAL_URL).then(r=>r.json());
  } catch {}
}

function renderAll() {
  renderLastUpdated();
  renderCalendarNav();
  renderCalendars();
  renderGraph();
}

// 1. 最終更新
function renderLastUpdated() {
  let d = 0;
  try { d = vacancyData && Object.keys(vacancyData).sort().reverse()[0]; }
  catch { }
  const dom = document.getElementById("last-updated");
  if (dom && d) dom.textContent = `最終更新日：${d}`;
}

// 2. ナビ（前月・当月・次月）
function renderCalendarNav() {
  const nav = document.getElementById("nav");
  nav.innerHTML = "";
  const makeBtn = (label, cb, disabled) => {
    const btn = document.createElement("button");
    btn.textContent = label;
    if (disabled) btn.disabled = true;
    btn.onclick = cb;
    return btn;
  };
  nav.appendChild(makeBtn("⬅️ 前月", ()=>{monthOffset=Math.max(monthOffset-1,-MAX_MONTH_OFFSET);renderAll();}, monthOffset<=-MAX_MONTH_OFFSET));
  nav.appendChild(makeBtn("📅 当月", ()=>{monthOffset=0;renderAll();}, monthOffset==0));
  nav.appendChild(makeBtn("➡️ 次月", ()=>{monthOffset=Math.min(monthOffset+1,MAX_MONTH_OFFSET);renderAll();}, monthOffset>=MAX_MONTH_OFFSET));
}

// 3. カレンダー2枚
function renderCalendars() {
  const today = new Date();
  today.setHours(0,0,0,0);
  let base = new Date(today.getFullYear(), today.getMonth()+monthOffset, 1);

  for(let k=1;k<=2;k++) {
    const id = "calendar"+k;
    const dom = document.getElementById(id);
    let dt = new Date(base.getFullYear(), base.getMonth()+(k-1), 1);
    dom.innerHTML = renderOneCalendar(dt, today);
  }
}

// カレンダー描画
function renderOneCalendar(monthDate, today) {
  const y = monthDate.getFullYear(), m = monthDate.getMonth();
  let html = `<div class="calendar-title">${y}年 ${m+1}月</div>`;
  html += `<table class="calendar"><thead><tr>`;
  for(let i=0;i<7;i++) html+=`<th class="${i==0?'sun':''}${i==6?'sat':''}">${MONTH_LABEL[i]}</th>`;
  html += "</tr></thead><tbody>";

  // 月カレンダーの全日
  let cal = [];
  let firstDay = new Date(y, m, 1);
  let lastDay = new Date(y, m+1, 0);
  let w = (firstDay.getDay()+7)%7;
  let d0 = new Date(y, m, 1-w);
  for(let i=0;i<42;i++) cal.push(new Date(d0.getFullYear(), d0.getMonth(), d0.getDate()+i));

  for(let wi=0;wi<6;wi++) {
    html+="<tr>";
    for(let di=0;di<7;di++) {
      let d = cal[wi*7+di];
      const iso = d.toISOString().slice(0,10);
      let out = (d.getMonth()!=m);
      let hol = (d.getDay()==0)||(d.getDay()==6)||isHoliday(iso);
      let tdCls = [];
      if(out) tdCls.push("out");
      if(!out && hol) tdCls.push("hol");
      if(d.getTime()===today.getTime()) tdCls.push("today");
      if(d.getDay()==0) tdCls.push("sun");
      if(d.getDay()==6) tdCls.push("sat");

      html+=`<td class="${tdCls.join(" ")}" data-date="${iso}" onclick="onDateClick('${iso}')">`;
      // 日付
      html+=`<div class="daynum">${d.getDate()}</div>`;
      // 在庫・価格・前日比
      if(!out) {
        const rec = vacancyData[iso]||{};
        html+=`<div><b>${rec.vacancy||0}件</b>`;
        if(rec.vacancy_diff>0) html+=`<span class="diff pos">（+${rec.vacancy_diff}）</span>`;
        if(rec.vacancy_diff<0) html+=`<span class="diff neg">（${rec.vacancy_diff}）</span>`;
        html+=`</div>`;
        html+=`<div><b>￥${(rec.avg_price||0).toLocaleString()}</b>`;
        if(rec.avg_price_diff>0) html+=`<span class="price-up">↑</span>`;
        if(rec.avg_price_diff<0) html+=`<span class="price-down">↓</span>`;
        html+=`</div>`;
        // 需要シンボル🔥
        html+=getDemandIcon(rec.vacancy||0, rec.avg_price||0);
        // イベント注記
        if(eventData[iso]) {
          for(const ev of eventData[iso]) {
            if(ev.icon && ev.name)
              html+=`<div class="event-${getEventType(ev.icon)}">${ev.icon} ${ev.name}</div>`;
          }
        }
      }
      html+=`</td>`;
    }
    html+="</tr>";
  }
  html+="</tbody></table>";
  return html;
}

// カレンダーセル用イベント種別
function getEventType(icon) {
  if(icon.includes("🔴")) return "kyocera";
  if(icon.includes("🔵")) return "yannar";
  if(icon.includes("★")) return "other";
  return "other";
}

// 日付クリック→グラフ
function onDateClick(iso) {
  selectedDate = iso;
  renderGraph();
  window.scrollTo({top:document.getElementById("graph-container").offsetTop-40,behavior:"smooth"});
}
window.onDateClick = onDateClick;

// 祝日判定（JS用: 将来カスタマイズ可能。デフォは日曜土曜色分け。）
function isHoliday(iso) {
  // JS単体では祝日計算不可（本番は祝日JSONやAPIで判定可）
  // 例: if(JPHOLIDAYS.includes(iso)) return true;
  // 仮：日曜土曜のみ
  const d = new Date(iso);
  return (d.getDay()==0||d.getDay()==6);
}

// 需要シンボル
function getDemandIcon(vac, price) {
  if(vac<=70||price>=50000) return `<span class="fire fire5">🔥5</span>`;
  if(vac<=100||price>=40000) return `<span class="fire fire4">🔥4</span>`;
  if(vac<=150||price>=35000) return `<span class="fire fire3">🔥3</span>`;
  if(vac<=200||price>=30000) return `<span class="fire fire2">🔥2</span>`;
  if(vac<=250||price>=25000) return `<span class="fire fire1">🔥1</span>`;
  return "";
}

// グラフ
function renderGraph() {
  const dom = document.getElementById("graph-container");
  dom.innerHTML = "";
  if(!selectedDate) return;
  // ボタン群
  let html = `<div style="display:flex;gap:20px;margin-bottom:12px;">`;
  html += `<button onclick="closeGraph()">❌ グラフを閉じる</button>`;
  html += `<button onclick="moveGraph(-1)">＜前日</button>`;
  html += `<button onclick="moveGraph(1)">翌日＞</button>`;
  html += `</div>`;
  html += `<h3 style="margin:0 0 12px 0;">${selectedDate} の在庫・価格推移</h3>`;
  html += `<canvas id="day-graph" width="670" height="360"></canvas>`;
  dom.innerHTML = html;

  // 履歴データ
  const hist = (historicalData[selectedDate]||{});
  const dates = Object.keys(hist).sort();
  if(!dates.length) {
    dom.innerHTML += "<div style='color:#148;'>この日付の履歴データがありません</div>";
    return;
  }
  const vac = dates.map(d=>hist[d].vacancy);
  const price = dates.map(d=>hist[d].avg_price);
  // グラフ
  setTimeout(()=>{
    new Chart(document.getElementById("day-graph"),{
      type:"line",
      data:{
        labels:dates,
        datasets:[
          {label:"在庫数",data:vac,yAxisID:"y1",borderColor:"#2a7fc1",backgroundColor:"#2a7fc120",tension:0.2},
          {label:"平均単価(円)",data:price,yAxisID:"y2",borderColor:"#e15759",backgroundColor:"#e1575918",tension:0.2}
        ]
      },
      options:{
        responsive:true,
        plugins:{legend:{position:"top"}},
        scales:{
          y1:{type:"linear",position:"left",title:{display:true,text:"在庫数"},min:0,max:350},
          y2:{type:"linear",position:"right",title:{display:true,text:"平均単価"},min:0,max:50000,grid:{drawOnChartArea:false}}
        }
      }
    });
  },50);
}
window.closeGraph = function(){ selectedDate=null; renderGraph(); }
window.moveGraph = function(dir){
  if(!selectedDate) return;
  const d = new Date(selectedDate);
  d.setDate(d.getDate()+dir);
  const iso = d.toISOString().slice(0,10);
  selectedDate = iso;
  renderGraph();
};
