const AUTH_KEY = 'verity_token';

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function formatTime(value) {
  if (!value || value === 'never') return 'Never';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

async function fetchJson(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getStoredToken();
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData) && options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(url, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || 'Request failed');
  }
  return payload;
}

function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.remove('hidden');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toast.classList.add('hidden'), 2400);
}

function getStoredToken() {
  return localStorage.getItem(AUTH_KEY) || '';
}

function setAuthState(token, profile) {
  if (token) {
    localStorage.setItem(AUTH_KEY, token);
  } else {
    localStorage.removeItem(AUTH_KEY);
  }
  const statusPill = document.querySelector('#authStatus .status-pill');
  if (!statusPill) return;
  if (token && profile) {
    statusPill.textContent = `${profile.name} · ${profile.role}`;
    statusPill.className = 'status-pill online';
  } else {
    statusPill.textContent = 'Not signed in';
    statusPill.className = 'status-pill offline';
  }
}

function setView(view) {
  document.querySelectorAll('[data-view-panel]').forEach((panel) => {
    panel.classList.toggle('hidden', panel.dataset.viewPanel !== view);
  });
  document.querySelectorAll('.nav-item').forEach((button) => {
    button.classList.toggle('active', button.dataset.view === view);
  });
}

function bindNavigation() {
  document.querySelectorAll('.nav-item').forEach((button) => {
    button.addEventListener('click', () => setView(button.dataset.view));
  });
}

function renderAuthMode(isLoggedIn, profile = null) {
  const authPanel = document.getElementById('authPanel');
  const workspacePanel = document.getElementById('workspacePanel');
  authPanel?.classList.toggle('hidden', isLoggedIn);
  workspacePanel?.classList.toggle('hidden', !isLoggedIn);
  if (profile) {
    const workerTitle = document.getElementById('workerTitle');
    if (workerTitle) workerTitle.textContent = `${profile.name}'s verification board`;
  }
}

function renderWorkspaceSummary(workspace) {
  const workspaceSummary = document.getElementById('workspaceSummary');
  if (!workspaceSummary) return;
  const summary = workspace.summary || {};
  workspaceSummary.innerHTML = `
    <div class="summary-box"><span>Total tasks</span><strong>${summary.total_tasks ?? 0}</strong></div>
    <div class="summary-box"><span>Queued</span><strong>${summary.queued ?? 0}</strong></div>
    <div class="summary-box"><span>In review</span><strong>${summary.in_review ?? 0}</strong></div>
    <div class="summary-box"><span>Verified</span><strong>${summary.verified ?? 0}</strong></div>
  `;
}

function renderWatchlists(items) {
  const grid = document.getElementById('watchlistGrid');
  if (!grid) return;
  if (!items?.length) {
    grid.innerHTML = '<span class="chip">No watchlists yet</span>';
    return;
  }
  grid.innerHTML = items.map((item) => `<span class="chip">${escapeHtml(item.name)}</span>`).join('');
}

