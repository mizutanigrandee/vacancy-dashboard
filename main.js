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

async function loadData() {
  try {
    const vacancyResponse = await fetch('vacancy_price_cache.json');
    if (!vacancyResponse.ok) throw new Error('vacancy_price_cache.json not found or invalid');
    vacancyData = await vacancyResponse.json();

    const historicalResponse = await fetch('historical_data.json');
    if (!historicalResponse.ok) throw new Error('historical_data.json not found or invalid');
    historicalData = await historicalResponse.json();

    const eventResponse = await fetch('event_data.xlsx');
    if (!eventResponse.ok) throw new Error('event_data.xlsx not found or invalid');
    const arrayBuffer = await eventResponse.arrayBuffer();
    const workbook = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' });
    eventData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]);
    eventData = eventData.map(event => ({
      ...event,
      date: moment('1899-12-30').add(event.date, 'days').format('YYYY-MM-DD')
    }));
    lastUpdatedEl.textContent = `最終更新: ${moment().format('YYYY-MM-DD HH:mm')} JST`;
    console.log('Data loaded successfully');
  } catch (error) {
    console.error('データ読み込みエラー:', error.message);
    lastUpdatedEl.textContent = `最終更新: エラー (${error.message})`;
  }
  renderCalendars();
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
  if (day === 0 || Math.random() > 0.9) return '#ffecec'; // 簡易祝日
  if (day === 6) return '#e0f7ff';
  return '#fff';
}

function renderCalendar(el, month) {
  const cal = [];
  cal.push('<div class="calendar-wrapper"><table style="border-collapse:collapse;width:100%;table-layout:fixed;text-align:center;">');
  cal.push('<thead style="background:#f4f4f4;color:#333;font-weight:bold;"><tr>');
  cal.push(''.join(`<th style="border:1px solid #aaa;padding:4px;">${d}</th>` for d in "日月火水木金土"));
  cal.push('</tr></thead><tbody>');
  const daysInMonth = month.daysInMonth();
  const startDay = month.startOf('month').day();
  const today = moment().startOf('day');

  for (let w = 0; w < 6; w++) {
    cal.push('<tr>');
    for (let d = 0; d < 7; d++) {
      const day = w * 7 + d - startDay + 1;
      if (day <= 0 || day > daysInMonth) {
        cal.push('<td style="border:1px solid #aaa;padding:8px;background:#fff;"></td>');
        continue;
      }
      const date = month.date(day).format('YYYY-MM-DD');
      const data = vacancyData[date] || { vacancy: '-', avg_price: '-', previous_vacancy: '-', previous_avg_price: '-' };
      const vacDiff = data.vacancy !== '-' && data.previous_vacancy !== '-' ? parseInt(data.vacancy) - parseInt(data.previous_vacancy) : null;
      const priceDiff = data.avg_price !== '-' && data.previous_avg_price !== '-' ? 
        Math.round(parseInt(data.avg_price) - parseInt(data.previous_avg_price)) : null;
      const events = eventData.filter(e => e.date === date);
      const demand = calculateDemand(data.vacancy, data.avg_price);
      const bgColor = getHolidayColor(date);
      const isPast = moment(date).isBefore(today);

      cal.push(`
        <td style="border:1px solid #aaa;padding:8px;background:${bgColor};position:relative;vertical-align:top;"
            onclick="showGraph('${date}')">
          <div style="position:absolute;top:4px;left:4px;font-size:14px;font-weight:bold;">${day}</div>
          <div style="font-size:16px;font-weight:bold;">${data.vacancy === '-' ? '-' : `${data.vacancy}件`}${vacDiff !== null ? `<span style="color:${vacDiff >= 0 ? 'red' : 'blue'};font-size:12px;">(${vacDiff >= 0 ? '+' : ''}${vacDiff}件)</span>` : ''}</div>
          <div style="font-size:16px;font-weight:bold;">¥${data.avg_price === '-' ? '-' : parseInt(data.avg_price).toLocaleString()}円${priceDiff !== null ? `<span style="color:${priceDiff >= 0 ? 'red' : 'blue'};">${priceDiff >= 0 ? '↑' : '↓'}</span>` : ''}</div>
          <div style="font-size:12px;margin-top:4px;">${events.map(e => `${e.icon} ${e.name}`).join('<br>')}</div>
          ${!isPast && demand > 0 ? `<div style="position:absolute;top:2px;right:4px;font-size:${[16, 18, 20, 22, 24][demand-1]}px;color:${['#e15759', '#f28c38', '#f1c40f', '#f39c12', '#e74c3c'][demand-1]};">🔥${'★'.repeat(demand)}</div>` : ''}
        </td>`);
    }
    cal.push('</tr>');
  }
  cal.push('</tbody></table></div>');
  el.innerHTML = cal.join('');
}

function renderCalendars() {
  if (!vacancyData || !eventData) {
    console.error('Data not loaded yet');
    return;
  }
  const month1 = currentMonth.clone();
  const month2 = currentMonth.clone().add(1, 'month');
  renderCalendar(calendar1El, month1);
  renderCalendar(calendar2El, month2);
}

document.getElementById('prevMonth').addEventListener('click', () => {
  currentMonth.add(-1, 'month');
  renderCalendars();
});
document.getElementById('currentMonth').addEventListener('click', () => {
  currentMonth = moment().startOf('month');
  renderCalendars();
});
document.getElementById('nextMonth').addEventListener('click', () => {
  currentMonth.add(1, 'month');
  renderCalendars();
});

function showGraph(date) {
  selectedDate = date;
  graphContainer.classList.remove('hidden');
  if (priceChart) priceChart.destroy();
  const data = historicalData[date] || {};
  const dates = Object.keys(data).sort();
  const graphData = dates.map(d => ({
    date: d,
    vacancy: data[d].vacancy || 0,
    avg_price: data[d].avg_price || 0
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
}

document.getElementById('closeGraph').addEventListener('click', () => graphContainer.classList.add('hidden'));
document.getElementById('prevDay').addEventListener('click', () => {
  if (selectedDate) showGraph(moment(selectedDate).subtract(1, 'day').format('YYYY-MM-DD'));
});
document.getElementById('nextDay').addEventListener('click', () => {
  if (selectedDate) showGraph(moment(selectedDate).add(1, 'day').format('YYYY-MM-DD'));
});

document.addEventListener('DOMContentLoaded', loadData);
