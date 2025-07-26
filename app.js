const API_URL = './vacancy_price_cache.json';
const HIST_URL = './historical_data.json';
const EVENT_URL = './event_data.json';

let rawData = {}, histData = {}, eventData = {};
let currentOffset = 0, currentDate = null;
let vacChart = null, priceChart = null;

document.addEventListener('DOMContentLoaded', async () => {
  await loadAll();
  renderCalendar();
  setupNavButtons();
  setupGraphButtons();
});

async function loadAll() {
  [ rawData, histData, eventData ] = await Promise.all(
    [API_URL, HIST_URL, EVENT_URL].map(url => fetch(url).then(r => r.json()))
  );
  document.getElementById('last-updated').textContent =
    `最終更新：${new Date().toLocaleString('ja-JP', { hour12:false })}`;
}

function setupNavButtons() {
  document.getElementById('prev-month').onclick = () => { currentOffset--; renderCalendar(); };
  document.getElementById('current-month').onclick = () => { currentOffset = 0; renderCalendar(); };
  document.getElementById('next-month').onclick = () => { currentOffset++; renderCalendar(); };
}

function renderCalendar() {
  const container = document.getElementById('calendar-container');
  container.innerHTML = '';
  const base = new Date();
  base.setMonth(base.getMonth() + currentOffset);
  for(let i=0; i<2; i++){
    const m = new Date(base.getFullYear(), base.getMonth()+i, 1);
    container.appendChild(createCalendar(m));
  }
  // attach cell clicks
  document.querySelectorAll('td[data-date]').forEach(td => {
    td.onclick = () => showGraph(td.dataset.date);
  });
}

function createCalendar(date) {
  const year = date.getFullYear(), month = date.getMonth();
  const first = new Date(year, month, 1), last = new Date(year, month+1, 0);
  const tbl = document.createElement('table');
  tbl.className = 'calendar';
  tbl.innerHTML = `<caption>${year}年${month+1}月</caption>
    <thead><tr>${['日','月','火','水','木','金','土'].map(d=>`<th>${d}</th>`).join('')}</tr></thead><tbody>`;
  let day = 1 - first.getDay();
  while(day <= last.getDate()){
    tbl.innerHTML += '<tr>' + Array(7).fill(0).map((_,i) => {
      const d = new Date(year,month,day+i);
      if(d.getMonth()!==month) return `<td class="empty"></td>`;
      const iso = d.toISOString().slice(0,10);
      const rec = rawData[iso]||{vacancy:0,avg_price:0,previous_vacancy:0,previous_avg_price:0};
      const dv = rec.vacancy - rec.previous_vacancy;
      const dp = rec.avg_price  - rec.previous_avg_price;
      const arrow = dp>0?'<span class="up">↑</span>':dp<0?'<span class="down">↓</span>':'';
      const evs = (eventData[iso]||[]).map(e=>`${e.icon}${e.name}`).join('<br>');
      const wd = d.getDay();
      const cls = wd===0?'sunday':wd===6?'saturday':'';
      return `<td data-date="${iso}" class="${cls}">
        <div class="date-number">${d.getDate()}</div>
        <div class="vacancy">${rec.vacancy}件${dv>0?`<span class="up">(+${dv})</span>`:dv<0?`<span class="down">(${dv})</span>`:''}</div>
        <div class="price">¥${rec.avg_price.toLocaleString()} ${arrow}</div>
        <div class="event">${evs}</div>
      </td>`;
    }).join('') + '</tr>';
    day += 7;
  }
  tbl.innerHTML += '</tbody>';
  const div = document.createElement('div');
  div.appendChild(tbl);
  return div;
}

function setupGraphButtons() {
  document.getElementById('close-graph').onclick = hideGraph;
  document.getElementById('prev-day').onclick   = () => navDay(-1);
  document.getElementById('next-day').onclick   = () => navDay(1);
}

function showGraph(date) {
  if(!histData[date]) { alert('この日付の履歴データがありません'); return; }
  currentDate = date;
  document.getElementById('graph-title').textContent = `${date} の在庫・価格推移`;
  document.getElementById('graph-area').classList.remove('hidden');

  const records = Object.entries(histData[date])
    .map(([d,r])=>({d,newVac:r.vacancy,newPrice:r.avg_price}))
    .sort((a,b)=>a.d.localeCompare(b.d));

  const labels = records.map(r=>r.d.slice(5));
  const vacData = records.map(r=>r.newVac);
  const priceData = records.map(r=>r.newPrice);

  const vacCtx = document.getElementById('vac-chart').getContext('2d');
  const priceCtx = document.getElementById('price-chart').getContext('2d');

  if(vacChart) vacChart.destroy();
  vacChart = new Chart(vacCtx, {
    type:'line',
    data:{ labels, datasets:[{ label:'在庫数', data:vacData, fill:false, tension:0.2 }] },
    options:{ scales:{ y:{ beginAtZero:true } } }
  });

  if(priceChart) priceChart.destroy();
  priceChart = new Chart(priceCtx, {
    type:'line',
    data:{ labels, datasets:[{ label:'平均単価 (¥)', data:priceData, fill:false, tension:0.2 }] },
    options:{ scales:{ y:{ beginAtZero:true } } }
  });
}

function hideGraph() {
  document.getElementById('graph-area').classList.add('hidden');
  currentDate = null;
}

function navDay(offset) {
  if(!currentDate) return;
  const dt = new Date(currentDate);
  dt.setDate(dt.getDate() + offset);
  const iso = dt.toISOString().slice(0,10);
  showGraph(iso);
}
