// Verity Operations Console - Practical Functional JavaScript

const AUTH_KEY = 'verity_token';
const API_BASE = '/api';
let refreshInterval = null;
let wsConnection = null;

// Utility Functions
function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function formatTime(value) {
  if (!value || value === 'never') return '--:--:--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatNumber(value) {
  if (value == null) return '0';
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
  
  const authStatus = document.getElementById('authStatus');
  const authText = document.getElementById('authText');
  
  if (authStatus && authText) {
    if (token && profile) {
      authStatus.classList.remove('offline');
      authStatus.classList.add('online');
      authText.textContent = profile.name;
    } else {
      authStatus.classList.remove('online');
      authStatus.classList.add('offline');
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
  
  document.querySelectorAll('.nav-btn').forEach((button) => {
    button.classList.toggle('active', button.dataset.view === view);
  });
  
  const pageTitle = document.getElementById('pageTitle');
  const titles = {
    dashboard: 'Dashboard',
    logs: 'Live Logs',
    agents: 'Agents',
    jobs: 'Jobs',
    workspace: 'Workspace',
    offers: 'Offers'
  };
  
  if (pageTitle) {
    pageTitle.textContent = titles[view] || 'Dashboard';
  }
  
  // Load view-specific data
  if (view === 'dashboard') loadDashboard();
  if (view === 'logs') loadLogs();
  if (view === 'agents') loadAgents();
  if (view === 'jobs') loadJobs();
  if (view === 'workspace') loadWorkspace();
  if (view === 'offers') loadOffers();
}

function bindNavigation() {
  document.querySelectorAll('.nav-btn').forEach((button) => {
    button.addEventListener('click', () => setView(button.dataset.view));
  });
}

// Dashboard
async function loadDashboard() {
  try {
    const status = await fetchJson('/api/agents/status');
    updateDashboardStats(status);
    
    const jobs = await fetchJson('/api/agents/jobs');
    updateRecentActivity(jobs.jobs || []);
    
  } catch (error) {
    addLogEntry('error', `Failed to load dashboard: ${error.message}`);
  }
}

function updateDashboardStats(status) {
  document.getElementById('orchestratorStatus').textContent = status.status || 'Idle';
  document.getElementById('jobsPending').textContent = status.queue?.pending || 0;
  document.getElementById('jobsCompleted').textContent = status.queue?.completed || 0;
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

function updateRecentActivity(jobs) {
  const container = document.getElementById('activityLog');
  if (!container) return;
  
  if (!jobs.length) {
    container.innerHTML = '<div class="log-entry"><span class="log-time">--:--:--</span><span class="log-level info">INFO</span><span class="log-message">No recent activity</span></div>';
    return;
  }
  
  container.innerHTML = jobs.slice(0, 10).map(job => `
    <div class="log-entry">
      <span class="log-time">${formatTime(job.created_at)}</span>
      <span class="log-level ${job.status === 'completed' ? 'success' : job.status === 'failed' ? 'error' : 'info'}">${job.status}</span>
      <span class="log-message">${job.job_type} - ${job.agent_type} (ID: ${job.id.substring(0, 8)}...)</span>
    </div>
  `).join('');
  
  document.getElementById('logCount').textContent = `${jobs.length} entries`;
}

// Logs
async function loadLogs() {
  try {
    const logs = await fetchJson('/api/agents/logs');
    renderLogs(logs.logs || []);
  } catch (error) {
    addLogEntry('error', `Failed to load logs: ${error.message}`);
  }
}

function renderLogs(logs) {
  const container = document.getElementById('fullLog');
  if (!container) return;
  
  if (!logs.length) {
    container.innerHTML = '<div class="log-entry"><span class="log-time">--:--:--</span><span class="log-level info">INFO</span><span class="log-message">No logs available</span></div>';
    return;
  }
  
  container.innerHTML = logs.map(log => `
    <div class="log-entry">
      <span class="log-time">${formatTime(log.created_at)}</span>
      <span class="log-level ${log.log_level}">${log.log_level}</span>
      <span class="log-message">[${log.agent_id?.substring(0, 12)}...] ${escapeHtml(log.message)}</span>
    </div>
  `).join('');
}

function addLogEntry(level, message) {
  const container = document.getElementById('fullLog');
  const activityContainer = document.getElementById('activityLog');
  const agentContainer = document.getElementById('agentLog');
  
  const entry = `<div class="log-entry">
    <span class="log-time">${formatTime(new Date().toISOString())}</span>
    <span class="log-level ${level}">${level}</span>
    <span class="log-message">${escapeHtml(message)}</span>
  </div>`;
  
  if (container) container.insertAdjacentHTML('afterbegin', entry);
  if (activityContainer) activityContainer.insertAdjacentHTML('afterbegin', entry);
  if (agentContainer) agentContainer.insertAdjacentHTML('afterbegin', entry);
}

function clearLogs() {
  const containers = ['fullLog', 'activityLog', 'agentLog'];
  containers.forEach(id => {
    const container = document.getElementById(id);
    if (container) {
      container.innerHTML = '<div class="log-entry"><span class="log-time">--:--:--</span><span class="log-level info">INFO</span><span class="log-message">Logs cleared</span></div>';
    }
  });
}

// Agents
async function loadAgents() {
  try {
    const status = await fetchJson('/api/agents/status');
    renderAgentGrid(status);
    
    const logs = await fetchJson('/api/agents/logs');
    renderAgentLogs(logs.logs || []);
    
  } catch (error) {
    addLogEntry('error', `Failed to load agents: ${error.message}`);
  }
}

function renderAgentGrid(status) {
  const container = document.getElementById('agentGrid');
  if (!container) return;
  
  const agents = status.agents || [];
  
  // Count by type
  const researcherCount = agents.filter(a => a.agent_type === 'researcher').length;
  const workerCount = agents.filter(a => a.agent_type === 'worker').length;
  const analyzerCount = agents.filter(a => a.agent_type === 'analyzer').length;
  
  container.innerHTML = `
    <div class="agent-card">
      <div class="agent-name">Researcher</div>
      <div class="agent-status ${status.status === 'running' ? 'running' : 'idle'}">${status.status === 'running' ? 'Running' : 'Idle'}</div>
      <div class="agent-metrics">Active: ${researcherCount} | Jobs: ${status.queue?.pending || 0}</div>
    </div>
    <div class="agent-card">
      <div class="agent-name">Worker</div>
      <div class="agent-status ${status.status === 'running' ? 'running' : 'idle'}">${status.status === 'running' ? 'Running' : 'Idle'}</div>
      <div class="agent-metrics">Active: ${workerCount} | Completed: ${status.queue?.completed || 0}</div>
    </div>
    <div class="agent-card">
      <div class="agent-name">Analyzer</div>
      <div class="agent-status ${status.status === 'running' ? 'running' : 'idle'}">${status.status === 'running' ? 'Running' : 'Idle'}</div>
      <div class="agent-metrics">Active: ${analyzerCount} | Errors: ${status.queue?.failed || 0}</div>
    </div>
  `;
}

function renderAgentLogs(logs) {
  const container = document.getElementById('agentLog');
  if (!container) return;
  
  if (!logs.length) {
    container.innerHTML = '<div class="log-entry"><span class="log-time">--:--:--</span><span class="log-level info">INFO</span><span class="log-message">No agent activity</span></div>';
    return;
  }
  
  container.innerHTML = logs.slice(0, 20).map(log => `
    <div class="log-entry">
      <span class="log-time">${formatTime(log.created_at)}</span>
      <span class="log-level ${log.log_level}">${log.log_level}</span>
      <span class="log-message">[${log.agent_id?.substring(0, 12)}...] ${escapeHtml(log.message)}</span>
    </div>
  `).join('');
}

// Jobs
async function loadJobs() {
  try {
    const jobs = await fetchJson('/api/agents/jobs');
    renderJobs(jobs.jobs || []);
  } catch (error) {
    addLogEntry('error', `Failed to load jobs: ${error.message}`);
  }
}

function renderJobs(jobs) {
  const container = document.getElementById('jobList');
  if (!container) return;
  
  if (!jobs.length) {
    container.innerHTML = '<div class="job-item"><div class="job-info"><div class="job-id">No jobs</div><div class="job-type">Queue is empty</div></div></div>';
    return;
  }
  
  container.innerHTML = jobs.map(job => `
    <div class="job-item">
      <div class="job-info">
        <div class="job-id">${job.id}</div>
        <div class="job-type">${job.job_type} - ${job.agent_type}</div>
      </div>
      <span class="job-status ${job.status}">${job.status}</span>
    </div>
  `).join('');
}

// Workspace
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
    renderAuthMode(true);
    renderWorkspaceStats(data.workspace);
    renderTasks(data.workspace.tasks);
  } catch (error) {
    setAuthState('', null);
    renderAuthMode(false);
  }
}

function renderAuthMode(isLoggedIn) {
  const authPanel = document.getElementById('authPanel');
  const workspacePanel = document.getElementById('workspacePanel');
  
  authPanel?.classList.toggle('hidden', isLoggedIn);
  workspacePanel?.classList.toggle('hidden', !isLoggedIn);
}

function renderWorkspaceStats(workspace) {
  const container = document.getElementById('workspaceStats');
  if (!container) return;
  
  const summary = workspace.summary || {};
  container.innerHTML = `
    <div class="stat-box">
      <div class="stat-label">Total Tasks</div>
      <div class="stat-value">${formatNumber(summary.total_tasks ?? 0)}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Queued</div>
      <div class="stat-value">${formatNumber(summary.queued ?? 0)}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">In Review</div>
      <div class="stat-value">${formatNumber(summary.in_review ?? 0)}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Verified</div>
      <div class="stat-value">${formatNumber(summary.verified ?? 0)}</div>
    </div>
  `;
}

function renderTasks(tasks) {
  const container = document.getElementById('taskList');
  if (!container) return;
  
  if (!tasks.length) {
    container.innerHTML = '<div class="job-item"><div class="job-info"><div class="job-type">No tasks assigned</div></div></div>';
    return;
  }
  
  container.innerHTML = tasks.map(task => `
    <div class="task-item">
      <div class="task-provider">${escapeHtml(task.provider)}</div>
      <div class="task-title">${escapeHtml(task.title)}</div>
      <div class="task-summary">${escapeHtml(task.summary)}</div>
      <div class="task-meta">
        <span>Priority: ${escapeHtml(task.priority)}</span>
        <span>Status: ${escapeHtml(task.status)}</span>
      </div>
    </div>
  `).join('');
}

// Offers
async function loadOffers() {
  try {
    const offers = await fetchJson('/api/offers');
    renderOffers(offers);
  } catch (error) {
    addLogEntry('error', `Failed to load offers: ${error.message}`);
  }
}

function renderOffers(offers) {
  const container = document.getElementById('offersList');
  if (!container) return;
  
  if (!offers.length) {
    container.innerHTML = '<div class="job-item"><div class="job-info"><div class="job-type">No offers available</div></div></div>';
    return;
  }
  
  container.innerHTML = offers.map(offer => `
    <div class="task-item">
      <div class="task-provider">${escapeHtml(offer.provider)}</div>
      <div class="task-title">${escapeHtml(offer.product)}</div>
      <div class="task-summary">${escapeHtml(offer.reward)}</div>
      <div class="task-meta">
        <span>Score: ${offer.score}</span>
        <span>Status: ${offer.status}</span>
        <span>${offer.verified ? '✓ Verified' : 'Unverified'}</span>
      </div>
    </div>
  `).join('');
}

// Agent Controls
async function startAgents() {
  try {
    addLogEntry('info', 'Starting agent orchestrator...');
    await fetchJson('/api/agents/start', { method: 'POST' });
    addLogEntry('success', 'Agents started successfully');
    loadDashboard();
  } catch (error) {
    addLogEntry('error', `Failed to start agents: ${error.message}`);
  }
}

async function stopAgents() {
  try {
    addLogEntry('info', 'Stopping agent orchestrator...');
    await fetchJson('/api/agents/stop', { method: 'POST' });
    addLogEntry('success', 'Agents stopped');
    loadDashboard();
  } catch (error) {
    addLogEntry('error', `Failed to stop agents: ${error.message}`);
  }
}

async function triggerResearch() {
  try {
    addLogEntry('info', 'Triggering research on Hacker News...');
    await fetchJson('/api/agents/research', { 
      method: 'POST',
      body: JSON.stringify({ platform: 'hackernews' })
    });
    addLogEntry('success', 'Research job queued');
    loadDashboard();
  } catch (error) {
    addLogEntry('error', `Failed to trigger research: ${error.message}`);
  }
}

// Authentication Handlers
async function handleLogin(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  
  try {
    addLogEntry('info', 'Attempting login...');
    const data = await fetchJson('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: formData.get('email'),
        password: formData.get('password')
      })
    });
    setAuthState(data.token, { name: data.name, role: data.role });
    addLogEntry('success', `Signed in as ${data.name}`);
    form.reset();
    loadWorkspace();
  } catch (error) {
    addLogEntry('error', `Login failed: ${error.message}`);
  }
}

