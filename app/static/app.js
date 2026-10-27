const AUTH_KEY = 'verity_token';

async function fetchJson(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
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
  showToast._timer = setTimeout(() => toast.classList.add('hidden'), 2200);
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

  const authStatus = document.getElementById('authStatus');
  const statusPill = authStatus?.querySelector('.status-pill');
  if (token && profile) {
    statusPill.textContent = `${profile.name} • ${profile.role}`;
    statusPill.className = 'status-pill online';
  } else {
    statusPill.textContent = 'Not signed in';
    statusPill.className = 'status-pill offline';
  }
}

function renderAuthMode(isLoggedIn, profile = null) {
  const authPanel = document.getElementById('authPanel');
  const workspacePanel = document.getElementById('workspacePanel');
  if (authPanel) {
    authPanel.classList.toggle('hidden', isLoggedIn);
  }
  if (workspacePanel) {
    workspacePanel.classList.toggle('hidden', !isLoggedIn);
  }

  if (profile) {
    const workerTitle = document.getElementById('workerTitle');
    if (workerTitle) {
      workerTitle.textContent = `${profile.name}'s operation board`;
    }
  }
}

function renderWorkspaceSummary(workspace) {
  const workspaceSummary = document.getElementById('workspaceSummary');
  if (!workspaceSummary) return;
  const summary = workspace.summary || {};
  workspaceSummary.innerHTML = `
    <div class="summary-box">
      <span>Total tasks</span>
      <strong>${summary.total_tasks ?? 0}</strong>
    </div>
    <div class="summary-box">
      <span>Queued</span>
      <strong>${summary.queued ?? 0}</strong>
    </div>
    <div class="summary-box">
      <span>In review</span>
      <strong>${summary.in_review ?? 0}</strong>
    </div>
    <div class="summary-box">
      <span>Verified</span>
      <strong>${summary.verified ?? 0}</strong>
    </div>
  `;
}

function renderTasks(tasks) {
  const taskList = document.getElementById('taskList');
  if (!taskList) return;

  if (!tasks || !tasks.length) {
    taskList.innerHTML = '<div class="task-card empty">No live tasks are assigned right now.</div>';
    return;
  }

  taskList.innerHTML = tasks.map((task) => `
    <article class="task-card">
      <div class="task-header">
        <div>
          <div class="task-provider">${task.provider}</div>
          <h3>${task.title}</h3>
        </div>
        <span class="status-badge ${task.status}">${task.status}</span>
      </div>
      <p class="task-summary">${task.summary}</p>
      <div class="chip-row">
        ${(task.signals || []).map((signal) => `<span class="chip">${signal}</span>`).join('')}
      </div>
      <div class="task-meta">
        <span>Priority: <strong>${task.priority}</strong></span>
        <span>Category: <strong>${task.category}</strong></span>
      </div>
      <div class="task-actions">
        <form class="inline-form attempt-form" data-task-id="${task.id}">
          <input type="hidden" name="task_id" value="${task.id}" />
          <input type="text" name="approach" placeholder="Approach used" value="${task.approaches?.[0] || ''}" required />
          <textarea name="notes" placeholder="What did you test or verify?" required></textarea>
          <button type="submit" class="secondary-btn">Submit attempt</button>
        </form>
        <form class="inline-form review-form" data-task-id="${task.id}">
          <input type="hidden" name="task_id" value="${task.id}" />
          <select name="decision">
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="needs-review">Needs review</option>
          </select>
          <textarea name="notes" placeholder="Decision notes" required></textarea>
          <button type="submit" class="primary-btn">Submit review</button>
        </form>
      </div>
      <div class="attempt-list">
        ${(task.attempts || []).map((attempt) => `
          <div class="attempt-item">
            <div class="attempt-header">
              <span>${attempt.approach}</span>
              <small>${attempt.created_at}</small>
            </div>
            <p>${attempt.notes}</p>
          </div>
        `).join('') || '<div class="attempt-item empty">No attempts yet.</div>'}
      </div>
      ${task.review ? `
        <div class="review-box">
          <div class="review-header">
            <strong>${task.review.decision}</strong>
            <small>${task.review.reviewed_by || 'system'}</small>
          </div>
          <p>${task.review.notes}</p>
        </div>
      ` : ''}
    </article>
  `).join('');

  document.querySelectorAll('.attempt-form').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const token = getStoredToken();
      if (!token) return;
      const formData = new FormData(form);
      const payload = {
        task_id: formData.get('task_id'),
        approach: formData.get('approach'),
        notes: formData.get('notes')
      };
      try {
        await fetchJson('/api/workspace/attempt', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload)
        });
        await loadWorkspace();
      } catch (error) {
        console.error('Attempt submission failed:', error);
        alert(error.message || 'Attempt failed');
      }
    });
  });

  document.querySelectorAll('.review-form').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const token = getStoredToken();
      if (!token) return;
      const formData = new FormData(form);
      const payload = {
        task_id: formData.get('task_id'),
        decision: formData.get('decision'),
        notes: formData.get('notes')
      };
      try {
        await fetchJson('/api/workspace/review', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload)
        });
        await loadWorkspace();
      } catch (error) {
        console.error('Review submission failed:', error);
        alert(error.message || 'Review failed');
      }
    });
  });
}