function renderTasks(tasks) {
  const taskList = document.getElementById('taskList');
  if (!taskList) return;
  if (!tasks?.length) {
    taskList.innerHTML = '<div class="task-card empty">No live tasks are assigned right now.</div>';
    return;
  }

  taskList.innerHTML = tasks.map((task) => `
    <article class="task-card">
      <div class="task-header">
        <div>
          <div class="task-provider">${escapeHtml(task.provider)}</div>
          <h3>${escapeHtml(task.title)}</h3>
        </div>
        <span class="status-badge ${escapeHtml(task.status)}">${escapeHtml(task.status)}</span>
      </div>
      <p class="task-summary">${escapeHtml(task.summary)}</p>
      <div class="chip-row">
        ${(task.signals || []).map((signal) => `<span class="chip">${escapeHtml(signal)}</span>`).join('')}
      </div>
      <div class="task-meta">
        <span>Priority: <strong>${escapeHtml(task.priority)}</strong></span>
        <span>Category: <strong>${escapeHtml(task.category)}</strong></span>
      </div>
      <div class="task-actions">
        <form class="inline-form attempt-form">
          <input type="hidden" name="task_id" value="${escapeHtml(task.id)}" />
          <input type="text" name="approach" placeholder="Approach used" value="${escapeHtml(task.approaches?.[0] || '')}" required />
          <textarea name="notes" placeholder="What did the official page say? Quote eligibility, dates, and limits." required></textarea>
          <button type="submit" class="secondary-btn">Submit attempt</button>
        </form>
        <form class="inline-form review-form">
          <input type="hidden" name="task_id" value="${escapeHtml(task.id)}" />
          <select name="decision">
            <option value="approved">Approved as public/official</option>
            <option value="rejected">Rejected / not public</option>
            <option value="needs-review">Needs another pass</option>
          </select>
          <textarea name="notes" placeholder="Decision notes" required></textarea>
          <button type="submit" class="primary-btn">Submit review</button>
        </form>
      </div>
      <div class="attempt-list">
        ${(task.attempts || []).map((attempt) => `
          <div class="attempt-item">
            <div class="attempt-header">
              <span>${escapeHtml(attempt.approach)}</span>
              <small>${escapeHtml(formatTime(attempt.created_at))}</small>
            </div>
            <p>${escapeHtml(attempt.notes)}</p>
          </div>
        `).join('') || '<div class="attempt-item empty">No attempts yet.</div>'}
      </div>
      ${task.review ? `
        <div class="review-box">
          <div class="review-header">
            <strong>${escapeHtml(task.review.decision)}</strong>
            <small>${escapeHtml(formatTime(task.review.reviewed_at))}</small>
          </div>
          <p>${escapeHtml(task.review.notes)}</p>
        </div>
      ` : ''}
    </article>
  `).join('');

  taskList.querySelectorAll('.attempt-form').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        await fetchJson('/api/workspace/attempt', {
          method: 'POST',
          body: JSON.stringify({
            task_id: formData.get('task_id'),
            approach: formData.get('approach'),
            notes: formData.get('notes')
          })
        });
        await loadWorkspace();
        showToast('Attempt saved');
      } catch (error) {
        showToast(error.message || 'Attempt failed');
      }
    });
  });

  taskList.querySelectorAll('.review-form').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        await fetchJson('/api/workspace/review', {
          method: 'POST',
          body: JSON.stringify({
            task_id: formData.get('task_id'),
            decision: formData.get('decision'),
            notes: formData.get('notes')
          })
        });
        await loadWorkspace();
        showToast('Review recorded');
      } catch (error) {
        showToast(error.message || 'Review failed');
      }
    });
  });
}

async function loadWorkspace() {
  const token = getStoredToken();
  if (!token) {
    renderAuthMode(false);
    setAuthState('', null);
    return null;
  }
  try {
    const data = await fetchJson('/api/workspace');
    setAuthState(token, data.profile);
    renderAuthMode(true, data.profile);
    renderWorkspaceSummary(data.workspace);
    renderTasks(data.workspace.tasks);
    const lists = await fetchJson('/api/watchlists');
    renderWatchlists(lists);
    return data.workspace;
  } catch (error) {
    setAuthState('', null);
    renderAuthMode(false);
    return null;
  }
}

