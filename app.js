// ========== データ & 祝日設定 ==========
const DATA_PATH  = "./vacancy_price_cache.json";
const PREV_PATH  = "./vacancy_price_cache_previous.json";
const EVENT_PATH = "./event_data.json";
const HIST_PATH  = "./historical_data.json";
const HOLIDAYS   = [ /* 省略 */ ];

// グローバル
let calendarData = {}, prevData = {}, eventData = {}, historicalData = {};
let currentYM = [], selectedDate = null;

// 起動時
window.onload = async()=>{
  await loadAll();
  initMonth();
  if(!selectedDate) selectedDate = todayIso();
  renderPage();
  updateLastUpdate();
  setupMonthButtons();
};

// ヘルパー
const todayIso = ()=> new Date().toISOString().slice(0,10);
async function loadJson(path){
  try{ let r=await fetch(path); if(!r.ok) return {}; return r.json(); }
  catch(e){ return {}; }
}
async function loadAll(){
  calendarData   = await loadJson(DATA_PATH);
  prevData       = await loadJson(PREV_PATH);
  eventData      = await loadJson(EVENT_PATH);
  historicalData = await loadJson(HIST_PATH);
}
function isHoliday(d){ return HOLIDAYS.includes(d); }

// 月切替
function setupMonthButtons(){
  document.getElementById("prevMonthBtn").onclick = ()=>{ shiftMonth(-1); renderPage(); };
  document.getElementById("currentMonthBtn").onclick = ()=>{ initMonth(); renderPage(); };
  document.getElementById("nextMonthBtn").onclick = ()=>{ shiftMonth(1); renderPage(); };
}
function initMonth(){
  let t=new Date(), y=t.getFullYear(), m=t.getMonth()+1;
  currentYM = [[y,m], m===12?[y+1,1]:[y,m+1]];
}
function shiftMonth(d){
  let [y,m]=currentYM[0];
  m+=d; if(m<1){ y--; m=12;} else if(m>12){ y++; m=1;}
  currentYM = [[y,m], m===12?[y+1,1]:[y,m+1]];
}

// 全体描画
function renderPage(){
  document.querySelector(".calendar-main").innerHTML = `
    <div class="main-flexbox">
      <div class="graph-side" id="graph-container"></div>
      <div class="calendar-container" id="calendar-container"></div>
    </div>`;
  renderGraph(selectedDate);
  renderCalendars();
}

