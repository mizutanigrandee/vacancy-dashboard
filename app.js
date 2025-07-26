// ========== 設定 & 祝日 & データパス ========== 
const DATA_PATH = "./vacancy_price_cache.json";
const PREV_DATA_PATH = "./vacancy_price_cache_previous.json";
const EVENT_PATH = "./event_data.json";
const HISTORICAL_PATH = "./historical_data.json";
const HOLIDAYS = [ /* 略 */ ];

// グローバル
let calendarData = {}, prevCalendarData = {}, eventData = {}, historicalData = {};
let currentYearMonth = [], selectedDate = null;

// 初期化
window.onload = async function() {
  await loadAllData();
  initMonth();
  if (!selectedDate) selectedDate = todayIso();
  renderPage();
  updateLastUpdate();
  setupMonthButtons();
};

function todayIso() {
  return new Date().toISOString().slice(0,10);
}
async function loadAllData() {
  calendarData = await fetchJson(DATA_PATH);
  prevCalendarData = await fetchJson(PREV_DATA_PATH);
  eventData = await fetchJson(EVENT_PATH);
  historicalData = await fetchJson(HISTORICAL_PATH);
}
async function fetchJson(path) {
  try { let r = await fetch(path); if(!r.ok) return {}; return r.json(); }
  catch(e){ return {}; }
}
function isHoliday(d){ return HOLIDAYS.includes(d); }

// 月切替設定
function setupMonthButtons() {
  document.getElementById("prevMonthBtn").onclick = ()=>{ shiftMonth(-1); renderPage(); };
  document.getElementById("currentMonthBtn").onclick = ()=>{ initMonth(); renderPage(); };
  document.getElementById("nextMonthBtn").onclick = ()=>{ shiftMonth(1); renderPage(); };
}
function initMonth() {
  let t=new Date(), y=t.getFullYear(), m=t.getMonth()+1;
  currentYearMonth = [[y,m], m===12?[y+1,1]:[y,m+1]];
}
function shiftMonth(diff) {
  let [y,m]=currentYearMonth[0];
  m+=diff;
  if(m<1){ y--; m=12; } else if(m>12){ y++; m=1; }
  currentYearMonth = [[y,m], m===12?[y+1,1]:[y,m+1]];
}

// 描画
function renderPage() {
  document.querySelector(".calendar-main").innerHTML = `
    <div class="main-flexbox">
      <div class="graph-side" id="graph-container"></div>
      <div class="calendar-container" id="calendar-container"></div>
    </div>`;
  renderGraph(selectedDate);
  renderCalendars();
  document.querySelectorAll('.calendar-cell').forEach(c=>{
    if(c.dataset.date===selectedDate) c.classList.add('selected');
  });
}

function renderCalendars() {
  let cont = document.getElementById("calendar-container");
  cont.innerHTML = "";
  for(let [y,m] of currentYearMonth){
    cont.appendChild(renderMonthCalendar(y,m));
  }
}