async function loadDashboard() {
  const statsGrid = document.getElementById('statsGrid');
  const providersGrid = document.getElementById('providersGrid');
  const researchSummary = document.getElementById('researchSummary');
  const offersGrid = document.getElementById('offersGrid');
  const alertsGrid = document.getElementById('alertsGrid');
  const insightsGrid = document.getElementById('insightsGrid');
  const searchInput = document.getElementById('searchInput');
  const sourcesTable = document.getElementById('sourcesTable');
  const signalsGrid = document.getElementById('signalsGrid');

  const [summary, offers, providers, research, alerts, insights, analytics, sources, signals] = await Promise.all([
    fetchJson('/api/summary'),
    fetchJson('/api/offers'),
    fetchJson('/api/providers'),
    fetchJson('/api/research'),
    fetchJson('/api/alerts'),
    fetchJson('/api/insights'),
    fetchJson('/api/analytics'),
    fetchJson('/api/sources'),
    fetchJson('/api/signals')
  ]);

  let logs = [];
  if (getStoredToken()) {
    try {
      logs = await fetchJson('/api/audit');
    } catch {
      logs = [];
    }
  }

  document.getElementById('heroReachable').textContent = `${research.checked_sources ?? 0}/${research.total_sources ?? 0}`;
  document.getElementById('heroReachableNote').textContent = research.last_scan === 'never'
    ? 'Awaiting first scan'
    : `Last scan ${formatTime(research.last_scan)}`;
  document.getElementById('heroConfidence').textContent = summary.high_confidence ?? 0;
  document.getElementById('heroQueue').textContent = (analytics.pipeline || []).slice(0, 2).reduce((sum, row) => sum + (row.value || 0), 0);
  document.getElementById('scanFreshness').textContent = research.last_scan === 'never'
    ? 'Scan idle'
    : `Updated ${formatTime(research.last_scan)}`;

  statsGrid.innerHTML = [
    { label: 'Total offers', value: summary.total_offers, note: 'Tracked programs' },
    { label: 'Active', value: summary.active_offers, note: 'Listed as currently public' },
    { label: 'High confidence', value: summary.high_confidence, note: 'Verified official programs' },
    { label: 'Needs review', value: summary.needs_review, note: 'Human confirmation still open' }
  ].map((item) => `
    <article class="stat-card">
      <div class="stat-label">${item.label}</div>
      <div class="stat-value">${item.value}</div>
      <div class="stat-note">${item.note}</div>
    </article>
  `).join('');

  const renderProviders = (filtered = providers) => {
    providersGrid.innerHTML = filtered.map((provider) => `
      <article class="provider-card" data-provider-id="${escapeHtml(provider.id)}" tabindex="0" role="button" aria-label="Open provider details for ${escapeHtml(provider.name)}">
        <div class="provider-top">
          <div class="provider-name">${escapeHtml(provider.name)}</div>
          <span class="status-badge ${escapeHtml(provider.status)}">${escapeHtml(provider.status)}</span>
        </div>
        <div class="provider-coverage">${escapeHtml(provider.research_coverage)}%</div>
        <div class="provider-meta">
          <div><strong>Signal:</strong> ${escapeHtml(provider.signal)}</div>
          <div><strong>Sources:</strong> ${escapeHtml(provider.source_count)}</div>
        </div>
      </article>
    `).join('');
    providersGrid.querySelectorAll('.provider-card').forEach((card) => {
      card.addEventListener('click', () => openProviderDetail(card.dataset.providerId));
      card.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openProviderDetail(card.dataset.providerId);
        }
      });
    });
  };

  insightsGrid.innerHTML = `
    <article class="insight-card highlight">
      <div class="muted-label">Momentum</div>
      <div class="insight-value">${escapeHtml(insights.momentum_score)}</div>
      <div class="insight-copy">${escapeHtml(insights.summary)}</div>
    </article>
    ${(insights.signals || []).map((signal) => `
      <article class="insight-card">
        <div class="muted-label">Signal</div>
        <div class="insight-title">${escapeHtml(signal.title)}</div>
        <div class="insight-value small">${escapeHtml(signal.value)}</div>
        <span class="signal-pill ${escapeHtml(signal.status)}">${escapeHtml(signal.status)}</span>
      </article>
    `).join('')}
  `;

  alertsGrid.innerHTML = alerts.map((alert) => `
    <article class="alert-card">
      <div class="alert-title">${escapeHtml(alert.title)}</div>
      <div class="alert-message">${escapeHtml(alert.message)}</div>
      <span class="alert-severity ${escapeHtml(alert.severity)}">${escapeHtml(alert.severity)} · ${escapeHtml(alert.provider || '')}</span>
    </article>
  `).join('');

  const logsGrid = document.getElementById('logsGrid');
  if (!getStoredToken()) {
    logsGrid.innerHTML = '<div class="alert-card"><div class="alert-message">Sign in to see desk activity.</div></div>';
  } else if (!logs.length) {
    logsGrid.innerHTML = '<div class="alert-card"><div class="alert-message">No activity recorded yet.</div></div>';
  } else {
    logsGrid.innerHTML = logs.map((entry) => `
      <article class="alert-card">
        <div class="alert-title">${escapeHtml(entry.action)}</div>
        <div class="alert-message">${escapeHtml(entry.entity_type)} ${escapeHtml(entry.entity_id || '')} · ${escapeHtml(formatTime(entry.created_at))}</div>
      </article>
    `).join('');
  }

  sourcesTable.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Provider</th>
          <th>Type</th>
          <th>Status</th>
          <th>HTTP</th>
          <th>Last checked</th>
          <th>Page</th>
        </tr>
      </thead>
      <tbody>
        ${sources.map((source) => `
          <tr>
            <td>${escapeHtml(source.provider)}</td>
            <td>${escapeHtml(source.source_type)}</td>
            <td><span class="status-badge ${escapeHtml(source.status)}">${escapeHtml(source.status)}</span></td>
            <td>${escapeHtml(source.http_status ?? '—')}</td>
            <td>${escapeHtml(formatTime(source.last_checked_at))}</td>
            <td><a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">Open</a></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;

  if (!signals.length) {
    signalsGrid.innerHTML = '<div class="alert-card"><div class="alert-message">No extracted language yet. Sign in and run verification against official pages.</div></div>';
  } else {
    signalsGrid.innerHTML = signals.map((item) => `
      <article class="alert-card">
        <div class="alert-title">${escapeHtml(item.provider)} · ${escapeHtml(item.label)}</div>
        <div class="alert-message">${escapeHtml(item.snippet)}</div>
        <span class="alert-severity medium">weight ${escapeHtml(item.weight)}</span>
      </article>
    `).join('');
  }

  const pipeline = analytics.pipeline || [];
  const trend = analytics.trend || { labels: [], values: [] };
  researchSummary.innerHTML = `
    <div class="summary-row"><span>Total sources</span><strong>${research.total_sources}</strong></div>
    <div class="summary-row"><span>Checked</span><strong>${research.checked_sources}</strong></div>
    <div class="summary-row"><span>Failed</span><strong>${research.failed_sources}</strong></div>
    <div class="summary-row"><span>Coverage</span><strong>${research.coverage_percent}%</strong></div>
    <div class="summary-row"><span>Last scan</span><strong>${escapeHtml(formatTime(research.last_scan))}</strong></div>
    <div class="analytics-block">
      <div class="analytics-title">Review pipeline</div>
      ${pipeline.map((entry) => `
        <div class="pipeline-row">
          <div class="pipeline-header"><span>${escapeHtml(entry.label)}</span><strong>${entry.value}</strong></div>
          <div class="pipeline-bar"><span style="width:${entry.percent}%"></span></div>
        </div>
      `).join('')}
    </div>
    <div class="analytics-block">
      <div class="analytics-title">Recent provider scans</div>
      <div class="trend-chart">
        ${trend.labels.map((label, index) => `
          <div class="trend-point">
            <span class="trend-bar" style="height:${Math.max(10, (trend.values[index] || 0) * 0.8)}px"></span>
            <small>${escapeHtml(label)}</small>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  const renderOffers = (filtered = offers) => {
    offersGrid.innerHTML = filtered.map((offer) => `
      <article class="offer-card">
        <div class="offer-top">
          <div class="offer-provider">${escapeHtml(offer.provider)}</div>
          <span class="status-badge ${escapeHtml(offer.status)}">${escapeHtml(offer.status)}</span>
        </div>
        <div class="offer-product">${escapeHtml(offer.product)}</div>
        <div class="offer-meta">
          <span><strong>Reward:</strong> ${escapeHtml(offer.reward)}</span>
          <span><strong>Eligibility:</strong> ${escapeHtml(offer.eligibility)}</span>
          <span><strong>Source:</strong> ${escapeHtml(offer.source)}</span>
        </div>
        <div class="score-row">
          <span class="score-pill">score ${escapeHtml(offer.score)}</span>
          <span>${offer.official ? 'Official' : 'Unofficial'}</span>
        </div>
      </article>
    `).join('');
  };

  const filterDashboard = () => {
    const query = searchInput.value.trim().toLowerCase();
    renderProviders(providers.filter((provider) => `${provider.name} ${provider.signal} ${provider.category}`.toLowerCase().includes(query) || !query));
    renderOffers(offers.filter((offer) => `${offer.provider} ${offer.product} ${offer.reward} ${offer.eligibility}`.toLowerCase().includes(query) || !query));
  };

  renderProviders();
  renderOffers();
  searchInput.oninput = filterDashboard;
}

async function openProviderDetail(providerId) {
  const modal = document.getElementById('providerModal');
  const content = document.getElementById('providerModalContent');
  if (!modal || !content) return;
  modal.classList.remove('hidden');
  modal.setAttribute('aria-hidden', 'false');
  content.innerHTML = '<div class="modal-loading">Loading provider intelligence…</div>';
  try {
    const provider = await fetchJson(`/api/providers/${providerId}`);
    const sourceMarkup = (provider.sources || []).map((source) => {
      const label = typeof source === 'string' ? source : `${source.source_type} · ${source.status || 'pending'}`;
      const url = typeof source === 'string' ? '' : source.url;
      return `<li>${escapeHtml(label)}${url ? ` — <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">open</a>` : ''}</li>`;
    }).join('');
    const offerMarkup = (provider.offers || []).map((offer) => `
      <div class="modal-offer-row">
        <div>
          <strong>${escapeHtml(offer.product)}</strong>
          <span>${escapeHtml(offer.reward)}</span>
        </div>
        <span class="score-pill">${escapeHtml(offer.score)}</span>
      </div>
    `).join('') || '<p class="modal-empty">No matching offers at the moment.</p>';
    const signalMarkup = (provider.live_signals || []).map((item) => `
      <p class="modal-empty"><strong>${escapeHtml(item.label)}</strong> — ${escapeHtml(item.snippet)}</p>
    `).join('') || '<p class="modal-empty">No live language extracted yet.</p>';

    content.innerHTML = `
      <div class="modal-header">
        <div>
          <p class="eyebrow">Provider detail</p>
          <h3 id="providerModalTitle">${escapeHtml(provider.name)}</h3>
        </div>
        <span class="status-badge ${escapeHtml(provider.status)}">${escapeHtml(provider.status)}</span>
      </div>
      <div class="modal-grid">
        <div class="modal-section">
          <div class="modal-label">Coverage</div>
          <div class="modal-value">${escapeHtml(provider.research_coverage)}%</div>
          <p>${escapeHtml(provider.notes)}</p>
        </div>
        <div class="modal-section">
          <div class="modal-label">Signals</div>
          <div class="modal-value small">${escapeHtml(provider.signal)}</div>
        </div>
      </div>
      <div class="modal-list-block">
        <div class="modal-label">Source channels</div>
        <ul class="source-list">${sourceMarkup}</ul>
      </div>
      <div class="modal-list-block">
        <div class="modal-label">Linked offers</div>
        ${offerMarkup}
      </div>
      <div class="modal-list-block">
        <div class="modal-label">Latest extracted language</div>
        ${signalMarkup}
      </div>
    `;
  } catch (error) {
    content.innerHTML = '<div class="modal-error">Unable to load provider detail.</div>';
  }
}

function bindModalControls() {
  const modal = document.getElementById('providerModal');
  if (!modal) return;
  modal.addEventListener('click', (event) => {
    if (event.target.dataset.close === 'true' || event.target.classList.contains('modal-close')) {
      modal.classList.add('hidden');
      modal.setAttribute('aria-hidden', 'true');
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      modal.classList.add('hidden');
      modal.setAttribute('aria-hidden', 'true');
    }
  });
}

function bindAuthForms() {
  const signupForm = document.getElementById('signupForm');
  const loginForm = document.getElementById('loginForm');
  const signOutBtn = document.getElementById('signOutBtn');
  const watchlistForm = document.getElementById('watchlistForm');

  signupForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(signupForm).entries());
    try {
      const result = await fetchJson('/api/auth/signup', { method: 'POST', body: JSON.stringify(payload) });
      setAuthState(result.token, { name: result.name, role: result.role });
      renderAuthMode(true, { name: result.name, role: result.role });
      renderWorkspaceSummary(result.workspace);
      renderTasks(result.workspace.tasks);
      signupForm.reset();
      showToast('Desk account created');
      setView('review');
    } catch (error) {
      showToast(error.message || 'Signup failed');
    }
  });

  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(loginForm).entries());
    try {
      const result = await fetchJson('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) });
      setAuthState(result.token, { name: result.name, role: result.role });
      await loadWorkspace();
      loginForm.reset();
      showToast('Signed in');
      setView('review');
    } catch (error) {
      showToast(error.message || 'Login failed');
    }
  });

  signOutBtn.addEventListener('click', () => {
    setAuthState('', null);
    renderAuthMode(false);
    showToast('Signed out');
  });

  watchlistForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const name = new FormData(watchlistForm).get('name');
    try {
      await fetchJson('/api/watchlists', { method: 'POST', body: JSON.stringify({ name, filters: {} }) });
      watchlistForm.reset();
      await loadWorkspace();
      showToast('Watchlist saved');
    } catch (error) {
      showToast(error.message || 'Could not save watchlist');
    }
  });
}

// Agent monitoring functions
async function loadAgentStatus() {
  try {
    const status = await fetchJson('/api/agents/status');
    renderAgentStatus(status);
  } catch (error) {
    console.error('Failed to load agent status:', error);
  }
}

function renderAgentStatus(status) {
  const orchestratorStatus = document.getElementById('orchestratorStatus');
  const orchestratorNote = document.getElementById('orchestratorNote');
  const queueStats = document.getElementById('queueStats');
  const activeAgents = document.getElementById('activeAgents');

  if (orchestratorStatus) {
    orchestratorStatus.textContent = status.status.charAt(0).toUpperCase() + status.status.slice(1);
  }
  if (orchestratorNote) {
    orchestratorNote.textContent = status.status === 'running' ? 'Active and monitoring' : 'Not running';
  }
  if (queueStats) {
    const pending = status.queue?.pending || 0;
    const completed = status.queue?.completed || 0;
    queueStats.textContent = `${pending} pending / ${completed} completed`;
  }
  if (activeAgents) {
    activeAgents.textContent = status.agents?.length || 0;
  }

  const startBtn = document.getElementById('startAgentsBtn');
  const stopBtn = document.getElementById('stopAgentsBtn');
  if (startBtn && stopBtn) {
    startBtn.classList.toggle('hidden', status.status === 'running');
    stopBtn.classList.toggle('hidden', status.status !== 'running');
  }
}

async function loadJobs(filter = 'all') {
  try {
    const response = await fetchJson(`/api/agents/jobs?status=${filter === 'all' ? '' : filter}&limit=20`);
    renderJobs(response.jobs);
  } catch (error) {
    console.error('Failed to load jobs:', error);
  }
}

function renderJobs(jobs) {
  const grid = document.getElementById('jobsGrid');
  if (!grid) return;

  if (!jobs || jobs.length === 0) {
    grid.innerHTML = '<p class="panel-empty">No jobs found.</p>';
    return;
  }

  grid.innerHTML = jobs.map(job => `
    <div class="job-card">
      <div class="job-card-header">
        <span class="job-type-badge">${escapeHtml(job.job_type)}</span>
        <span class="job-status ${escapeHtml(job.status)}">${escapeHtml(job.status)}</span>
      </div>
      <div class="job-details">
        <small><strong>Agent:</strong> ${escapeHtml(job.agent_type)}</small>
        <small><strong>Priority:</strong> ${job.priority}</small>
        <small><strong>Created:</strong> ${formatTime(job.created_at)}</small>
      </div>
      ${job.error_message ? `<p class="error-message"><strong>Error:</strong> ${escapeHtml(job.error_message)}</p>` : ''}
    </div>
  `).join('');
}

async function loadMemory(filter = 'all') {
  try {
    const response = await fetchJson(`/api/agents/memory?memory_type=${filter === 'all' ? '' : filter}&limit=20`);
    renderMemory(response.memories);
  } catch (error) {
    console.error('Failed to load memory:', error);
  }
}

function renderMemory(memories) {
  const grid = document.getElementById('memoryGrid');
  if (!grid) return;

  if (!memories || memories.length === 0) {
    grid.innerHTML = '<p class="panel-empty">No memories found.</p>';
    return;
  }

  grid.innerHTML = memories.map(mem => `
    <div class="memory-card">
      <div class="memory-card-header">
        <span class="memory-type-badge">${escapeHtml(mem.memory_type)}</span>
        <small>${formatTime(mem.created_at)}</small>
      </div>
      <div class="memory-content">${escapeHtml(mem.content.substring(0, 200))}${mem.content.length > 200 ? '...' : ''}</div>
      <div class="memory-meta">
        <small>Agent: ${escapeHtml(mem.agent_id)}</small>
        <small>Relevance: ${mem.relevance_score?.toFixed(2) || 'N/A'}</small>
      </div>
    </div>
  `).join('');
}

async function loadApiKeys() {
  try {
    const response = await fetchJson('/api/ai/keys');
    renderApiKeys(response.keys);
  } catch (error) {
    console.error('Failed to load API keys:', error);
  }
}

function renderApiKeys(keys) {
  const grid = document.getElementById('apiKeysGrid');
  if (!grid) return;

  if (!keys || keys.length === 0) {
    grid.innerHTML = '<p class="panel-empty">No API keys configured. Add one to enable AI agents.</p>';
    return;
  }

  grid.innerHTML = keys.map(key => `
    <div class="api-key-card">
      <div class="api-key-header">
        <span class="provider-badge">${escapeHtml(key.provider)}</span>
        <span class="status-badge ${key.is_active ? 'active' : 'inactive'}">${key.is_active ? 'Active' : 'Inactive'}</span>
      </div>
      <div><strong>${escapeHtml(key.key_name)}</strong></div>
      <div class="api-key-meta">
        <span class="api-key-usage"><span class="usage-badge">${key.usage_count} uses</span></span>
        <span>Rate: ${key.rate_limit_per_minute}/min</span>
        <span>Last used: ${formatTime(key.last_used_at)}</span>
      </div>
    </div>
  `).join('');
}

async function loadAgentLogs(level = null) {
  try {
    const response = await fetchJson(`/api/agents/logs?level=${level || ''}&limit=30`);
    renderAgentLogs(response.logs);
  } catch (error) {
    console.error('Failed to load agent logs:', error);
  }
}

function renderAgentLogs(logs) {
  const grid = document.getElementById('agentLogsGrid');
  if (!grid) return;

  if (!logs || logs.length === 0) {
    grid.innerHTML = '<p class="panel-empty">No logs found.</p>';
    return;
  }

  grid.innerHTML = logs.map(log => `
    <div class="log-entry">
      <span class="log-level ${escapeHtml(log.log_level)}">${escapeHtml(log.log_level)}</span>
      <span class="log-message">${escapeHtml(log.message)}</span>
      <div class="log-time">${formatTime(log.created_at)} · Agent: ${escapeHtml(log.agent_id)}</div>
    </div>
  `).join('');
}

function bindAgentControls() {
  const startBtn = document.getElementById('startAgentsBtn');
  const stopBtn = document.getElementById('stopAgentsBtn');
  const triggerResearchBtn = document.getElementById('triggerResearchBtn');
  const addKeyBtn = document.getElementById('addKeyBtn');

  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      try {
        await fetchJson('/api/agents/start', { method: 'POST' });
        showToast('Agents started');
        await loadAgentStatus();
      } catch (error) {
        showToast(error.message || 'Failed to start agents');
      }
    });
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
      try {
        await fetchJson('/api/agents/stop', { method: 'POST' });
        showToast('Agents stopped');
        await loadAgentStatus();
      } catch (error) {
        showToast(error.message || 'Failed to stop agents');
      }
    });
  }

  if (triggerResearchBtn) {
    triggerResearchBtn.addEventListener('click', async () => {
      try {
        await fetchJson('/api/agents/research', { method: 'POST', body: JSON.stringify({}) });
        showToast('Research triggered');
        await loadJobs();
      } catch (error) {
        showToast(error.message || 'Failed to trigger research');
      }
    });
  }

  if (addKeyBtn) {
    addKeyBtn.addEventListener('click', () => {
      const provider = prompt('Enter provider (anthropic, openai, groq):');
      if (!provider) return;
      const keyName = prompt('Enter key name:');
      if (!keyName) return;
      const apiKey = prompt('Enter API key:');
      if (!apiKey) return;

      fetchJson('/api/ai/keys', {
        method: 'POST',
        body: JSON.stringify({ provider, key_name: keyName, api_key: apiKey }),
      })
        .then(() => {
          showToast('API key added');
          loadApiKeys();
        })
        .catch(error => showToast(error.message || 'Failed to add API key'));
    });
  }

  // Filter tabs for jobs
  document.querySelectorAll('[data-filter]').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('[data-filter]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      loadJobs(tab.dataset.filter);
    });
  });

  // Filter tabs for memory
  document.querySelectorAll('[data-memory-filter]').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('[data-memory-filter]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      loadMemory(tab.dataset.memory_filter);
    });
  });
}

async function initAgentView() {
  await loadAgentStatus();
  await loadJobs();
  await loadMemory();
  await loadApiKeys();
  await loadAgentLogs();
  bindAgentControls();

  // Auto-refresh every 10 seconds
  setInterval(async () => {
    await loadAgentStatus();
    await loadAgentLogs();
  }, 10000);
}

function bindScanButton() {
  const runCheckBtn = document.getElementById('runCheckBtn');
  runCheckBtn.addEventListener('click', async () => {
    if (!getStoredToken()) {
      showToast('Sign in on Review to run a live source scan');
      setView('review');
      return;
    }
    runCheckBtn.disabled = true;
    runCheckBtn.textContent = 'Scanning official pages…';
    try {
      const result = await fetchJson('/api/monitor/run', { method: 'POST', body: JSON.stringify({}) });
      await loadDashboard();
      showToast(`Scan complete · ${result.scanned} sources`);
      setView('desk');
    } catch (error) {
      showToast(error.message || 'Scan failed');
    } finally {
      runCheckBtn.disabled = false;
      runCheckBtn.textContent = 'Run verification';
    }
  });
}

async function init() {
  bindNavigation();
  bindAuthForms();
  bindModalControls();
  bindScanButton();
  await loadDashboard();
  await loadWorkspace();

  // Initialize agent view when tab is selected
  document.querySelectorAll('.nav-item').forEach(button => {
    button.addEventListener('click', () => {
      if (button.dataset.view === 'agents') {
        initAgentView();
      }
    });
  });
}

init().catch((error) => {
  console.error('Dashboard failed to load:', error);
  document.getElementById('offersGrid').innerHTML = '<p>Unable to load the desk. Refresh and try again.</p>';
});