// カレンダー描画
function renderCalendars(){
  let cont = document.getElementById("calendar-container");
  cont.innerHTML="";
  for(let [y,m] of currentYM) cont.appendChild(renderMonth(y,m));
}
function renderMonth(y,m){
  let wrap=document.createElement("div"), day=1;
  wrap.className="month-calendar";
  wrap.innerHTML=`<div class="month-header">${y}年${m}月</div>`;
  let grid=document.createElement("div"); grid.className="calendar-grid";
  // 曜日
  ["日","月","火","水","木","金","土"].forEach(d=>{
    let c=document.createElement("div");
    c.className="calendar-cell calendar-dow"; c.textContent=d;
    grid.appendChild(c);
  });
  // 空セル
  let first=new Date(y,m-1,1).getDay(), last=new Date(y,m,0).getDate();
  for(let i=0;i<first;i++){ let e=document.createElement("div"); e.className="calendar-cell"; grid.appendChild(e);}
  // 日付セル
  for(let d=1;d<=last;d++){
    let iso=`${y}-${String(m).padStart(2,0)}-${String(d).padStart(2,0)}`,
        cell=document.createElement("div");
    cell.className="calendar-cell"; cell.dataset.date=iso;
    // 背景色
    let wd=(grid.children.length)%7;
    if(isHoliday(iso)) cell.classList.add("holiday-bg");
    else if(wd===0) cell.classList.add("sunday-bg");
    else if(wd===6) cell.classList.add("saturday-bg");
    // データ取得
    let cur=calendarData[iso]||{}, prv=prevData[iso]||{};
    // 差分：JSONにあればそれ、なければ計算
    let dv = (typeof cur.vacancy_diff==="number")? cur.vacancy_diff : (cur.vacancy||0)-(prv.vacancy||0);
    let dp = (typeof cur.avg_price_diff==="number")? cur.avg_price_diff : Math.round((cur.avg_price||0)-(prv.avg_price||0));
    // 表示用
    let stock = cur.vacancy!=null? `${cur.vacancy}件` : "-";
    let price = cur.avg_price!=null? cur.avg_price.toLocaleString() : "-";
    // 需要シンボルLv
    let lvl=0;
    if(cur.vacancy!=null&&cur.avg_price!=null){
      if(cur.vacancy<=70||cur.avg_price>=50000) lvl=5;
      else if(cur.vacancy<=100||cur.avg_price>=40000) lvl=4;
      else if(cur.vacancy<=150||cur.avg_price>=35000) lvl=3;
      else if(cur.vacancy<=200||cur.avg_price>=30000) lvl=2;
      else if(cur.vacancy<=250||cur.avg_price>=25000) lvl=1;
    }
    let badge=lvl?`<div class="cell-demand-badge lv${lvl}">🔥${lvl}</div>`:"";
    // イベント
    let evs=(eventData[iso]||[]).map(e=>`<div class="cell-event">${e.icon} ${e.name}</div>`).join("");
    // HTML
    cell.innerHTML=`
      <div class="cell-date">${d}</div>
      <div class="cell-main">
        <span class="cell-vacancy">${stock}</span>
        <span class="cell-vacancy-diff ${dv>0?"plus":dv<0?"minus":"flat"}">
          ${dv>0?"+"+dv:dv<0?dv:"±0"}
        </span>
      </div>
      <div class="cell-price">
        ￥${price}
        <span class="cell-price-diff ${dp>0?"up":dp<0?"down":"flat"}">
          ${dp>0?"↑":dp<0?"↓":"→"}
        </span>
      </div>
      ${badge}
      <div class="cell-event-list">${evs}</div>
    `;
    cell.onclick=()=>{ selectedDate=iso; renderPage(); };
    grid.appendChild(cell);
  }
  wrap.appendChild(grid);
  return wrap;
}

// グラフ描画
function renderGraph(dateStr){
  let gc=document.getElementById("graph-container");
  if(!dateStr){ gc.innerHTML=""; return; }
  gc.innerHTML=`
    <div class="graph-btns">
      <button onclick="closeGraph()">✗ グラフを閉じる</button>
      <button onclick="nav(-1)">< 前日</button>
      <button onclick="nav(1)">翌日 ></button>
    </div>
    <h3>${dateStr} の在庫・価格推移</h3>
    <canvas id="stockChart" width="420" height="180"></canvas>
    <canvas id="priceChart" width="420" height="180"></canvas>
  `;
  // 履歴取得
  let hist = historicalData[dateStr]||{}, labels=[], sv=[], pv=[];
  Object.keys(hist).sort().forEach(d=>{
    labels.push(d);
    sv.push(hist[d].vacancy);
    pv.push(hist[d].avg_price);
  });
  // ナビ用
  let all=Object.keys(historicalData).sort(), idx=all.indexOf(dateStr);
  window.nav = diff=>{ let ni=idx+diff; if(ni>=0&&ni<all.length){ selectedDate=all[ni]; renderPage(); }};
  window.closeGraph = ()=>{ selectedDate=todayIso(); renderPage(); };

  // Chart.js
  if(window.sc) window.sc.destroy();
  if(window.pc) window.pc.destroy();
  if(labels.length){
    window.sc = new Chart(
      document.getElementById("stockChart").getContext("2d"),
      {
        type:"line",
        data:{labels, datasets:[{data:sv, fill:false, borderColor:"#2196f3", pointRadius:2}]},
        options:{plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true,title:{display:true,text:"在庫数"}}, x:{title:{display:true,text:"日付"}}}}
      }
    );
    window.pc = new Chart(
      document.getElementById("priceChart").getContext("2d"),
      {
        type:"line",
        data:{labels, datasets:[{data:pv, fill:false, borderColor:"#e91e63", pointRadius:2}]},
        options:{plugins:{legend:{display:false}}, scales:{y:{beginAtZero:false,title:{display:true,text:"平均価格（円）"}}, x:{title:{display:true,text:"日付"}}}}
      }
    );
  }
}

// 最終更新
function updateLastUpdate(){
  let e=document.getElementById("last-update"), d=new Date(), p=n=>String(n).padStart(2,"0");
  e.textContent=`最終更新日時：${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
