const API_URL  = './vacancy_price_cache.json';
const HIST_URL = './historical_data.json';
const EVT_URL  = './event_data.json';

let rawData = {}, histData = {}, eventData = {};
let offset = 0, current = null;
let vacChart, priceChart;

window.addEventListener('DOMContentLoaded', async () => {
  [rawData, histData, eventData] = await Promise.all(
    [API_URL, HIST_URL, EVT_URL].map(u => fetch(u).then(r=>r.json()))
  );
  document.getElementById('last-updated').textContent =
    `最終更新：${new Date().toLocaleString('ja-JP',{hour12:false})}`;
  render();
  setupNav();
  setupGraphNav();
});

function setupNav(){
  document.getElementById('prev-month').onclick   = ()=>{ offset--; render(); };
  document.getElementById('current-month').onclick= ()=>{ offset=0; render(); };
  document.getElementById('next-month').onclick   = ()=>{ offset++; render(); };
}

function render(){
  const cont = document.getElementById('calendar-container');
  cont.innerHTML = '';
  const base = new Date();
  base.setMonth(base.getMonth()+offset);
  for(let i=0;i<2;i++){
    const m = new Date(base.getFullYear(), base.getMonth()+i,1);
    cont.appendChild(makeCal(m));
  }
  attachDates();
}

function makeCal(date){
  const y=date.getFullYear(), mo=date.getMonth();
  const first=new Date(y,mo,1), last=new Date(y,mo+1,0);
  let html=`<table class="calendar"><caption>${y}年 ${mo+1}月</caption>
    <thead><tr>${['日','月','火','水','木','金','土'].map(d=>`<th>${d}</th>`).join('')}</tr></thead><tbody>`;
  let day=1-first.getDay();
  while(day<=last.getDate()){
    html+='<tr>';
    for(let w=0;w<7;w++){
      const d=new Date(y,mo,day+w);
      if(d.getMonth()!==mo){ html+='<td class="empty"></td>'; continue; }
      const iso=d.toISOString().slice(0,10);
      const rec=rawData[iso]||{vacancy:0,avg_price:0,previous_vacancy:0,previous_avg_price:0};
      const dv=rec.vacancy-rec.previous_vacancy, dp=rec.avg_price-rec.previous_avg_price;
      const vSign = dv>0?`<span class="up">(+${dv})</span>`:dv<0?`<span class="down">(${dv})</span>`:'';
      const pSign = dp>0?`<span class="up">↑</span>`:dp<0?`<span class="down">↓</span>`:'';
      const evs=(eventData[iso]||[]).map(e=>`${e.icon}${e.name}`).join('<br>');
      const cls = d.getDay()===0?'sunday':d.getDay()===6?'saturday':'';
      html+=`<td data-date="${iso}" class="${cls}">
        <div class="date-number">${d.getDate()}</div>
        <div class="vacancy">${rec.vacancy}件${vSign}</div>
        <div class="price">¥${rec.avg_price.toLocaleString()} ${pSign}</div>
        <div class="event">${evs}</div>
      </td>`;
    }
    html+='</tr>'; day+=7;
  }
  html+='</tbody></table>';
  const wrapper=document.createElement('div');
  wrapper.innerHTML=html;
  return wrapper.firstElementChild;
}

function attachDates(){
  document.querySelectorAll('td[data-date]').forEach(td=>{
    td.onclick=()=>showGraph(td.dataset.date);
  });
}

function setupGraphNav(){
  document.getElementById('close-graph').onclick = hideGraph;
  document.getElementById('prev-day').onclick   = ()=>navDay(-1);
  document.getElementById('next-day').onclick   = ()=>navDay(1);
}

function showGraph(date){
  if(!histData[date]){
    alert('この日付の履歴データがありません');
    return;
  }
  current = date;
  document.getElementById('graph-title').textContent=`${date} の在庫・価格推移`;
  document.getElementById('graph-area').classList.remove('hidden');

  const recs = Object.entries(histData[date])
    .map(([d,r])=>({d, vac:r.vacancy, pri:r.avg_price}))
    .sort((a,b)=>a.d.localeCompare(b.d));

  const labels = recs.map(r=>r.d.slice(5));
  const vData  = recs.map(r=>r.vac);
  const pData  = recs.map(r=>r.pri);

  const vCtx = document.getElementById('vac-chart').getContext('2d');
  const pCtx = document.getElementById('price-chart').getContext('2d');

  vacChart   && vacChart.destroy();
  priceChart && priceChart.destroy();

  vacChart = new Chart(vCtx,{
    type:'line',
    data:{ labels, datasets:[{ label:'在庫数', data:vData, borderColor:'#4285F4', fill:false, tension:0.2 }]},
    options:{ scales:{ y:{ beginAtZero:true }}}
  });
  priceChart = new Chart(pCtx,{
    type:'line',
    data:{ labels, datasets:[{ label:'平均単価 (¥)', data:pData, borderColor:'#DB4437', fill:false, tension:0.2 }]},
    options:{ scales:{ y:{ beginAtZero:true }}}
  });
}

function hideGraph(){
  document.getElementById('graph-area').classList.add('hidden');
  current = null;
}

function navDay(offset){
  if(!current) return;
  const dt = new Date(current);
  dt.setDate(dt.getDate()+offset);
  showGraph(dt.toISOString().slice(0,10));
}