function renderMonthCalendar(year,month) {
  let wrapper=document.createElement("div");
  wrapper.className="month-calendar";
  let hdr=document.createElement("div");
  hdr.className="month-header";
  hdr.textContent=`${year}年${month}月`;
  wrapper.appendChild(hdr);

  let grid=document.createElement("div");
  grid.className="calendar-grid";
  for(let d of ["日","月","火","水","木","金","土"]){
    let c=document.createElement("div");
    c.className="calendar-cell calendar-dow";
    c.textContent=d;
    grid.appendChild(c);
  }

  let first=new Date(year,month-1,1).getDay();
  let last=new Date(year,month,0).getDate();
  let count=0;
  // 空セル
  for(let i=0;i<first;i++){ let e=document.createElement("div"); e.className="calendar-cell"; grid.appendChild(e); count++; }
  // 各日
  for(let d=1;d<=last;d++){
    let iso=`${year}-${String(month).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
    let c=document.createElement("div");
    c.className="calendar-cell";
    c.dataset.date=iso;
    // 背景
    let wd=(count)%7;
    if(isHoliday(iso)) c.classList.add("holiday-bg");
    else if(wd===0) c.classList.add("sunday-bg");
    else if(wd===6) c.classList.add("saturday-bg");
    // データ差分
    let data=calendarData[iso]||{}, prev=prevCalendarData[iso]||{};
    let dv=(typeof data.vacancy==="number"&&typeof prev.vacancy==="number")?data.vacancy-prev.vacancy:0;
    let dp=(typeof data.avg_price==="number"&&typeof prev.avg_price==="number")?Math.round(data.avg_price)-Math.round(prev.avg_price):0;
    let stock=typeof data.vacancy==="number"?`${data.vacancy}件`:"-";
    let price=typeof data.avg_price==="number"?data.avg_price.toLocaleString():"-";
    // demandLv
    let lvl=0;
    if(data.vacancy!=null&&data.avg_price!=null){
      if(data.vacancy<=70||data.avg_price>=50000) lvl=5;
      else if(data.vacancy<=100||data.avg_price>=40000) lvl=4;
      else if(data.vacancy<=150||data.avg_price>=35000) lvl=3;
      else if(data.vacancy<=200||data.avg_price>=30000) lvl=2;
      else if(data.vacancy<=250||data.avg_price>=25000) lvl=1;
    }
    let badge = lvl?`<div class="cell-demand-badge lv${lvl}">🔥${lvl}</div>`:"";
    // イベント
    let evs=(eventData[iso]||[]).map(e=>`<div class="cell-event">${e.icon} ${e.name}</div>`).join("");
    // HTML
    c.innerHTML=`
      <div class="cell-date">${d}</div>
      <div class="cell-main">
        <span class="cell-vacancy">${stock}</span>
        <span class="cell-vacancy-diff ${dv>0?"plus":dv<0?"minus":"flat"}">
          ${dv>0?("+"+dv):(dv<0?dv:"±0")}
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
    c.onclick=()=>{ selectedDate=iso; renderPage(); };

    grid.appendChild(c);
    count++;
  }

  wrapper.appendChild(grid);
  return wrapper;
}

// グラフ
function renderGraph(dateStr) {
  let gc=document.getElementById("graph-container");
  if(!dateStr){ gc.innerHTML=""; return; }
  gc.style.display="block";
  // 履歴
  let hist=historicalData[dateStr]||{};
  let labels=[], sv=[], pv=[];
  for(let d of Object.keys(hist).sort()){
    labels.push(d);
    sv.push(hist[d].vacancy);
    pv.push(hist[d].avg_price);
  }
  // ボタン群
  let allDates=Object.keys(historicalData).sort(),
      idx=allDates.indexOf(dateStr);
  function nav(diff){
    let ni=idx+diff;
    if(ni>=0&&ni<allDates.length){
      selectedDate=allDates[ni];
      renderPage();
    }
  }

  gc.innerHTML=`
    <div class="graph-btns">
      <button onclick="closeGraph()">当日に戻る</button>
      <button onclick="nav(-1)">< 前日</button>
      <button onclick="nav(1)">翌日 ></button>
    </div>
    <h3>${dateStr} の在庫・価格推移</h3>
    <canvas id="stockChart" width="420" height="180"></canvas>
    <canvas id="priceChart" width="420" height="180"></canvas>
  `;
  window.closeGraph = ()=>{ selectedDate=todayIso(); renderPage(); };
  window.nav = nav;

  if(window.stockChartInstance) window.stockChartInstance.destroy();
  if(window.priceChartInstance) window.priceChartInstance.destroy();

  if(labels.length){
    window.stockChartInstance=new Chart(
      document.getElementById('stockChart').getContext('2d'),
      {
        type:'line',
        data:{labels, datasets:[{label:'在庫数',data:sv, fill:false, borderColor:'#2196f3', tension:0.2, pointRadius:2}]},
        options:{plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true,title:{display:true,text:'在庫数'}}, x:{title:{display:true,text:'日付'}}}}
      }
    );
    window.priceChartInstance=new Chart(
      document.getElementById('priceChart').getContext('2d'),
      {
        type:'line',
        data:{labels, datasets:[{label:'平均価格',data:pv, fill:false, borderColor:'#e91e63', tension:0.2, pointRadius:2}]},
        options:{plugins:{legend:{display:false}}, scales:{y:{beginAtZero:false,title:{display:true,text:'平均価格（円）'}}, x:{title:{display:true,text:'日付'}}}}
      }
    );
  }
}

// 最終更新
function updateLastUpdate(){
  let t=document.getElementById("last-update"),
      d=new Date(), pad=(n)=>String(n).padStart(2,'0');
  t.textContent=`最終更新日時：${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
