import { useCallback, useEffect, useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const dateText = (value) => {
  if (!value) return 'Not provided';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Invalid date' : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};
const sourceLabel = (status) => ({ healthy: 'Healthy', stale: 'Stale', failed: 'Failed', unknown: 'Unknown' }[status] || status || 'Unknown');

function Icon({ name }) {
  const paths = {
    wave: <><path d="M2 9c2.2 0 2.2-2 4.4-2s2.2 2 4.4 2 2.2-2 4.4-2 2.2 2 4.4 2 2.2-2 4.4-2"/><path d="M2 15c2.2 0 2.2-2 4.4-2s2.2 2 4.4 2 2.2-2 4.4-2 2.2 2 4.4 2 2.2-2 4.4-2"/></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    alert: <><path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/></>,
    refresh: <><path d="M20 7v5h-5"/><path d="M4 17v-5h5"/><path d="M5.6 9a7 7 0 0 1 11.6-2L20 12M4 12l2.8 5a7 7 0 0 0 11.6-2"/></>,
    external: <><path d="M14 3h7v7"/><path d="M10 14 21 3"/><path d="M19 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6"/></>,
    anchor: <><circle cx="12" cy="5" r="3"/><path d="M12 8v13m-7-7a7 7 0 0 0 14 0M3 12h4m10 0h4"/></>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name] || paths.wave}</svg>;
}

function App() {
  const [advisories, setAdvisories] = useState([]);
  const [sources, setSources] = useState([]);
  const [health, setHealth] = useState(null);
  const [connection, setConnection] = useState(() => (typeof navigator !== 'undefined' && navigator.onLine === false ? 'offline' : 'loading'));
  const [browserOnline, setBrowserOnline] = useState(() => typeof navigator === 'undefined' ? true : navigator.onLine);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [showOriginal, setShowOriginal] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadData = useCallback(async () => {
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      setBrowserOnline(false);
      setConnection('offline');
      setError('Your device reports that it is offline. Reconnect to the internet or local network and try again.');
      setAdvisories([]); setSources([]); setHealth(null);
      return;
    }
    setBrowserOnline(true);
    setConnection('loading');
    setError('');
    setAdvisories([]); setSources([]); setHealth(null);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    try {
      const options = { signal: controller.signal, headers: { Accept: 'application/json' } };
      const [a, s, h] = await Promise.all([
        fetch(`${API_BASE}/api/v1/advisories?include_expired=true&limit=100`, options),
        fetch(`${API_BASE}/api/v1/sources/status`, options),
        fetch(`${API_BASE}/api/v1/operations/health`, options),
      ]);
      if (![a, s, h].every((response) => response.ok)) throw new Error('The API returned an error. Check that the backend is running.');
      const [advisoryData, sourceData, healthData] = await Promise.all([a.json(), s.json(), h.json()]);
      setAdvisories(Array.isArray(advisoryData) ? advisoryData : []);
      setSources(Array.isArray(sourceData) ? sourceData : []);
      setHealth(healthData);
      setConnection('connected');
      setLastUpdated(new Date());
    } catch (err) {
      const isOffline = typeof navigator !== 'undefined' && !navigator.onLine;
      setBrowserOnline(!isOffline);
      setConnection(isOffline ? 'offline' : 'error');
      setError(err?.name === 'AbortError' ? 'The API took longer than 10 seconds to respond. Try again when the connection is stable.' : (err?.message || 'Could not connect to the CoastGuard AI API.'));
      setAdvisories([]); setSources([]); setHealth(null);
    } finally {
      clearTimeout(timeoutId);
    }
  }, []);

  useEffect(() => {
    const onOnline = () => { setBrowserOnline(true); loadData(); };
    const onOffline = () => {
      setBrowserOnline(false); setConnection('offline');
      setError('Your device is offline. Data is not cached for safety; reconnect and refresh to check current source information.');
      setAdvisories([]); setSources([]); setHealth(null);
    };
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    loadData();
    return () => { window.removeEventListener('online', onOnline); window.removeEventListener('offline', onOffline); };
  }, [loadData]);

  const filtered = useMemo(() => advisories.filter((item) => {
    const matchesSearch = `${item.title || ''} ${item.region || ''} ${item.source_name || ''} ${item.original_text || ''}`.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'all' || (filter === 'current' ? item.is_current : !item.is_current);
    return matchesSearch && matchesFilter;
  }), [advisories, search, filter]);

  const hasDemo = advisories.some((item) => item.is_demo) || sources.some((item) => item.is_demo);
  const needsAttention = health?.overall !== 'ok';

  return <div className="app-shell">
    <header className="topbar">
      <a className="brand" href="#top" aria-label="CoastGuard AI home"><span className="brand-mark"><Icon name="wave" /></span><span><b>CoastGuard <em>AI</em></b><small>COASTAL SAFETY INFORMATION</small></span></a>
      <div className="topbar-right"><span className={`connection ${connection}`} role="status" aria-live="polite"><i />{connection === 'connected' ? 'API connected' : connection === 'loading' ? 'Checking connection…' : connection === 'offline' ? 'Device offline' : 'API unavailable'}</span><button className="refresh-btn" onClick={loadData} disabled={connection === 'loading'} aria-label="Refresh dashboard data"><Icon name="refresh" /> Refresh</button></div>
    </header>

    <main id="top" className="main-content">
      <section className="hero">
        <div className="hero-copy"><div className="eyebrow"><span className="eyebrow-line" /> COASTAL KARNATAKA · PROTOTYPE</div><h1>Know the conditions.<br/><span>Make informed decisions.</span></h1><p>One place to review marine advisories, check their validity, and see when source information may be out of date.</p><div className="hero-foot"><Icon name="anchor"/><span>Information support only — official advisories remain authoritative.</span></div></div>
        <div className="hero-art" aria-hidden="true"><div className="sun"/><div className="art-ring ring-one"/><div className="art-ring ring-two"/><div className="sea sea-one"/><div className="sea sea-two"/><div className="sea sea-three"/><div className="buoy"><span/></div><div className="art-label">MARINE<br/>AWARENESS</div></div>
      </section>

      <section className="notice" role="note"><span className="notice-icon"><Icon name="alert"/></span><div><b>Prototype status</b><p>This dashboard does not currently receive live IMD/INCOIS data. Demo records, if present, are not real warnings. Always verify conditions through official sources before making a trip.</p></div><a href="https://incois.gov.in/oceanservices/osfforecast.jsp" target="_blank" rel="noreferrer">INCOIS forecast <Icon name="external"/></a></section>

      {error && <div className={`error-banner ${connection === 'offline' ? 'offline-banner' : ''}`} role="alert"><Icon name="alert"/><div><b>{connection === 'offline' ? 'Device is offline' : 'Unable to load dashboard data'}</b><span>{error} {browserOnline && 'Check that the FastAPI backend is running, then retry.'} No sample warnings are shown as a fallback.</span><button className="text-action" onClick={loadData} disabled={connection === 'loading'}>Retry connection <Icon name="refresh"/></button></div></div>}

      <section className="section-heading"><div><div className="eyebrow">AT A GLANCE</div><h2>Situation overview</h2></div><span className="updated">{lastUpdated ? `Last checked ${lastUpdated.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}` : 'Not yet checked'}</span></section>
      <div className="stat-grid">
        <article className="stat-card"><span className="stat-icon blue"><Icon name="shield"/></span><div className="stat-label">Current advisories</div><div className="stat-value">{health?.current_advisory_count ?? '—'}<small> / {health?.advisory_count ?? '—'} total</small></div><div className="stat-caption">Passed current-display checks</div></article>
        <article className="stat-card"><span className="stat-icon teal"><Icon name="wave"/></span><div className="stat-label">Tracked sources</div><div className="stat-value">{health?.source_count ?? '—'}</div><div className="stat-caption">Configured source records</div></article>
        <article className="stat-card"><span className="stat-icon amber"><Icon name="clock"/></span><div className="stat-label">Freshness window</div><div className="stat-value">{health ? `${health.freshness_threshold_hours}h` : '—'}</div><div className="stat-caption">Configured source threshold</div></article>
        <article className="stat-card"><span className={`stat-icon ${needsAttention ? 'amber' : 'green'}`}><Icon name={needsAttention ? 'alert' : 'shield'}/></span><div className="stat-label">System status</div><div className={`status-value ${needsAttention ? 'attention' : 'good'}`}>{health ? (needsAttention ? 'Needs attention' : 'Checks passed') : 'Unavailable'}</div><div className="stat-caption">Status snapshot, not live polling</div></article>
      </div>

      <section className="content-grid">
        <div className="panel advisories-panel"><div className="panel-head"><div><div className="eyebrow">BULLETINS</div><h2>Marine advisories</h2><p>Review source text and validity before relying on a bulletin.</p></div><span className="count-pill">{filtered.length} shown</span></div>
          <div className="toolbar"><label className="search-box"><span>⌕</span><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search region, source or text…" aria-label="Search advisories"/></label><select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter advisories"><option value="all">All records</option><option value="current">Current only</option><option value="not-current">Not current</option></select></div>
          {connection === 'connected' && filtered.length === 0 && <div className="empty-state"><span className="empty-icon"><Icon name="wave"/></span><b>No advisories to display</b><p>{advisories.length ? 'Try changing your search or filter.' : 'No records are available from the configured backend. This is not a forecast of safe conditions.'}</p></div>}
          {connection === 'loading' && <div className="empty-state"><div className="loader"/><b>Checking the API…</b></div>}
          {connection === 'error' && <div className="empty-state"><span className="empty-icon"><Icon name="alert"/></span><b>Advisories unavailable</b><p>Connect to the backend to load records. We will not substitute invented data.</p><button className="text-action" onClick={loadData}>Try again <Icon name="refresh"/></button></div>}
          <div className="advisory-list">{filtered.map((item) => <article className="advisory-card" key={item.id}><div className="advisory-card-top"><span className={`badge ${item.is_current ? 'badge-current' : 'badge-stale'}`}><i/>{item.is_current ? 'Passed current checks' : 'Not confirmed current'}</span>{item.is_demo && <span className="demo-tag">DEMO</span>}<span className="demo-tag">SOURCE NOT VERIFIED</span></div><h3>{item.title || 'No title provided by source'}</h3><div className="advisory-meta"><span><b>Region</b>{item.region || 'Not specified'}</span><span><b>Source</b>{item.source_name || 'Unknown'}</span></div><div className="validity-row"><div><span>Issued</span><b>{dateText(item.issued_at)}</b></div><div><span>Valid from</span><b>{dateText(item.valid_from)}</b></div><div><span>Valid until</span><b>{dateText(item.valid_until)}</b></div></div>{!item.is_current && item.current_reason && <p className="source-error" role="status">{item.current_reason}</p>}<button className="expand-btn" onClick={() => setShowOriginal(showOriginal === item.id ? null : item.id)} aria-expanded={showOriginal === item.id} aria-controls={`source-text-${item.id}`}>{showOriginal === item.id ? 'Hide original source text' : 'View original source text'} <span>{showOriginal === item.id ? '−' : '+'}</span></button>{showOriginal === item.id && <div className="original-text" id={`source-text-${item.id}`}>{item.original_text}<div className="source-footer"><span>Retrieved {dateText(item.retrieved_at)}</span>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Open source <Icon name="external"/></a>}</div></div>}</article>)}</div>
        </div>

        <aside className="panel sources-panel"><div className="panel-head"><div><div className="eyebrow">DATA QUALITY</div><h2>Source health</h2><p>Latest status recorded by the backend.</p></div></div>
          {connection === 'connected' && sources.length === 0 && <div className="source-empty">No source status records have been configured yet.</div>}
          <div className="source-list">{sources.map((source) => <article className="source-item" key={source.source_name}><div className="source-name-row"><span className="source-dot-wrap"><i className={`source-dot ${source.freshness || source.status || 'unknown'}`}/></span><div className="source-name"><b>{source.source_name}</b>{source.is_demo && <small>Demo record</small>}</div><span className={`source-status ${source.freshness || 'unknown'}`}>{sourceLabel(source.freshness || source.status)}</span></div><div className="source-details"><span>Last success</span><b>{dateText(source.last_success_at)}</b></div>{source.last_error && <div className="source-error"><Icon name="alert"/>{source.last_error}</div>}</article>)}</div>
          <div className={`health-note ${needsAttention ? 'health-note-warn' : ''}`}><Icon name={needsAttention ? 'alert' : 'shield'}/><p>{health?.note || 'Connect to the API to see source health. Unknown status must not be interpreted as safe conditions.'}</p></div>
          <div className="official-links"><h3>Official information</h3><a href="https://incois.gov.in/oceanservices/osfforecast.jsp" target="_blank" rel="noreferrer"><span>INCOIS Ocean State Forecast</span><Icon name="external"/></a><a href="https://incois.gov.in/site/SAMUDRA/index.html" target="_blank" rel="noreferrer"><span>INCOIS SAMUDRA</span><Icon name="external"/></a><a href="https://mausam.imd.gov.in/" target="_blank" rel="noreferrer"><span>India Meteorological Department</span><Icon name="external"/></a></div>
        </aside>
      </section>

      <section className="bottom-note"><span className="bottom-icon"><Icon name="shield"/></span><div><b>Safety-first by design</b><p>“Current” means a record passed this prototype’s timestamp and source-health checks. It is not a guarantee of safety, accuracy, or completeness. Do not use this app alone to decide whether to go to sea.</p></div></section>
      <footer><span>© {new Date().getFullYear()} CoastGuard AI · Student prototype</span><span>{hasDemo ? 'Demo records detected' : 'No demo label detected'} · Live official integration not confirmed</span></footer>
    </main>
  </div>;
}

export default App;
