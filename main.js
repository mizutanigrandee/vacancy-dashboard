const calendar1El = document.getElementById('calendar1');
const calendar2El = document.getElementById('calendar2');
const graphContainer = document.getElementById('graph-container');
const priceChartEl = document.getElementById('priceChart');
const lastUpdatedEl = document.getElementById('lastUpdated');
let vacancyData = {};
let eventData = [];
let historicalData = {};
let currentMonth = moment().startOf('month');
let selectedDate = null;
let priceChart = null;

// ここだけ！JSONをfetchで本番取得
async function loadData() {
  try {
    const [vacancyRes, eventRes, histRes] = await Promise.all([
      fetch('./vacancy_price_cache.json'),
      fetch('./event_data.json'),
      fetch('./historical_data.json')
    ]);
    vacancyData = await vacancyRes.json();
    // eventData: 配列でも連想配列でもOKに対応
    const eventRaw = await eventRes.json();
    eventData = Array.isArray(eventRaw) ? eventRaw : Object.values(eventRaw);
    historicalData = await histRes.json();
    lastUpdatedEl.textContent = `最終更新: ${new Date().toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' })} JST`;
    renderCalendars();
  } catch (e) {
    lastUpdatedEl.textContent = "データ取得エラー";
    alert("JSONデータの読み込みに失敗しました。");
    console.error(e);
  }
}

function calculateDemand(vacancy, avgPrice) {
  if (vacancy === '-' || avgPrice === '-') return 0;
  const v = parseInt(vacancy);
  const p = parseInt(avgPrice);
  if (v <= 70 || p >= 50000) return 5;
  if (v <= 100 || p >= 40000) return 4;
  if (v <= 150 || p >= 35000) return 3;
  if (v <= 200 || p >= 30000) return 2;
  if (v <= 250 || p >= 25000) return 1;
  return 0;
}

function getHolidayColor(date) {
  const day = moment(date).day();
  if (day === 0) return '#ffecec'; // 日曜
  if (day === 6) return '#e0f7ff'; // 土曜
  // jpholiday.js等を組み込めば祝日特定も可能
  return '#fff';
}

function renderCalendar(el, month) {
  if (!el) return;
  const cal = [];
  cal.push('<div class="calendar-wrapper"><table>');
  cal.push('<thead><tr>');
  for (const d of "日月火水木金土") cal.push(`<th>${d}</th>`);
  cal.push('</tr></thead><tbody>');
  const daysInMonth = month.daysInMonth();
  const startDay = month.startOf('month').day();
  const today = moment().startOf('day');
  let dNum = 1 - startDay;
  for (let w = 0; w < 6; w++) {
    cal.push('<tr>');
    for (let d = 0; d < 7; d++, dNum++) {
      if (dNum <= 0 || dNum > daysInMonth) {
        cal.push('<td class="empty"></td>');
        continue;
      }
      const date = month.clone().date(dNum).format('YYYY-MM-DD');
      const data = vacancyData[date] || { vacancy: '-', avg_price: '-', previous_vacancy: '-', previous_avg_price: '-' };
      const vacDiff = (data.vacancy !== '-' && data.previous_vacancy !== '-') ? data.vacancy - data.previous_vacancy : null;
      const priceDiff = (data.avg_price !== '-' && data.previous_avg_price !== '-') ? data.avg_price - data.previous_avg_price : null;
      const events = eventData.filter(e => e.date === date);
      const demand = calculateDemand(data.vacancy, data.avg_price);
      const bgColor = getHolidayColor(date);
      const isPast = moment(date).isBefore(today);

      cal.push(`
        <td style="background:${bgColor};" onclick="showGraph('${date}')">
          <div class="date-num">${dNum}</div>
          <div class="vacancy">${data.vacancy !== '-' ? `${data.vacancy}件` : '-' }${vacDiff !== null ? `<span class="diff ${vacDiff>=0?'plus':'minus'}">(${vacDiff>=0?'+':''}${vacDiff}件)</span>` : ''}</div>
          <div class="price">${data.avg_price !== '-' ? `￥${Number(data.avg_price).toLocaleString()}円` : '￥-円'}${priceDiff !== null ? `<span class="diff ${priceDiff>=0?'plus':'minus'}">${priceDiff>=0?'↑':'↓'}</span>` : ''}</div>
          <div class="event-line">${events.map(e => `<span class="event-symbol ${e.icon=='🔴'?'red':e.icon=='🔵'?'blue':'black'}">${e.icon}</span>${e.name||''}`).join('<br>')}</div>
          ${!isPast && demand>0 ? `<div class="demand-mark">🔥${'★'.repeat(demand)}</div>` : ''}
        </td>
      `);
    }
    cal.push('</tr>');
  }
  cal.push('</tbody></table></div>');
  el.innerHTML = cal.join('');
}

function renderCalendars() {
  const month1 = currentMonth.clone();
  const month2 = currentMonth.clone().add(1, 'month');
  renderCalendar(calendar1El, month1);
  renderCalendar(calendar2El, month2);
}

// ナビ
document.getElementById('prevMonth').onclick = () => { currentMonth.add(-1, 'month'); renderCalendars(); };
document.getElementById('currentMonth').onclick = () => { currentMonth = moment().startOf('month'); renderCalendars(); };
document.getElementById('nextMonth').onclick = () => { currentMonth.add(1, 'month'); renderCalendars(); };

// グラフ
window.showGraph = function(date) {
  selectedDate = date;
  graphContainer.classList.remove('hidden');
  if (priceChart) priceChart.destroy();
  const data = historicalData[date] || {};
  const dates = Object.keys(data).sort();
  const graphData = dates.map(d => ({
    date: d,
    vacancy: data[d]?.vacancy || 0,
    avg_price: data[d]?.avg_price || 0
  }));
  priceChart = new Chart(priceChartEl, {
    type: 'line',
    data: {
      labels: graphData.map(d => moment(d.date).format('MM/DD')),
      datasets: [
        { label: '平均単価', data: graphData.map(d => d.avg_price), borderColor: '#e15759', yAxisID: 'y1', fill: false, pointRadius: 3, tension: 0.1 },
        { label: '在庫数', data: graphData.map(d => d.vacancy), borderColor: 'green', yAxisID: 'y2', fill: false, pointRadius: 3, tension: 0.1 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: '日付' } },
        y1: { type: 'linear', position: 'left', title: { display: true, text: '平均単価 (円)' }, ticks: { callback: v => `¥${v.toLocaleString()}` }, beginAtZero: true },
        y2: { type: 'linear', position: 'right', title: { display: true, text: '在庫数' }, grid: { drawOnChartArea: false }, beginAtZero: true }
      },
      plugins: { legend: { position: 'top', labels: { boxWidth: 20, font: { size: 14 } } } }
    }
  });
};
document.getElementById('closeGraph').onclick = () => graphContainer.classList.add('hidden');
document.getElementById('prevDay').onclick = () => {
  if (selectedDate) window.showGraph(moment(selectedDate).subtract(1, 'day').format('YYYY-MM-DD'));
};
document.getElementById('nextDay').onclick = () => {
  if (selectedDate) window.showGraph(moment(selectedDate).add(1, 'day').format('YYYY-MM-DD'));
};

document.addEventListener('DOMContentLoaded', loadData);
