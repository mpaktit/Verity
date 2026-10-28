// Verity Intelligence Platform - Premium Professional JavaScript

const AUTH_KEY = 'verity_token';
const API_BASE = '/api';

// Utility Functions
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

function formatNumber(value) {
  if (value == null) return '—';
  return Number(value).toLocaleString();
}

// API Client
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

// Toast Notifications
function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast ${type}`;
  toast.classList.remove('hidden');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toast.classList.add('hidden'), 3000);
}

// Authentication
function getStoredToken() {
  return localStorage.getItem(AUTH_KEY) || '';
}

function setAuthState(token, profile) {
  if (token) {
    localStorage.setItem(AUTH_KEY, token);
  } else {
    localStorage.removeItem(AUTH_KEY);
  }
  
  const authIndicator = document.querySelector('#authStatus .auth-indicator');
  const authText = document.querySelector('#authStatus .auth-text');
  
  if (authIndicator && authText) {
    if (token && profile) {
      authIndicator.classList.remove('offline');
      authIndicator.classList.add('online');
      authText.textContent = profile.name;
    } else {
      authIndicator.classList.remove('online');
      authIndicator.classList.add('offline');
      authText.textContent = 'Not authenticated';
    }
  }
}

// Navigation
function setView(view) {
  document.querySelectorAll('.view').forEach((panel) => {
    panel.classList.remove('active');
  });
  const targetView = document.getElementById(`view-${view}`);
  if (targetView) {
    targetView.classList.add('active');
  }
  
  document.querySelectorAll('.nav-item').forEach((button) => {
    button.classList.toggle('active', button.dataset.view === view);
  });
  
  // Update page title
  const pageTitle = document.getElementById('pageTitle');
  const pageSubtitle = document.getElementById('pageSubtitle');
  const titles = {
    overview: ['Dashboard', 'Public offer intelligence dashboard'],
    offers: ['Opportunities', 'All tracked opportunities'],
    providers: ['Providers', 'Provider intelligence coverage'],
    agents: ['Agents', 'Autonomous research & verification'],
    alerts: ['Alerts', 'System alerts & notifications'],
    workspace: ['Workspace', 'Your verification workspace']
  };
  
  if (pageTitle && pageSubtitle && titles[view]) {
    pageTitle.textContent = titles[view][0];
    pageSubtitle.textContent = titles[view][1];
  }
  
  // Load view-specific data
  if (view === 'overview') loadDashboard();
  if (view === 'offers') loadOffers();
  if (view === 'providers') loadProviders();
  if (view === 'agents') loadAgents();
  if (view === 'alerts') loadAlerts();
  if (view === 'workspace') loadWorkspace();
}

function bindNavigation() {
  document.querySelectorAll('.nav-item').forEach((button) => {
    button.addEventListener('click', () => setView(button.dataset.view));
  });
  
  // Handle view buttons in cards
  document.querySelectorAll('[data-view]').forEach((button) => {
    if (!button.classList.contains('nav-item')) {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        setView(button.dataset.view);
      });
    }
  });
}

// Dashboard Rendering
async function loadDashboard() {
  try {
    const [summary, offers, providers, research] = await Promise.all([
      fetchJson('/api/summary'),
      fetchJson('/api/offers'),
      fetchJson('/api/providers'),
      fetchJson('/api/research')
    ]);
    
    // Update metrics
    document.getElementById('metricSources').textContent = formatNumber(research.checked_sources);
    document.getElementById('metricOffers').textContent = formatNumber(summary.active_offers);
    document.getElementById('metricConfidence').textContent = formatNumber(summary.high_confidence);
    
    // Render recent offers
    renderRecentOffers(offers.slice(0, 5));
    
    // Render top providers
    renderTopProviders(providers.slice(0, 5));
    
    // Render activity feed
    renderActivityFeed([]);
    
  } catch (error) {
    console.error('Failed to load dashboard:', error);
  }
}

function renderRecentOffers(offers) {
  const container = document.getElementById('recentOffers');
  if (!container) return;
  
  if (!offers.length) {
    container.innerHTML = '<div class="empty-state">No offers available</div>';
    return;
  }
  
  container.innerHTML = offers.map(offer => `
    <div class="offer-item">
      <div class="offer-header">
        <span class="offer-title">${escapeHtml(offer.product)}</span>
        <span class="offer-badge ${offer.status}">${escapeHtml(offer.status)}</span>
      </div>
      <div class="offer-details">
        <span class="offer-provider">${escapeHtml(offer.provider)}</span>
        <span class="offer-reward">${escapeHtml(offer.reward)}</span>
      </div>
      <div class="offer-meta">
        <span class="offer-score">Score: ${offer.score}</span>
        <span>${offer.official ? 'Official' : 'Unofficial'}</span>
      </div>
    </div>
  `).join('');
}

function renderTopProviders(providers) {
  const container = document.getElementById('topProviders');
  if (!container) return;
  
  if (!providers.length) {
    container.innerHTML = '<div class="empty-state">No providers available</div>';
    return;
  }
  
  container.innerHTML = providers.map(provider => `
    <div class="provider-item">
      <div class="provider-header">
        <span class="provider-name">${escapeHtml(provider.name)}</span>
        <span class="provider-badge ${provider.status}">${escapeHtml(provider.status)}</span>
      </div>
      <div class="provider-details">
        <span>Coverage: ${provider.research_coverage}%</span>
        <span>Sources: ${provider.source_count}</span>
      </div>
    </div>
  `).join('');
}

function renderActivityFeed(activities) {
  const container = document.getElementById('activityFeed');
  if (!container) return;
  
  if (!activities.length) {
    container.innerHTML = '<div class="empty-state">No recent activity</div>';
    return;
  }
  
  container.innerHTML = activities.map(activity => `
    <div class="activity-item">
      <div class="activity-header">
        <span class="activity-title">${escapeHtml(activity.action)}</span>
        <span class="activity-time">${formatTime(activity.created_at)}</span>
      </div>
      <div class="activity-details">${escapeHtml(activity.details || '')}</div>
    </div>
  `).join('');
}

// Offers View
async function loadOffers() {
  try {
    const offers = await fetchJson('/api/offers');
    renderOffers(offers);
  } catch (error) {
    console.error('Failed to load offers:', error);
  }
}

function renderOffers(offers) {
  const container = document.getElementById('offersGrid');
  if (!container) return;
  
  if (!offers.length) {
    container.innerHTML = '<div class="empty-state">No offers available</div>';
    return;
  }
  
  container.innerHTML = offers.map(offer => `
    <div class="job-item">
      <div class="offer-header">
        <span class="offer-title">${escapeHtml(offer.product)}</span>
        <span class="offer-badge ${offer.status}">${escapeHtml(offer.status)}</span>
      </div>
      <div class="offer-details">
        <div><strong>Provider:</strong> ${escapeHtml(offer.provider)}</div>
        <div><strong>Reward:</strong> ${escapeHtml(offer.reward)}</div>
        <div><strong>Eligibility:</strong> ${escapeHtml(offer.eligibility)}</div>
      </div>
      <div class="offer-meta">
        <span class="offer-score">Score: ${offer.score}</span>
        <span>${offer.official ? '✓ Official' : 'Unofficial'}</span>
        <span>${offer.verified ? '✓ Verified' : 'Unverified'}</span>
      </div>
    </div>
  `).join('');
}

// Providers View
async function loadProviders() {
  try {
    const providers = await fetchJson('/api/providers');
    renderProviders(providers);
  } catch (error) {
    console.error('Failed to load providers:', error);
  }
}

function renderProviders(providers) {
  const container = document.getElementById('providersGrid');
  if (!container) return;
  
  if (!providers.length) {
    container.innerHTML = '<div class="empty-state">No providers available</div>';
    return;
  }
  
  container.innerHTML = providers.map(provider => `
    <div class="provider-item">
      <div class="provider-header">
        <span class="provider-name">${escapeHtml(provider.name)}</span>
        <span class="provider-badge ${provider.status}">${escapeHtml(provider.status)}</span>
      </div>
      <div class="provider-details">
        <div><strong>Category:</strong> ${escapeHtml(provider.category)}</div>
        <div><strong>Coverage:</strong> ${provider.research_coverage}%</div>
        <div><strong>Sources:</strong> ${provider.source_count}</div>
        <div><strong>Signal:</strong> ${escapeHtml(provider.signal || 'None')}</div>
      </div>
    </div>
  `).join('');
}

// Agents View
async function loadAgents() {
  try {
    const status = await fetchJson('/api/agents/status');
    renderAgentStatus(status);
    
    const jobs = await fetchJson('/api/agents/jobs');
    renderJobs(jobs.jobs || []);
    
    const memory = await fetchJson('/api/agents/memory');
    renderMemory(memory.memories || []);
    
    const keys = await fetchJson('/api/ai/keys');
    renderApiKeys(keys.keys || []);
    
  } catch (error) {
    console.error('Failed to load agents:', error);
  }
}

function renderAgentStatus(status) {
  document.getElementById('orchestratorStatus').textContent = status.status || 'Idle';
  document.getElementById('queueStats').textContent = `${status.queue?.pending || 0} pending / ${status.queue?.completed || 0} completed`;
  document.getElementById('activeAgents').textContent = status.agents?.length || 0;
  
  const startBtn = document.getElementById('startAgentsBtn');
  const stopBtn = document.getElementById('stopAgentsBtn');
  
  if (status.status === 'running') {
    startBtn?.classList.add('hidden');
    stopBtn?.classList.remove('hidden');
  } else {
    startBtn?.classList.remove('hidden');
    stopBtn?.classList.add('hidden');
  }
}

function renderJobs(jobs) {
  const container = document.getElementById('jobsGrid');
  if (!container) return;
  
  if (!jobs.length) {
    container.innerHTML = '<div class="empty-state">No jobs in queue</div>';
    return;
  }
  
  container.innerHTML = jobs.map(job => `
    <div class="job-item">
      <div class="job-header">
        <span class="job-id">${escapeHtml(job.id)}</span>
        <span class="job-badge ${job.status}">${escapeHtml(job.status)}</span>
      </div>
      <div class="job-details">
        <div><strong>Type:</strong> ${escapeHtml(job.job_type)}</div>
        <div><strong>Agent:</strong> ${escapeHtml(job.agent_type)}</div>
        <div><strong>Priority:</strong> ${job.priority}</div>
      </div>
      <div class="job-meta">
        <span>Created: ${formatTime(job.created_at)}</span>
        ${job.completed_at ? `<span>Completed: ${formatTime(job.completed_at)}</span>` : ''}
      </div>
    </div>
  `).join('');
}

function renderMemory(memories) {
  const container = document.getElementById('memoryGrid');
  if (!container) return;
  
  if (!memories.length) {
    container.innerHTML = '<div class="empty-state">No stored memories</div>';
    return;
  }
  
  container.innerHTML = memories.slice(0, 10).map(memory => `
    <div class="memory-item">
      <div class="memory-header">
        <span class="memory-type">${escapeHtml(memory.memory_type)}</span>
        <span class="memory-time">${formatTime(memory.created_at)}</span>
      </div>
      <div class="memory-content">${escapeHtml(memory.content?.substring(0, 200))}${memory.content?.length > 200 ? '...' : ''}</div>
    </div>
  `).join('');
}

function renderApiKeys(keys) {
  const container = document.getElementById('apiKeysGrid');
  if (!container) return;
  
  if (!keys.length) {
    container.innerHTML = '<div class="empty-state">No API keys configured</div>';
    return;
  }
  
  container.innerHTML = keys.map(key => `
    <div class="api-key-item">
      <div class="api-key-header">
        <span class="api-key-name">${escapeHtml(key.key_name)}</span>
        <span class="api-key-provider">${escapeHtml(key.provider)}</span>
      </div>
      <div class="api-key-details">
        <span>Rate limit: ${key.rate_limit_per_minute}/min</span>
        <span>Usage: ${key.usage_count}</span>
        <span class="api-key-status ${key.is_active ? 'active' : 'inactive'}">${key.is_active ? 'Active' : 'Inactive'}</span>
      </div>
    </div>
  `).join('');
}

// Alerts View
async function loadAlerts() {
  try {
    const alerts = await fetchJson('/api/alerts');
    renderAlerts(alerts);
  } catch (error) {
    console.error('Failed to load alerts:', error);
  }
}

function renderAlerts(alerts) {
  const container = document.getElementById('alertsGrid');
  if (!container) return;
  
  if (!alerts.length) {
    container.innerHTML = '<div class="empty-state">No alerts</div>';
    return;
  }
  
  container.innerHTML = alerts.map(alert => `
    <div class="alert-item">
      <div class="alert-header">
        <span class="alert-title">${escapeHtml(alert.title)}</span>
        <span class="alert-severity ${alert.severity}">${escapeHtml(alert.severity)}</span>
      </div>
      <div class="alert-message">${escapeHtml(alert.message)}</div>
      <div class="alert-meta">
        <span>Updated: ${formatTime(alert.updated_at)}</span>
        ${alert.provider ? `<span>Provider: ${escapeHtml(alert.provider)}</span>` : ''}
      </div>
    </div>
  `).join('');
}

// Workspace View
async function loadWorkspace() {
  const token = getStoredToken();
  if (!token) {
    renderAuthMode(false);
    setAuthState('', null);
    return;
  }
  
  try {
    const data = await fetchJson('/api/workspace');
    setAuthState(token, data.profile);
    renderAuthMode(true, data.profile);
    renderWorkspaceSummary(data.workspace);
    renderTasks(data.workspace.tasks);
  } catch (error) {
    setAuthState('', null);
    renderAuthMode(false);
  }
}

function renderAuthMode(isLoggedIn, profile = null) {
  const authPanel = document.getElementById('authPanel');
  const workspacePanel = document.getElementById('workspacePanel');
  
  authPanel?.classList.toggle('hidden', isLoggedIn);
  workspacePanel?.classList.toggle('hidden', !isLoggedIn);
}

function renderWorkspaceSummary(workspace) {
  const container = document.getElementById('workspaceSummary');
  if (!container) return;
  
  const summary = workspace.summary || {};
  container.innerHTML = `
    <div class="workspace-stat">
      <div class="workspace-stat-value">${formatNumber(summary.total_tasks ?? 0)}</div>
      <div class="workspace-stat-label">Total Tasks</div>
    </div>
    <div class="workspace-stat">
      <div class="workspace-stat-value">${formatNumber(summary.queued ?? 0)}</div>
      <div class="workspace-stat-label">Queued</div>
    </div>
    <div class="workspace-stat">
      <div class="workspace-stat-value">${formatNumber(summary.in_review ?? 0)}</div>
      <div class="workspace-stat-label">In Review</div>
    </div>
    <div class="workspace-stat">
      <div class="workspace-stat-value">${formatNumber(summary.verified ?? 0)}</div>
      <div class="workspace-stat-label">Verified</div>
    </div>
  `;
}

function renderTasks(tasks) {
  const container = document.getElementById('taskList');
  if (!container) return;
  
  if (!tasks.length) {
    container.innerHTML = '<div class="empty-state">No tasks assigned</div>';
    return;
  }
  
  container.innerHTML = tasks.map(task => `
    <div class="task-item">
      <div class="task-header">
        <span class="task-provider">${escapeHtml(task.provider)}</span>
        <span class="task-badge ${task.status}">${escapeHtml(task.status)}</span>
      </div>
      <h3 class="task-title">${escapeHtml(task.title)}</h3>
      <p class="task-summary">${escapeHtml(task.summary)}</p>
      <div class="task-meta">
        <span>Priority: <strong>${escapeHtml(task.priority)}</strong></span>
        <span>Category: <strong>${escapeHtml(task.category)}</strong></span>
      </div>
      <div class="task-signals">
        ${(task.signals || []).map(signal => `<span class="task-signal">${escapeHtml(signal)}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

// Agent Controls
async function startAgents() {
  try {
    await fetchJson('/api/agents/start', { method: 'POST' });
    showToast('Agents started successfully', 'success');
    loadAgents();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function stopAgents() {
  try {
    await fetchJson('/api/agents/stop', { method: 'POST' });
    showToast('Agents stopped', 'info');
    loadAgents();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function triggerResearch() {
  try {
    await fetchJson('/api/agents/research', { 
      method: 'POST',
      body: JSON.stringify({ platform: 'hackernews' })
    });
    showToast('Research triggered', 'success');
    loadAgents();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

// Authentication Handlers
async function handleLogin(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  
  try {
    const data = await fetchJson('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: formData.get('email'),
        password: formData.get('password')
      })
    });
    setAuthState(data.token, { name: data.name, role: data.role });
    showToast('Signed in successfully', 'success');
    form.reset();
    loadWorkspace();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function handleSignup(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  
  try {
    const data = await fetchJson('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({
        name: formData.get('name'),
        email: formData.get('email'),
        password: formData.get('password'),
        role: formData.get('role')
      })
    });
    setAuthState(data.token, { name: data.name, role: data.role });
    showToast('Account created successfully', 'success');
    form.reset();
    loadWorkspace();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

function handleSignOut() {
  setAuthState('', null);
  renderAuthMode(false);
  showToast('Signed out', 'info');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  bindNavigation();
  
  // Auth forms
  const loginForm = document.getElementById('loginForm');
  const signupForm = document.getElementById('signupForm');
  const signOutBtn = document.getElementById('signOutBtn');
  
  loginForm?.addEventListener('submit', handleLogin);
  signupForm?.addEventListener('submit', handleSignup);
  signOutBtn?.addEventListener('click', handleSignOut);
  
  // Agent controls
  const startAgentsBtn = document.getElementById('startAgentsBtn');
  const stopAgentsBtn = document.getElementById('stopAgentsBtn');
  const triggerResearchBtn = document.getElementById('triggerResearchBtn');
  
  startAgentsBtn?.addEventListener('click', startAgents);
  stopAgentsBtn?.addEventListener('click', stopAgents);
  triggerResearchBtn?.addEventListener('click', triggerResearch);
  
  // Refresh button
  const refreshBtn = document.getElementById('refreshBtn');
  refreshBtn?.addEventListener('click', () => {
    const activeView = document.querySelector('.view.active');
    if (activeView?.id === 'view-overview') loadDashboard();
    if (activeView?.id === 'view-offers') loadOffers();
    if (activeView?.id === 'view-providers') loadProviders();
    if (activeView?.id === 'view-agents') loadAgents();
    if (activeView?.id === 'view-alerts') loadAlerts();
    if (activeView?.id === 'view-workspace') loadWorkspace();
    showToast('Data refreshed', 'success');
  });
  
  // Load initial view
  setView('overview');
  
  // Check for existing token
  const token = getStoredToken();
  if (token) {
    setAuthState(token, { name: 'User', role: 'researcher' });
  }
});
