/**
 * AlgoTrader — Reusable Calendar Component
 * Renders a 5-column (Mon-Fri) calendar with P&L colored cells.
 * Usage: new AlgoCalendar(containerId, algoId, onDateClick)
 */
class AlgoCalendar {
  constructor(containerId, algoId, onDateClick) {
    this.container   = document.getElementById(containerId);
    this.algoId      = algoId;  // "algo1", "algo2", "algo3", or "all"
    this.onDateClick = onDateClick || function(){};
    this.year        = new Date().getFullYear();
    this.month       = new Date().getMonth() + 1; // 1-based
    this.selectedDate = null;
    this.dailyPnl    = {};
    this.monthlyTotal = 0;
    this.monthlyPct   = 0;
    this.render();
    this.loadData();
  }

  async loadData() {
    try {
      const endpoint = this.algoId === 'all'
        ? `/api/calendar/all/${this.year}/${this.month}`
        : `/api/calendar/${this.algoId}/${this.year}/${this.month}`;
      const res  = await fetch(endpoint);
      const data = await res.json();
      this.dailyPnl     = this.algoId === 'all' ? (data.combined_pnl || {}) : (data.daily_pnl || {});
      this.monthlyTotal = data.monthly_total || 0;
      this.monthlyPct   = data.monthly_pct || 0;
      this.render();
    } catch(e) {
      console.warn('Calendar load error:', e);
    }
  }

  prevMonth() {
    this.month--;
    if (this.month < 1) { this.month = 12; this.year--; }
    this.loadData();
  }

  nextMonth() {
    this.month++;
    if (this.month > 12) { this.month = 1; this.year++; }
    this.loadData();
  }

  selectDate(dateStr) {
    this.selectedDate = dateStr;
    this.render();
    this.onDateClick(dateStr);
  }

  _monthName(m) {
    return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1];
  }

  _daysInMonth(y, m) {
    return new Date(y, m, 0).getDate();
  }

  // Day of week: 1=Mon, 2=Tue, ..., 5=Fri (skip weekends)
  _dayOfWeek(y, m, d) {
    const dow = new Date(y, m-1, d).getDay(); // 0=Sun, 1=Mon...6=Sat
    return dow; // 1-5 = weekday
  }

  _formatPnl(v) {
    if (!v || v === 0) return '';
    const abs  = Math.abs(v);
    const sign = v > 0 ? '+' : '-';
    if (abs >= 100000) return sign + '₹' + (abs/100000).toFixed(1) + 'L';
    if (abs >= 1000)   return sign + '₹' + (abs/1000).toFixed(1) + 'K';
    return sign + '₹' + Math.round(abs);
  }

  render() {
    if (!this.container) return;
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    const totalColor = this.monthlyTotal >= 0 ? 'text-green' : 'text-red';
    const totalSign  = this.monthlyTotal >= 0 ? '+' : '';

    let html = `
      <div class="calendar-header">
        <button class="cal-nav-btn" onclick="this.closest('[data-cal]').__cal.prevMonth()">&#8249;</button>
        <div>
          <div class="calendar-month">${this._monthName(this.month)} ${this.year}</div>
          <div class="calendar-month-return ${totalColor}">
            ${totalSign}${this._formatPnl(this.monthlyTotal)}
            ${this.monthlyPct ? `(${totalSign}${this.monthlyPct}%)` : ''}
          </div>
        </div>
        <button class="cal-nav-btn" onclick="this.closest('[data-cal]').__cal.nextMonth()">&#8250;</button>
      </div>
      <div class="calendar-grid">
        <div class="cal-day-header">MON</div>
        <div class="cal-day-header">TUE</div>
        <div class="cal-day-header">WED</div>
        <div class="cal-day-header">THU</div>
        <div class="cal-day-header">FRI</div>
    `;

    const totalDays = this._daysInMonth(this.year, this.month);
    // Find what weekday day 1 falls on (0=Sun,1=Mon..5=Fri,6=Sat)
    const firstDow = new Date(this.year, this.month - 1, 1).getDay();
    // Offset to Mon=0 grid: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4
    let startOffset = (firstDow === 0) ? 4 : firstDow - 1; // Sun maps to 4 (treat as Fri placeholder)
    if (firstDow === 6) startOffset = 5; // Sat: skip whole row basically

    // Fill empty cells before first weekday
    for (let i = 0; i < Math.min(startOffset, 5); i++) {
      html += `<div class="cal-day empty"></div>`;
    }

    for (let d = 1; d <= totalDays; d++) {
      const dow = new Date(this.year, this.month - 1, d).getDay();
      if (dow === 0 || dow === 6) continue; // skip weekends

      const dateStr = `${this.year}-${String(this.month).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
      const pnl     = this.dailyPnl[dateStr] || 0;
      const hasPnl  = pnl !== 0;
      const isToday = dateStr === todayStr;
      const isSel   = dateStr === this.selectedDate;

      let cls = 'cal-day';
      if (isToday) cls += ' today';
      if (isSel)   cls += ' selected';
      if (hasPnl && pnl > 0) cls += ' profit';
      if (hasPnl && pnl < 0) cls += ' loss';

      const pnlStr = hasPnl ? `<div class="cal-pnl ${pnl>0?'text-green':'text-red'}">${this._formatPnl(pnl)}</div>` : '';

      html += `
        <div class="${cls}" onclick="this.closest('[data-cal]').__cal.selectDate('${dateStr}')">
          <div class="cal-date">${d}</div>
          ${pnlStr}
        </div>
      `;
    }

    html += `</div>`;
    this.container.setAttribute('data-cal', '1');
    this.container.innerHTML = html;
    this.container.__cal = this;
  }
}
