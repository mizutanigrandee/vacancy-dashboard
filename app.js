const API_URL   = './vacancy_price_cache.json';
const HIST_URL  = './historical_data.json';
const EVT_URL   = './event_data.json';
const DEMAND_URL= './demand_spike_history.json';
const HOL_URL   = './holiday_data.json';

let rawData, histData, eventData, spikeData, holidayList;
let holidaySet;
let offset = 0, current = null;
let vacChart, priceChart;

window.addEventListener('DOMContentLoaded', async () => {
  // 1. JSON一括取得
  [ rawData, histData, eventData, spikeData, holidayList ] = await Promise.all(
    [ API_URL, HIST_URL, EVT_URL, DEMAND_URL, HOL_URL ]
      .map(u => fetch(u).then(r=>r.json()))
  );
  holidaySet = new Set(holidayList);

  // 2. 最終更新表示
  document.getElementById('last-updated').textContent =
    `最終更新：${new Date().toLocaleString('ja-JP',{hour12:false})}`;

  // 3. 需要急騰バナー描画
  renderSpike(spikeData);

  // 4. カレンダー描画＋ナビ設定＋グラフナビ設定
  render();
  setupNav();
  setupGraphNav();
});


// --- Require 3日分×最大10件 のチップ生成 ---
function formatSpikeChip(spike, upDate) {
  const priceTxt = `<span style="color:#d35400;">単価${spike.price_diff>0?'↑':'↓'} ${Math.abs(spike.price_diff).toLocaleString()}円</span>（${(spike.price_ratio*100).toFixed(1)}%）`;
  const vacTxt   = `<span style="color:#2980b9;">客室${spike.vacancy_diff<0?'減':'増'} ${Math.abs(spike.vacancy_diff)}件</span>（${(spike.vacancy_ratio*100).toFixed(1)}%）`;
  const dateLbl  = new Date(upDate);
  return `<span class="spike-chip" style="background:#fff8e6;border:1.1px solid #ffdca7;border-radius:6px;padding:6px 12px 5px 8px;display:inline-block;font-size:14.2px;line-height:1.22;margin-right:10px;margin-bottom:3px;">
    <span style="color:#e67e22;font-weight:700;margin-right:8px;">【${dateLbl.getMonth()+1}/${dateLbl.getDate()} UP】</span>
    <span style="font-weight:900;color:#222;font-size:15px;margin-right:2px;">該当日 <span style="letter-spacing:1px;">${spike.spike_date}</span></span>
    ${priceTxt}　${vacTxt}　
    <span style="color:#555;font-size:12.3px;">平均￥${spike.price.toLocaleString()}／残${spike.vacancy}</span>
  </span>`;
}

function renderSpike(data) {
  const days = Object.keys(data).sort((a,b)=>b.localeCompare(a)).slice(0,3);
  const chips = [];
  for (const d of days) {
    for (const c of data[d]) {
      chips.push(formatSpikeChip(c, d));
      if (chips.length >= 10) break;
    }
    if (chips.length >= 10) break;
  }
  document.getElementById('spike-container').innerHTML = `
    <div style="background:#fff8e6;border:2px solid #ffdca7;border-radius:13px;padding:12px 24px 10px 24px;max-width:850px;margin:15px auto;">
      <div style="display:flex;align-items:center;margin-bottom:4px;">
        <span style="font-size:20px;color:#e67e22;margin-right:9px;">🚀</span>
        <span style="font-weight:800;color:#e67e22;font-size:16px;letter-spacing:0.5px;margin-right:9px;">需要急騰検知日</span>
        <span style="font-size:12.5px;color:#ae8d3a;">（直近3日分・最大10件）</span>
      </div>
      <div class="spike-flex-row" style="display:flex;flex-wrap:wrap;gap:7px 0;align-items:center;margin-top:1px;">
        ${chips.join("")}
      </div>
    </div>`;
}


// --- カレンダー生成 & 日付クリック --- 
function setupNav(){
  document.getElementById('prev-month').onclick    = ()=>{ offset--; render(); };
  document.getElementById('current-month').onclick = ()=>{ offset=0; render(); };
  document.getElementById('next-month').onclick    = ()=>{ offset++; render(); };
}

