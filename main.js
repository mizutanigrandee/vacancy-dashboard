const calendarEl = document.getElementById('calendar');
const graphContainer = document.getElementById('graph-container');
const priceChartEl = document.getElementById('priceChart');
const lastUpdatedEl = document.getElementById('lastUpdated');
let vacancyData = {};
let eventData = [];
let historicalData = [];
let currentMonth = moment();
let selectedDate = null;
let priceChart = null;

async function loadData() {
  try {
    const vacancyResponse = await fetch('vacancy_price_cache.json');
    vacancyData = await vacancyResponse.json();

    const historicalResponse = await fetch('historical_data.json');
    historicalData = await historicalResponse.json();

    const eventResponse = await fetch('event_data.xlsx');
    const arrayBuffer = await eventResponse.arrayBuffer();
    const workbook = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' });
    eventData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]);
    eventData = eventData.map(event => ({
      ...event,
      date: moment('1899-12-30').add(event.date, 'days').format('YYYY-MM-DD')
    }));
    lastUpdatedEl.textContent = `最終更新: ${moment().format('YYYY-MM-DD HH:mm')} JST`;
  } catch (error) {
    console.error('データ読み込みエラー:', error);
  }
  renderCalendar();
}

function calculateDemand(vacancy, avgPrice) {
  if (vacancy === '-' || avgPrice === '-') return 0;
  if (vacancy <= 70 || avgPrice >= 50000) return 5;
  if (vacancy <= 100 || avgPrice >= 40000) return 4;
  if (vacancy <= 150 || avgPrice >= 35000) return 3;
  if (vacancy <= 200 || avgPrice >= 30000) return 2;
  if (vacancy <= 250 || avgPrice >= 25000) return 1;
  return 0;
}

function renderCalendar() {
  const html = [];
  html.push('<div class="grid grid-cols-7 gap-1 text-center">');
  html.push('<div class="col-span-7 flex justify-between mb-2">');
  html.push(`<button onclick="changeMonth(-1)" class="px-2 py-1 bg-blue-500 text-white rounded"><</button>`);
  html.push(`<h2 class="text-xl">${currentMonth.format('YYYY年MM月')}</h2>`);
  html.push(`<button onclick="changeMonth(1)" class="px-2 py-1 bg-blue-500 text-white rounded">></button>`);
  html.push('</div>');

  const days = ['日', '月', '火', '水', '木', '金', '土'];
  days.forEach((day, i) => {
    html.push(`<div class="font-bold ${i === 0 || i === 6 ? 'text-red-500' : 'text-black'}">${day}</div>`);
  });

  const startOfMonth = currentMonth.clone().startOf('month');
  const endOfMonth = currentMonth.clone().endOf('month');
  const startWeek = startOfMonth.day();
  const daysInMonth = endOfMonth.date();

  for (let i = 0; i < startWeek; i++) html.push('<div></div>');
  for (let day = 1; day <= daysInMonth; day++) {
    const date = currentMonth.clone().date(day).format('YYYY-MM-DD');
    const data = vacancyData[date] || { vacancy: '-', avg_price: '-', previous_vacancy: '-', previous_avg_price: '-' };
    const vacDiff = data.vacancy !== '-' && data.previous_vacancy !== '-' ? data.vacancy - data.previous_vacancy : null;
    const priceDiff = data.avg_price !== '-' && data.previous_avg_price !== '-' ? 
      Math.round(data.avg_price - data.previous_avg_price) : null;
    const events = eventData.filter(e => e.date === date);
    const demand = calculateDemand(data.vacancy, data.avg_price);
    const isHoliday = [0].includes(moment(date).day()) || Math.random() > 0.9;

    html.push(`
      <div class="p-2 border rounded relative hover:bg-gray-100 ${isHoliday ? 'bg-red-100' : ''}" onclick="showGraph('${date}')">
        <div class="text-right">${day}</div>
        <div>空室: ${data.vacancy !== '-' ? data.vacancy : 'N/A'} ${vacDiff !== null ? `(${vacDiff >= 0 ? '↑' : '↓'}${Math.abs(vacDiff)})` : ''}</div>
        <div>価格: ${data.avg_price !== '-' ? `¥${data.avg_price.toLocaleString()}` : 'N/A'} ${priceDiff !== null ? `(${priceDiff >= 0 ? '↑' : '↓'}¥${Math.abs(priceDiff).toLocaleString()})` : ''}</div>
        ${events.map(e => `<div class="text-xs">${e.icon} ${e.name}</div>`).join('')}
        ${demand > 0 ? `<div class="text-orange-500">🔥${'★'.repeat(demand)}</div>` : ''}
      </div>`);
  }
  calendarEl.innerHTML = html.join('');
}

function changeMonth(offset) {
  currentMonth.add(offset, 'months');
  renderCalendar();
}

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
      labels: graphData.map(d => d.date),
      datasets: [
        { label: '平均価格', data: graphData.map(d => d.avg_price), borderColor: 'blue', yAxisID: 'y1', fill: false },
        { label: '空室数', data: graphData.map(d => d.vacancy), borderColor: 'green', yAxisID: 'y2', fill: false }
      ]
    },
    options: {
      responsive: true,
      scales: {
        x: { title: { display: true, text: '日付' } },
        y1: { type: 'linear', position: 'left', title: { display: true, text: '価格 (¥)' }, ticks: { callback: v => `¥${v.toLocaleString()}` } },
        y2: { type: 'linear', position: 'right', title: { display: true, text: '空室数' }, grid: { drawOnChartArea: false } }
      },
      plugins: { legend: { position: 'top' } }
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