async function handleSignup(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  
  try {
    addLogEntry('info', 'Creating account...');
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
    addLogEntry('success', `Account created for ${data.name}`);
    form.reset();
    loadWorkspace();
  } catch (error) {
    addLogEntry('error', `Signup failed: ${error.message}`);
  }
}

function handleSignOut() {
  addLogEntry('info', 'Signing out...');
  setAuthState('', null);
  renderAuthMode(false);
}

// Auto-refresh
function startAutoRefresh() {
  if (refreshInterval) clearInterval(refreshInterval);
  
  refreshInterval = setInterval(() => {
    const activeView = document.querySelector('.view.active');
    if (activeView?.id === 'view-dashboard') loadDashboard();
    if (activeView?.id === 'view-logs') loadLogs();
    if (activeView?.id === 'view-agents') loadAgents();
    if (activeView?.id === 'view-jobs') loadJobs();
  }, 5000); // Refresh every 5 seconds
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
  const refreshBtn = document.getElementById('refreshBtn');
  
  startAgentsBtn?.addEventListener('click', startAgents);
  stopAgentsBtn?.addEventListener('click', stopAgents);
  triggerResearchBtn?.addEventListener('click', triggerResearch);
  refreshBtn?.addEventListener('click', () => {
    const activeView = document.querySelector('.view.active');
    if (activeView?.id === 'view-dashboard') loadDashboard();
    if (activeView?.id === 'view-logs') loadLogs();
    if (activeView?.id === 'view-agents') loadAgents();
    if (activeView?.id === 'view-jobs') loadJobs();
    if (activeView?.id === 'view-workspace') loadWorkspace();
    if (activeView?.id === 'view-offers') loadOffers();
    addLogEntry('info', 'Data refreshed');
  });
  
  // Load initial view
  setView('dashboard');
  
  // Check for existing token
  const token = getStoredToken();
  if (token) {
    setAuthState(token, { name: 'User', role: 'researcher' });
  }
  
  // Start auto-refresh
  startAutoRefresh();
  
  addLogEntry('info', 'Verity Operations Console initialized');
  addLogEntry('info', 'Ready to start agents and monitor activity');
});