function render(){
  const cont = document.getElementById('calendar-container');
  cont.innerHTML = '';
  const base = new Date();
  base.setMonth(base.getMonth()+offset);
  for(let i=0;i<2;i++){
    const m = new Date(base.getFullYear(), base.getMonth()+i, 1);
    cont.appendChild(createCalendar(m));
  }
  attachDateClicks();
}

function createCalendar(date){
  const y=date.getFullYear(), mo=date.getMonth();
  const first=new Date(y,mo,1), last=new Date(y,mo+1,0);
  let html=`<table class="calendar"><caption>${y}年 ${mo+1}月</caption>
    <thead><tr>${['日','月','火','水','木','金','土'].map(d=>`<th>${d}</th>`).join('')}</tr></thead><tbody>`;
  let day=1-first.getDay();
  while(day<=last.getDate()){
    html+='<tr>';
    for(let w=0;w<7;w++){
      const d=new Date(y,mo,day+w);
      if(d.getMonth()!==mo){
        html+='<td class="empty"></td>';
      } else {
        const iso=d.toISOString().slice(0,10);
        const rec=rawData[iso]||{vacancy:0,avg_price:0,previous_vacancy:0,previous_avg_price:0};
        const dv=rec.vacancy-rec.previous_vacancy, dp=rec.avg_price-rec.previous_avg_price;
        const vSign = dv>0?`<span class="up">(+${dv})</span>`:dv<0?`<span class="down">(${dv})</span>`:'';
        const pSign = dp>0?`<span class="up">↑</span>`:dp<0?`<span class="down">↓</span>`:'';
        const evs   = (eventData[iso]||[]).map(e=>`${e.icon}${e.name}`).join('<br>');
        const isHol = holidaySet.has(iso);
        const cls   = isHol||d.getDay()===0?'sunday':d.getDay()===6?'saturday':'';
        html+=`<td data-date="${iso}" class="${cls}">
          <div class="date-number">${d.getDate()}</div>
          <div class="vacancy">${rec.vacancy}件${vSign}</div>
          <div class="price">¥${rec.avg_price.toLocaleString()} ${pSign}</div>
          <div class="event">${evs}</div>
        </td>`;
      }
    }
    html+='</tr>'; day+=7;
  }
  html+='</tbody></table>';
  const wrap=document.createElement('div');
  wrap.innerHTML=html;
  return wrap.firstElementChild;
}

function attachDateClicks(){
  document.querySelectorAll('td[data-date]').forEach(td=>{
    td.onclick=()=> showGraph(td.dataset.date);
  });
}


// --- 推移グラフ --- 
function setupGraphNav(){
  document.getElementById('close-graph').onclick = hideGraph;
  document.getElementById('prev-day').onclick    = ()=>navDay(-1);
  document.getElementById('next-day').onclick    = ()=>navDay(1);
}

function showGraph(date){
  if(!histData[date]){
    alert('この日付の履歴データがありません'); return;
  }
  current = date;
  document.getElementById('graph-title').textContent = `${date} の在庫・価格推移`;
  document.getElementById('graph-area').classList.remove('hidden');

  const recs = Object.entries(histData[date])
    .map(([d,r])=>({d, vac:r.vacancy, pri:r.avg_price}))
    .sort((a,b)=>a.d.localeCompare(b.d));

  const labs = recs.map(r=>r.d.slice(5));
  const vData= recs.map(r=>r.vac);
  const pData= recs.map(r=>r.pri);

  const vCtx = document.getElementById('vac-chart').getContext('2d');
  const pCtx = document.getElementById('price-chart').getContext('2d');

  vacChart   && vacChart.destroy();
  priceChart && priceChart.destroy();

  vacChart = new Chart(vCtx, {
    type:'line',
    data:{ labels:labs, datasets:[{ label:'在庫数', data:vData, borderColor:'#4285F4', fill:false, tension:0.2 }]},
    options:{ scales:{ y:{ beginAtZero:true } } }
  });
  priceChart = new Chart(pCtx, {
    type:'line',
    data:{ labels:labs, datasets:[{ label:'平均単価 (¥)', data:pData, borderColor:'#DB4437', fill:false, tension:0.2 }]},
    options:{ scales:{ y:{ beginAtZero:true } } }
  });
}

function hideGraph(){
  document.getElementById('graph-area').classList.add('hidden');
  current = null;
}

function navDay(delta){
  if(!current) return;
  const dt=new Date(current);
  dt.setDate(dt.getDate()+delta);
  showGraph(dt.toISOString().slice(0,10));
}
