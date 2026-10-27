async function loadDashboard() {
  const statsGrid = document.getElementById('statsGrid');
  const providersGrid = document.getElementById('providersGrid');
  const researchSummary = document.getElementById('researchSummary');
  const offersGrid = document.getElementById('offersGrid');

  const [summaryResponse, offersResponse, providersResponse, researchResponse] = await Promise.all([
    fetch('/api/summary'),
    fetch('/api/offers'),
    fetch('/api/providers'),
    fetch('/api/research')
  ]);

  const summary = await summaryResponse.json();
  const offers = await offersResponse.json();
  const providers = await providersResponse.json();
  const research = await researchResponse.json();

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

  providersGrid.innerHTML = providers.map((provider) => `
    <article class="provider-card">
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

  researchSummary.innerHTML = `
    <div class="summary-row"><span>Total sources</span><strong>${research.total_sources}</strong></div>
    <div class="summary-row"><span>Active providers</span><strong>${research.active_providers}</strong></div>
    <div class="summary-row"><span>Coverage</span><strong>${research.coverage_percent}%</strong></div>
    <div class="summary-row"><span>Needs review</span><strong>${research.needs_review}</strong></div>
    <div class="summary-row"><span>Last scan</span><strong>${research.last_scan}</strong></div>
  `;

  offersGrid.innerHTML = offers.map((offer) => `
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
}

loadDashboard().catch((error) => {
  console.error('Dashboard failed to load:', error);
  document.getElementById('offersGrid').innerHTML = '<p>Unable to load offers.</p>';
});
