// ---- 設定エリア ----
const HOLIDAYS = [
  // 2025年〜2026年分までの祝日を都度追加
  "2025-01-01","2025-01-13","2025-02-11","2025-02-23","2025-02-24",
  "2025-03-20","2025-04-29","2025-05-03","2025-05-04","2025-05-05","2025-05-06",
  "2025-07-21","2025-08-11","2025-09-15","2025-09-23","2025-10-13",
  "2025-11-03","2025-11-23","2025-11-24","2025-12-23", // etc.
  // 2026年の祝日も必要に応じて追加
];
function isHoliday(date) {
  // date: Dateオブジェクト
  const iso = date.toISOString().slice(0,10);
  return HOLIDAYS.includes(iso);
}

// ---- ダミーデータ読込 ----
async function fetchData() {
  // デモ用データ構造（本番はAPIやファイル読込に置換）
  // 実際には vacancy_price_cache.json, historical_data.json などをfetch
  // サンプル用JSON
  const [calendar, hist] = await Promise.all([
    fetch('vacancy_price_cache.json').then(r=>r.json()),
    fetch('historical_data.json').then(r=>r.json())
  ]);
  return {calendar, hist};
}

// ---- 日付操作ユーティリティ ----
function getFirstDay(monthOffset=0) {
  const today = new Date();
  today.setDate(1);
  today.setMonth(today.getMonth() + monthOffset);
  today.setHours(0,0,0,0);
  return today;
}
function addMonth(date, n) {
  let d = new Date(date);
  d.setMonth(d.getMonth()+n);
  return d;
}
function formatDate(d) {
  // yyyy-mm-dd
  return d.toISOString().slice(0,10);
}
function formatYmd(d) {
  // yyyy年m月d日
  return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日`;
}
function isSameDay(d1, d2) {
  return d1 && d2 && formatDate(d1) === formatDate(d2);
}

// ---- カレンダー生成 ----
function buildCalendar(monthDate, calendarData, selected, histData) {
  // monthDate: その月の1日(Date)
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth();
  const weeks = [];
  let firstDay = new Date(year, month, 1);
  let lastDay = new Date(year, month+1, 0);
  let week = [];

  // 曜日ヘッダー
  const weekDays = ['日','月','火','水','木','金','土'];
  weeks.push(weekDays.map((w,i)=>({weekday:i, label:w, header:true})));

  // カレンダーの日付並び
  let start = new Date(firstDay); start.setDate(1 - firstDay.getDay());
  for(let i=0;i<6*7;i++){
    let d = new Date(start); d.setDate(start.getDate()+i);
    week.push({date: d, isCurrent: d.getMonth()===month});
    if(week.length===7){
      weeks.push(week);
      week = [];
    }
  }

  // 1カ月分カレンダー要素生成
  const calDiv = document.createElement('div');
  calDiv.className = "month-calendar";
  // ヘッダー
  const h = document.createElement('div');
  h.className = "month-header";
  h.innerText = `${year}年${month+1}月`;
  calDiv.appendChild(h);

  // グリッド
  const grid = document.createElement('div');
  grid.className = "calendar-grid";

  for(const row of weeks){
    for(const cell of row){
      if(cell.header){
        // 曜日ヘッダーセル
        const div = document.createElement('div');
        div.className = "calendar-cell";
        div.innerText = cell.label;
        grid.appendChild(div);
        continue;
      }
      // 日付セル
      const d = cell.date;
      const isThisMonth = d.getMonth()===month;
      const iso = formatDate(d);
      const rec = calendarData[iso] || {};
      const isSat = d.getDay()===6;
      const isSun = d.getDay()===0;
      const isHol = isHoliday(d);
      const selectedFlag = selected && isSameDay(selected, d);

      // セル装飾
      let cls = "calendar-cell";
      if(!isThisMonth) { cls+=" disabled"; }
      if(isHol) cls+=" holiday";
      else if(isSat) cls+=" saturday";
      else if(isSun) cls+=" sunday";
      if(selectedFlag) cls += " selected";

      const cellDiv = document.createElement('div');
      cellDiv.className = cls;
      // 日付
      const dateSpan = document.createElement('span');
      dateSpan.className = "cell-date";
      dateSpan.innerText = d.getDate();
      cellDiv.appendChild(dateSpan);

      // 在庫数
      if(isThisMonth){
        const mainDiv = document.createElement('div');
        mainDiv.className = "cell-main";
        mainDiv.innerHTML = `${rec.vacancy ?? '-'}件 `;
        // 前日比
        if(rec.vacancy_diff>0) mainDiv.innerHTML += `<span class="cell-diff up">（+${rec.vacancy_diff}）</span>`;
        else if(rec.vacancy_diff<0) mainDiv.innerHTML += `<span class="cell-diff down">（${rec.vacancy_diff}）</span>`;
        cellDiv.appendChild(mainDiv);

        // 平均価格
        const priceDiv = document.createElement('div');
        priceDiv.className = "cell-price";
        priceDiv.innerHTML = `￥${rec.avg_price?.toLocaleString() ?? '-'}`;
        if(rec.avg_price_diff>0) priceDiv.innerHTML += `<span class="cell-diff up">↑</span>`;
        else if(rec.avg_price_diff<0) priceDiv.innerHTML += `<span class="cell-diff down">↓</span>`;
        cellDiv.appendChild(priceDiv);

        // 需要シンボル（サンプル）
        if(rec.demand) {
          const dem = document.createElement('span');
          dem.className = "cell-demand";
          dem.innerText = "🔥" + rec.demand;
          cellDiv.appendChild(dem);
        }
        // イベント（ここはrec.eventsとしてお好みで）
        if(rec.event){
          const eventDiv = document.createElement('div');
          eventDiv.className = "cell-event";
          eventDiv.innerText = rec.event;
          cellDiv.appendChild(eventDiv);
        }
        // グラフ用
        cellDiv.addEventListener('click', ()=>{
          renderGraph(d, histData);
          selectDate(d);
        });
      }
      grid.appendChild(cellDiv);
    }
  }
  calDiv.appendChild(grid);
  return calDiv;
}

// ---- グラフ描画 ----
let chart1, chart2;
function renderGraph(date, histData){
  // graph-container直書き
  const gc = document.getElementById('graph-container');
  gc.innerHTML = `
    <button onclick="closeGraph()" style="margin-bottom:7px;">✗ グラフを閉じる</button>
    <button onclick="moveDay(-1)">＜前日</button>
    <button onclick="moveDay(1)">翌日＞</button>
    <div style="font-weight:bold;margin-top:5px;">${formatDate(date)} の在庫・価格推移</div>
    <canvas id="vacancyChart" height="110"></canvas>
    <canvas id="priceChart" height="110"></canvas>
  `;
  const hist = histData[formatDate(date)];
  if(hist){
    // 履歴データ：{"2025-07-25": {"2025-07-10":{vacancy:123,avg_price:9999}, ...} }
    const labels = Object.keys(hist).sort();
    const vacancies = labels.map(d=>hist[d].vacancy);
    const prices = labels.map(d=>hist[d].avg_price);

    if(chart1) chart1.destroy();
    if(chart2) chart2.destroy();
    chart1 = new Chart(document.getElementById('vacancyChart').getContext('2d'), {
      type:'line',
      data:{labels, datasets:[{label:'在庫数', data:vacancies, borderColor:'#3c7cfc', fill:false}]},
      options:{responsive:true, plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true}}}
    });
    chart2 = new Chart(document.getElementById('priceChart').getContext('2d'), {
      type:'line',
      data:{labels, datasets:[{label:'平均単価', data:prices, borderColor:'#e15759', fill:false}]},
      options:{responsive:true, plugins:{legend:{display:false}}, scales:{y:{beginAtZero:false}}}
    });
  }else{
    gc.innerHTML += "<div style='margin-top:8px;color:#888;'>この日の履歴データはありません</div>";
  }
  window.__selectedDate = new Date(date);
}
window.closeGraph = function(){
  // グラフ非表示にせず当日表示
  selectDate(new Date());
  renderGraph(new Date(), window.__histData);
}
window.moveDay = function(diff){
  if(!window.__selectedDate) return;
  const d = new Date(window.__selectedDate);
  d.setDate(d.getDate()+diff);
  selectDate(d);
  renderGraph(d, window.__histData);
}

// ---- カレンダー表示 ----
function renderAll(calendarData, histData){
  // 日付選択状態（local/globalに持たせる）
  const container = document.getElementById('calendar-container');
  container.innerHTML = '';
  // 2ヶ月分のカレンダー
  let offset = window.__monthOffset || 0;
  let sel = window.__selectedDate || new Date();
  const cal1 = buildCalendar(getFirstDay(offset), calendarData, sel, histData);
  const cal2 = buildCalendar(getFirstDay(offset+1), calendarData, sel, histData);
  container.appendChild(cal1);
  container.appendChild(cal2);
}
function selectDate(d){
  window.__selectedDate = new Date(d);
  renderAll(window.__calendarData, window.__histData);
}

// ---- 最終更新日などフッター処理 ----
function updateFooter(){
  // ファイル更新日時取得など適宜
  document.getElementById('update-info').innerText =
    (new Date()).toLocaleString();
  document.getElementById('last-update').innerText =
    "最終更新日時：" + (new Date()).toLocaleString();
}

// ---- 月切替ボタン ----
function bindNav(){
  window.__monthOffset = 0;
  document.getElementById('prevMonthBtn').onclick = ()=>{
    window.__monthOffset = (window.__monthOffset || 0) - 1;
    renderAll(window.__calendarData, window.__histData);
  };
  document.getElementById('currentMonthBtn').onclick = ()=>{
    window.__monthOffset = 0;
    renderAll(window.__calendarData, window.__histData);
  };
  document.getElementById('nextMonthBtn').onclick = ()=>{
    window.__monthOffset = (window.__monthOffset || 0) + 1;
    renderAll(window.__calendarData, window.__histData);
  };
}

// ---- 初期化 ----
window.addEventListener('DOMContentLoaded', async ()=>{
  // データ読込
  const {calendar, hist} = await fetchData();
  window.__calendarData = calendar;
  window.__histData = hist;
  window.__monthOffset = 0;
  window.__selectedDate = new Date(); // 初期選択は本日
  bindNav();
  renderAll(calendar, hist);
  renderGraph(new Date(), hist);
  updateFooter();
});