async function loadWorkspace() {
  const token = getStoredToken();
  if (!token) {
    renderAuthMode(false);
    setAuthState('', null);
    return;
  }

  try {
    const data = await fetchJson('/api/workspace', {
      headers: { Authorization: `Bearer ${token}` }
    });
    setAuthState(token, data.profile);
    renderAuthMode(true, data.profile);
    renderWorkspaceSummary(data.workspace);
    renderTasks(data.workspace.tasks);
  } catch (error) {
    console.error('Workspace load failed:', error);
    setAuthState('', null);
    renderAuthMode(false);
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

  const [summaryResponse, offersResponse, providersResponse, researchResponse, alertsResponse, insightsResponse, analyticsResponse, sourcesResponse] = await Promise.all([
    fetch('/api/summary'),
    fetch('/api/offers'),
    fetch('/api/providers'),
    fetch('/api/research'),
    fetch('/api/alerts'),
    fetch('/api/insights'),
    fetch('/api/analytics'),
    fetch('/api/sources')
  ]);

  const summary = await summaryResponse.json();
  let offers = await offersResponse.json();
  let providers = await providersResponse.json();
  const research = await researchResponse.json();
  const alerts = await alertsResponse.json();
  const insights = await insightsResponse.json();
  const analytics = await analyticsResponse.json();
  const sources = await sourcesResponse.json();

  const renderStats = () => {
    const stats = [
      { label: 'Total offers', value: summary.total_offers, note: 'Tracked programs' },
      { label: 'Active', value: summary.active_offers, note: 'Verified public access' },
      { label: 'High confidence', value: summary.high_confidence, note: 'Eligible and valid' },
      { label: 'Needs review', value: summary.needs_review, note: 'Requires policy check' }
    ];

    statsGrid.innerHTML = stats.map((item) => `
      <article class="stat-card">
        <div class="stat-label">${item.label}</div>
        <div class="stat-value">${item.value}</div>
        <div class="stat-note">${item.note}</div>
      </article>
    `).join('');
  };

  const renderProviders = (filteredProviders = providers) => {
    providersGrid.innerHTML = filteredProviders.map((provider) => `
      <article class="provider-card" data-provider-id="${provider.id}" tabindex="0" role="button" aria-label="Open provider details for ${provider.name}">
        <div class="provider-top">
          <div class="provider-name">${provider.name}</div>
          <span class="status-badge ${provider.status}">${provider.status}</span>
        </div>
        <div class="provider-coverage">${provider.research_coverage}%</div>
        <div class="provider-meta">
          <div><strong>Signal:</strong> ${provider.signal}</div>
          <div><strong>Sources:</strong> ${provider.source_count}</div>
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

  const renderInsights = () => {
    if (!insightsGrid) return;
    insightsGrid.innerHTML = `
      <article class="insight-card highlight">
        <div class="muted-label">Momentum</div>
        <div class="insight-value">${insights.momentum_score}</div>
        <div class="insight-copy">${insights.summary}</div>
      </article>
      ${(insights.signals || []).map((signal) => `
        <article class="insight-card">
          <div class="muted-label">Signal</div>
          <div class="insight-title">${signal.title}</div>
          <div class="insight-value small">${signal.value}</div>
          <span class="signal-pill ${signal.status}">${signal.status}</span>
        </article>
      `).join('')}
    `;
  };

  const renderAlerts = () => {
    alertsGrid.innerHTML = alerts.map((alert) => `
      <article class="alert-card">
        <div class="alert-title">${alert.title}</div>
        <div class="alert-message">${alert.message}</div>
        <span class="alert-severity ${alert.severity}">${alert.severity}</span>
      </article>
    `).join('');
  };

  const renderAnalytics = () => {
    const pipeline = analytics.pipeline || [];
    const trend = analytics.trend || { labels: [], values: [] };

    const pipelineMarkup = pipeline.map((entry) => `
      <div class="pipeline-row">
        <div class="pipeline-header">
          <span>${entry.label}</span>
          <strong>${entry.value}</strong>
        </div>
        <div class="pipeline-bar"><span style="width:${entry.percent}%"></span></div>
      </div>
    `).join('');

    const trendMarkup = trend.labels.map((label, index) => `
      <div class="trend-point">
        <span class="trend-bar" style="height:${Math.max(10, trend.values[index] * 1.2)}px"></span>
        <small>${label}</small>
      </div>
    `).join('');

    researchSummary.innerHTML += `
      <div class="analytics-block">
        <div class="analytics-title">Review pipeline</div>
        ${pipelineMarkup}
      </div>
      <div class="analytics-block">
        <div class="analytics-title">Monitoring trend</div>
        <div class="trend-chart">${trendMarkup}</div>
      </div>
    `;
  };

  const renderResearch = () => {
    const checked = sources.filter((source) => source.status === 'checked').length;
    const failed = sources.filter((source) => source.status !== 'checked' && source.status !== 'pending').length;
    researchSummary.innerHTML = `
      <div class="summary-row"><span>Total sources</span><strong>${research.total_sources}</strong></div>
      <div class="summary-row"><span>Active providers</span><strong>${research.active_providers}</strong></div>
      <div class="summary-row"><span>Coverage</span><strong>${research.coverage_percent}%</strong></div>
      <div class="summary-row"><span>Needs review</span><strong>${research.needs_review}</strong></div>
      <div class="summary-row"><span>Checked sources</span><strong>${checked}</strong></div>
      <div class="summary-row"><span>Source errors</span><strong>${failed}</strong></div>
      <div class="summary-row"><span>Last scan</span><strong>${research.last_scan}</strong></div>
    `;
  };

  const renderOffers = (filteredOffers = offers) => {
    offersGrid.innerHTML = filteredOffers.map((offer) => `
      <article class="offer-card">
        <div class="offer-top">
          <div class="offer-provider">${offer.provider}</div>
          <span class="status-badge ${offer.status}">${offer.status}</span>
        </div>
        <div class="offer-product">${offer.product}</div>
        <div class="offer-meta">
          <span><strong>Reward:</strong> ${offer.reward}</span>
          <span><strong>Eligibility:</strong> ${offer.eligibility}</span>
          <span><strong>Source:</strong> ${offer.source}</span>
        </div>
        <div class="score-row">
          <span class="score-pill">score ${offer.score}</span>
          <span>${offer.official ? 'Official' : 'Unofficial'}</span>
        </div>
      </article>
    `).join('');
  };

  const filterDashboard = () => {
    const query = searchInput.value.trim().toLowerCase();
    const filteredProviders = providers.filter((provider) => {
      const haystack = `${provider.name} ${provider.signal} ${provider.category}`.toLowerCase();
      return !query || haystack.includes(query);
    });

    const filteredOffers = offers.filter((offer) => {
      const haystack = `${offer.provider} ${offer.product} ${offer.reward} ${offer.eligibility}`.toLowerCase();
      return !query || haystack.includes(query);
    });

    renderProviders(filteredProviders);
    renderOffers(filteredOffers);
  };

  renderInsights();
  renderStats();
  renderProviders();
  renderResearch();
  renderAnalytics();
  renderAlerts();
  renderOffers();

  searchInput.addEventListener('input', filterDashboard);

  const runCheckBtn = document.getElementById('runCheckBtn');
  if (runCheckBtn) {
    runCheckBtn.addEventListener('click', async () => {
      runCheckBtn.disabled = true;
      runCheckBtn.textContent = 'Scanning…';
      try {
        await fetchJson('/api/research');
        await loadDashboard();
        showToast('Verification scan completed');
      } catch (error) {
        console.error('Verification scan failed:', error);
        showToast('Scan failed');
      } finally {
        runCheckBtn.disabled = false;
        runCheckBtn.textContent = 'Run verification';
      }
    });
  }
}

async function openProviderDetail(providerId) {
  const modal = document.getElementById('providerModal');
  const content = document.getElementById('providerModalContent');
  if (!modal || !content) return;

  modal.classList.remove('hidden');
  content.innerHTML = '<div class="modal-loading">Loading provider intelligence…</div>';

  try {
    const provider = await fetchJson(`/api/providers/${providerId}`);
    const sourceMarkup = (provider.sources || []).map((source) => `<li>${source}</li>`).join('');
    const offerMarkup = (provider.offers || []).map((offer) => `
      <div class="modal-offer-row">
        <div>
          <strong>${offer.product}</strong>
          <span>${offer.reward}</span>
        </div>
        <span class="score-pill">${offer.score}</span>
      </div>
    `).join('') || '<p class="modal-empty">No matching offers at the moment.</p>';

    content.innerHTML = `
      <div class="modal-header">
        <div>
          <p class="eyebrow">Provider detail</p>
          <h3 id="providerModalTitle">${provider.name}</h3>
        </div>
        <span class="status-badge ${provider.status}">${provider.status}</span>
      </div>
      <div class="modal-grid">
        <div class="modal-section">
          <div class="modal-label">Coverage</div>
          <div class="modal-value">${provider.research_coverage}%</div>
          <p>${provider.notes}</p>
        </div>
        <div class="modal-section">
          <div class="modal-label">Signals</div>
          <div class="modal-value small">${provider.signal}</div>
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
    `;
  } catch (error) {
    content.innerHTML = '<div class="modal-error">Unable to load provider detail.</div>';
    console.error(error);
  }
}

function bindModalControls() {
  const modal = document.getElementById('providerModal');
  if (!modal) return;

  modal.addEventListener('click', (event) => {
    if (event.target.dataset.close === 'true' || event.target.classList.contains('modal-close')) {
      modal.classList.add('hidden');
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      modal.classList.add('hidden');
    }
  });
}

async function bindAuthForms() {
  const signupForm = document.getElementById('signupForm');
  const loginForm = document.getElementById('loginForm');
  const signOutBtn = document.getElementById('signOutBtn');

  signupForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(signupForm).entries());
    try {
      const result = await fetchJson('/api/auth/signup', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      setAuthState(result.token, { name: result.name, role: result.role });
      renderAuthMode(true, { name: result.name, role: result.role });
      renderWorkspaceSummary(result.workspace);
      renderTasks(result.workspace.tasks);
      signupForm.reset();
    } catch (error) {
      console.error('Signup failed:', error);
      alert(error.message || 'Signup failed');
    }
  });

  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(loginForm).entries());
    try {
      const result = await fetchJson('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      setAuthState(result.token, { name: result.name, role: result.role });
      renderAuthMode(true, { name: result.name, role: result.role });
      renderWorkspaceSummary(result.workspace);
      renderTasks(result.workspace.tasks);
      loginForm.reset();
    } catch (error) {
      console.error('Login failed:', error);
      alert(error.message || 'Login failed');
    }
  });

  signOutBtn.addEventListener('click', () => {
    setAuthState('', null);
    renderAuthMode(false);
  });
}

async function init() {
  await loadDashboard();
  bindAuthForms();
  bindModalControls();
  await loadWorkspace();
}

init().catch((error) => {
  console.error('Dashboard failed to load:', error);
  document.getElementById('offersGrid').innerHTML = '<p>Unable to load offers.</p>';
});
