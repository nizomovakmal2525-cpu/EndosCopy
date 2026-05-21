(function () {
  const adminMenu = [
    ['dashboard', 'Dashboard'],
    ['users', 'Users'],
    ['analyses', 'Analyses'],
    ['review-queue', 'Review Queue'],
    ['dataset', 'Dataset'],
    ['model-stats', 'Model Stats'],
    ['reports', 'Reports'],
    ['news-manager', 'News Manager'],
    ['activity-logs', 'Activity Logs'],
    ['messages', 'Messages'],
    ['settings', 'Settings']
  ];

  const userMenu = [
    ['snapshot', 'My Snapshot'],
    ['scan-library', 'Scan Library'],
    ['ai-insights', 'AI Insights'],
    ['risk-map', 'Risk Map'],
    ['confidence-pulse', 'Confidence Pulse'],
    ['timeline', 'Timeline'],
    ['reports', 'My Reports'],
    ['profile', 'Profile']
  ];

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, ch => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    }[ch]));
  }

  function sectionBase(scope) {
    return scope === 'admin' ? '/admin' : '/dashboard';
  }

  function renderMenu(scope, active) {
    const nav = $('statsNav');
    if (!nav) return;
    const menu = scope === 'admin' ? adminMenu : userMenu;
    const base = sectionBase(scope);
    nav.innerHTML = menu.map(([key, label]) => `
      <button class="stats-nav-item ${key === active ? 'active' : ''}" type="button" data-target="${base}/${key}">
        <span>${escapeHtml(label)}</span>
      </button>
    `).join('') + `
      <button class="stats-nav-item muted" type="button" data-target="/logout">
        <span>Logout</span>
      </button>
    `;
    nav.querySelectorAll('[data-target]').forEach(btn => {
      btn.addEventListener('click', () => {
        window.location.href = btn.getAttribute('data-target');
      });
    });
  }

  function renderCards(cards) {
    const grid = $('statsCards');
    if (!grid) return;
    grid.innerHTML = (cards || []).map(card => `
      <article class="stats-card ${card.target ? 'clickable' : ''}" ${card.target ? `data-target="${escapeHtml(card.target)}"` : ''}>
        <div class="stats-card-label">${escapeHtml(card.label)}</div>
        <div class="stats-card-value">${escapeHtml(card.value)}</div>
        <div class="stats-card-detail">${escapeHtml(card.detail)}</div>
      </article>
    `).join('');
    grid.querySelectorAll('[data-target]').forEach(card => {
      card.addEventListener('click', () => {
        window.location.href = card.getAttribute('data-target');
      });
    });
  }

  function renderFilters(filters) {
    const wrap = $('statsFilters');
    if (!wrap) return;
    if (!filters || !filters.length) {
      wrap.innerHTML = '';
      wrap.style.display = 'none';
      return;
    }
    wrap.style.display = 'flex';
    wrap.innerHTML = filters.map(filter => `
      <button class="stats-filter" type="button">${escapeHtml(filter)}</button>
    `).join('');
  }

  function renderLineChart(chart) {
    const items = chart.items || [];
    if (!items.length) return '';
    const values = items.map(item => Number(item[1]) || 0);
    const max = Math.max(...values, 100);
    const min = Math.min(...values, 0);
    const width = 520;
    const height = 180;
    const step = items.length > 1 ? width / (items.length - 1) : width;
    const points = values.map((value, index) => {
      const x = index * step;
      const y = height - ((value - min) / Math.max(max - min, 1)) * (height - 28) - 14;
      return `${x},${y}`;
    }).join(' ');

    return `
      <div class="stats-chart-card">
        <div class="stats-panel-title">${escapeHtml(chart.title)}</div>
        <svg class="stats-line-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
          <polyline points="${points}" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline>
        </svg>
        <div class="stats-chart-labels">
          ${items.map(item => `<span>${escapeHtml(item[0])}</span>`).join('')}
        </div>
      </div>
    `;
  }

  function renderBarChart(chart) {
    const items = chart.items || [];
    const max = Math.max(...items.map(item => Number(item[1]) || 0), 1);
    const title = String(chart.title || '');
    const showPercent = /Risk Distribution|Result Balance|Train \/ Validation \/ Test Split|Class Performance/.test(title);
    return `
      <div class="stats-chart-card">
        <div class="stats-panel-title">${escapeHtml(chart.title)}</div>
        <div class="stats-bars">
          ${items.map(item => {
            const value = Number(item[1]) || 0;
            const pct = Math.round((value / max) * 100);
            return `
              <div class="stats-bar-row">
                <span>${escapeHtml(item[0])}</span>
                <div class="stats-bar-track"><i style="width:${pct}%"></i></div>
                <b>${escapeHtml(item[1])}${showPercent ? '%' : ''}</b>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  function renderCharts(charts) {
    const grid = $('statsCharts');
    if (!grid) return;
    grid.innerHTML = (charts || []).map(chart => {
      return chart.type === 'line' ? renderLineChart(chart) : renderBarChart(chart);
    }).join('');
  }

  function renderTable(table, detailTarget) {
    const wrap = $('statsTable');
    if (!wrap) return;
    if (!table) {
      wrap.innerHTML = '';
      wrap.style.display = 'none';
      return;
    }
    wrap.style.display = 'block';
    wrap.innerHTML = `
      <div class="stats-panel-title">${escapeHtml(table.title || 'Records')}</div>
      <div class="stats-table-wrap">
        <table class="stats-table">
          <thead>
            <tr>${(table.columns || []).map(col => `<th>${escapeHtml(col)}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${(table.rows || []).map(row => `
              <tr ${detailTarget ? `data-row-target="${escapeHtml(detailTarget)}"` : ''}>${row.map(cell => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      ${(table.actions || []).length ? `
        <div class="stats-action-row">
          ${table.actions.map(action => `<button class="stats-action" type="button">${escapeHtml(action)}</button>`).join('')}
        </div>
      ` : ''}
    `;
    wrap.querySelectorAll('[data-row-target]').forEach(row => {
      row.addEventListener('click', () => {
        window.location.href = row.getAttribute('data-row-target');
      });
    });
  }

  function renderNotes(notes) {
    const wrap = $('statsNotes');
    if (!wrap) return;
    if (!notes || !notes.length) {
      wrap.innerHTML = '';
      wrap.style.display = 'none';
      return;
    }
    wrap.style.display = 'block';
    wrap.innerHTML = `
      <div class="stats-panel-title">AI Notes</div>
      <ul class="stats-notes">
        ${(notes || []).map(note => `<li>${escapeHtml(note)}</li>`).join('')}
      </ul>
    `;
  }

  function renderPanels(panels) {
    const grid = $('statsPanels');
    if (!grid) return;
    if (!panels || !panels.length) {
      grid.innerHTML = '';
      grid.style.display = 'none';
      return;
    }
    grid.style.display = 'grid';
    grid.innerHTML = panels.map(panel => `
      <section class="stats-panel">
        <div class="stats-panel-title">${escapeHtml(panel.title)}</div>
        <div class="stats-kv-list">
          ${(panel.items || []).map(item => renderPanelItem(panel.title, item)).join('')}
        </div>
      </section>
    `).join('');
  }

  function renderPanelItem(title, item) {
    const key = String(item[0] || '');
    const value = String(item[1] || '');
    const imageValue = value.replace(/\\/g, '/');
    const isImage = /Uploaded Image/i.test(title) && /^(\/uploads\/|uploads\/)/.test(imageValue);
    if (isImage) {
      const src = imageValue.startsWith('/') ? imageValue : `/${imageValue}`;
      return `
        <div class="stats-image-preview">
          <img src="${escapeHtml(src)}" alt="Uploaded analysis image">
        </div>
      `;
    }
    return `
      <div class="stats-kv-row">
        <span>${escapeHtml(key)}</span>
        <b>${escapeHtml(value)}</b>
      </div>
    `;
  }

  function renderTimeline(items) {
    const wrap = $('statsTimeline');
    if (!wrap) return;
    if (!items || !items.length) {
      wrap.innerHTML = '';
      wrap.style.display = 'none';
      return;
    }
    wrap.style.display = 'block';
    wrap.innerHTML = `
      <div class="stats-panel-title">Timeline</div>
      <div class="stats-timeline-list">
        ${items.map(item => `
          <div class="stats-timeline-item">
            <span>${escapeHtml(item.date)}</span>
            <b>${escapeHtml(item.title)}</b>
            <p>${escapeHtml(item.detail)}</p>
          </div>
        `).join('')}
      </div>
    `;
  }

  function renderForm(form) {
    const wrap = $('statsForm');
    if (!wrap) return;
    if (!form) {
      wrap.innerHTML = '';
      wrap.style.display = 'none';
      return;
    }
    wrap.style.display = 'block';
    wrap.innerHTML = `
      <div class="stats-panel-title">${escapeHtml(form.title)}</div>
      <div class="stats-form-grid">
        ${(form.fields || []).map(field => `
          <label class="stats-form-field">
            <span>${escapeHtml(field[0])}</span>
            <input type="text" value="${escapeHtml(field[1])}" readonly>
          </label>
        `).join('')}
      </div>
      ${(form.included || []).length ? `
        <div class="stats-check-list">
          ${form.included.map(item => `<label><input type="checkbox" checked readonly> ${escapeHtml(item)}</label>`).join('')}
        </div>
      ` : ''}
      ${(form.actions || []).length ? `
        <div class="stats-action-row">
          ${form.actions.map(action => `<button class="stats-action" type="button">${escapeHtml(action)}</button>`).join('')}
        </div>
      ` : ''}
    `;
  }

  function renderNotifications(notifications) {
    const wrap = $('statsNotifications');
    const menu = $('statsNotificationMenu');
    const badge = $('statsNotificationBadge');
    const button = $('statsNotificationButton');
    const items = notifications || [];
    if (badge) {
      badge.textContent = String(items.length);
      badge.style.display = items.length ? 'grid' : 'none';
    }
    if (menu) {
      menu.innerHTML = `
        <div class="stats-panel-title">Notifications</div>
        ${items.length ? `
          <ul class="stats-notifications-list compact">
            ${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
          </ul>
        ` : '<p class="stats-empty-text">No notifications</p>'}
      `;
    }
    if (button) {
      button.setAttribute('aria-label', `${items.length} notifications`);
    }
    if (!wrap) return;
    if (!notifications || !notifications.length) {
      wrap.innerHTML = '';
      wrap.style.display = 'none';
      return;
    }
    wrap.style.display = 'block';
    wrap.innerHTML = `
      <div class="stats-panel-title">Notifications</div>
      <ul class="stats-notifications-list">
        ${notifications.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
      </ul>
    `;
  }

  function initNotificationMenu() {
    const shell = document.querySelector('.stats-notification-shell');
    const button = $('statsNotificationButton');
    if (!shell || !button) return;
    button.addEventListener('click', event => {
      event.stopPropagation();
      const open = shell.classList.toggle('open');
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.addEventListener('click', event => {
      if (!shell.contains(event.target)) {
        shell.classList.remove('open');
        button.setAttribute('aria-expanded', 'false');
      }
    });
  }

  function renderGlobalActions(actions) {
    const wrap = $('statsActions');
    if (!wrap) return;
    if (!actions || !actions.length) {
      wrap.innerHTML = '';
      wrap.style.display = 'none';
      return;
    }
    wrap.style.display = 'flex';
    wrap.innerHTML = actions.map(action => `
      <button class="stats-action" type="button">${escapeHtml(action)}</button>
    `).join('');
  }

  async function loadStats() {
    const body = document.body;
    const scope = body.getAttribute('data-stats-scope');
    const section = body.getAttribute('data-stats-section');
    if (!scope || !section) return;

    renderMenu(scope, section);
    const userName = body.getAttribute('data-current-user') || 'User';
    const profile = $('statsProfileName');
    if (profile) profile.textContent = userName;

    try {
      const response = await fetch(`/api/stats/${scope}/${section}`);
      if (response.status === 401) {
        window.location.href = '/login';
        return;
      }
      if (!response.ok) throw new Error('Stats request failed');
      const data = await response.json();
      const title = $('statsTitle');
      const subtitle = $('statsSubtitle');
      const search = document.querySelector('.stats-search');
      if (title) title.textContent = scope === 'user' && data.section === 'snapshot'
        ? `${data.title}, ${userName}`
        : data.title;
      if (subtitle) subtitle.textContent = data.subtitle;
      if (search && data.searchPlaceholder) search.placeholder = data.searchPlaceholder;
      renderCards(data.cards);
      renderFilters(data.filters);
      renderCharts(data.charts);
      renderTable(data.table, data.detailTarget);
      renderNotes(data.notes);
      renderPanels(data.panels);
      renderTimeline(data.timeline);
      renderForm(data.form);
      renderNotifications(data.notifications);
      renderGlobalActions(data.actions);
    } catch (err) {
      const subtitle = $('statsSubtitle');
      if (subtitle) subtitle.textContent = 'Statistika service bilan aloqa vaqtincha mavjud emas.';
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    initNotificationMenu();
    loadStats();
  });
})();
