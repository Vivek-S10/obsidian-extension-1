import { useState } from 'react'
import './index.css'

type Stats = {
  total_md_files: number;
  new_or_modified: number;
  deleted: number;
};

type Result = {
  file_path: string;
  file_name: string;
  chunk_text: string;
  distance: number;
};

type AIResponse = {
  answer: string;
  sources: { file_name: string; file_path: string }[];
};

type Suggestion = {
  file1_path: string;
  file1_name: string;
  file2_path: string;
  file2_name: string;
  distance: number;
  reason: string;
};

function App() {
  const [vaultPath, setVaultPath] = useState('');
  const [phase, setPhase] = useState<'entry' | 'validation' | 'search' | 'discover'>('entry');
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Result[]>([]);
  const [aiResponse, setAiResponse] = useState<AIResponse | null>(null);

  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const handleScan = async () => {
    if (!vaultPath) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault_path: vaultPath })
      });
      if (!res.ok) throw new Error('Invalid vault path or server error');
      const data = await res.json();
      setStats(data.stats);
      setPhase('validation');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEmbed = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/api/embed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault_path: vaultPath })
      });
      if (!res.ok) throw new Error('Embedding failed. Check server logs.');
      await res.json();
      setPhase('search');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!query) return;
    setLoading(true);
    setError(null);
    setAiResponse(null);
    try {
      const res = await fetch(`http://localhost:8000/api/search?q=${encodeURIComponent(query)}`);
      if (!res.ok) throw new Error('Search failed');
      const data = await res.json();
      setResults(data.results);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAsk = async () => {
    if (!query) return;
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const res = await fetch('http://localhost:8000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'AI Query failed. Is Ollama running?');
      }
      const data = await res.json();
      setAiResponse(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeepLink = (path: string) => {
    const uri = `obsidian://open?path=${encodeURIComponent(path)}`;
    window.location.href = uri;
  };

  const loadSuggestions = async () => {
    setDiscovering(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/api/discover_links?limit=5');
      if (!res.ok) throw new Error('Failed to discover links');
      const data = await res.json();
      setSuggestions(data.suggestions || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDiscovering(false);
    }
  };

  const confirmLink = async (s: Suggestion) => {
    try {
      const res = await fetch('http://localhost:8000/api/confirm_link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file1_path: s.file1_path, file2_path: s.file2_path })
      });
      if (!res.ok) throw new Error('Failed to confirm link');
      setSuggestions(prev => prev.filter(item => item !== s));
    } catch (err: any) {
      setError(err.message);
    }
  };

  const dismissLink = async (s: Suggestion) => {
    try {
      const res = await fetch('http://localhost:8000/api/dismiss_link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file1_path: s.file1_path, file2_path: s.file2_path })
      });
      if (!res.ok) throw new Error('Failed to dismiss link');
      setSuggestions(prev => prev.filter(item => item !== s));
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="app-layout">
      {/* Sidebar Mockup */}
      <div className="sidebar-pane">
        <div className="sidebar-header">
          Local Vault
        </div>
        <div className="sidebar-nav">
          <div className={`nav-item ${phase === 'entry' ? 'active' : ''}`} onClick={() => setPhase('entry')}>
            ⚙️ Configuration
          </div>
          {stats && (
            <div className={`nav-item ${phase === 'validation' ? 'active' : ''}`} onClick={() => setPhase('validation')}>
              📊 Status
            </div>
          )}
          {stats && (
            <div className={`nav-item ${phase === 'search' ? 'active' : ''}`} onClick={() => setPhase('search')}>
              🔍 Search & AI
            </div>
          )}
          {stats && (
            <div className={`nav-item ${phase === 'discover' ? 'active' : ''}`} onClick={() => { setPhase('discover'); loadSuggestions(); }}>
              💡 Discover Links
            </div>
          )}
        </div>
      </div>

      {/* Main Editor/Content Area */}
      <div className="main-pane">
        <div className="content-wrapper">
          <h1 style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem'}}>Semantic Local Discovery</h1>
          
          {error && (
            <div style={{ color: 'var(--danger-color)', border: '1px solid var(--danger-color)', marginBottom: '1rem', padding: '0.75rem', borderRadius: '4px', background: 'rgba(229, 83, 83, 0.1)' }}>
              {error}
            </div>
          )}

          {phase === 'entry' && (
            <div className="phase-container">
              <div className="input-group">
                <label>Absolute Vault Path</label>
                <input 
                  type="text" 
                  value={vaultPath} 
                  onChange={(e) => setVaultPath(e.target.value)} 
                  placeholder="e.g. /Users/name/Documents/Vault"
                  onKeyDown={(e) => e.key === 'Enter' && handleScan()}
                />
              </div>
              <button className="btn btn-primary" onClick={handleScan} disabled={loading || !vaultPath}>
                {loading ? 'Scanning...' : 'Scan Vault'}
              </button>
            </div>
          )}

          {phase === 'validation' && stats && (
            <div className="phase-container">
              <h3>Vault Analysis Complete</h3>
              <div className="stats-grid">
                <div className="stat-box">
                  <div className="stat-value">{stats.total_md_files}</div>
                  <div className="stat-label">Total MD Files</div>
                </div>
                <div className="stat-box">
                  <div className="stat-value" style={{color: 'var(--success-color)'}}>{stats.new_or_modified}</div>
                  <div className="stat-label">New / Modified</div>
                </div>
                <div className="stat-box">
                  <div className="stat-value" style={{color: 'var(--danger-color)'}}>{stats.deleted}</div>
                  <div className="stat-label">Deleted</div>
                </div>
              </div>
              
              <p style={{color: 'var(--text-secondary)', marginBottom: '1rem'}}>
                {stats.new_or_modified > 0 
                  ? `${stats.new_or_modified} files need to be processed to sync the knowledge base.` 
                  : 'Knowledge base is completely up to date.'}
              </p>

              <button className="btn btn-primary" onClick={handleEmbed} disabled={loading}>
                {loading ? 'Building Knowledge Base...' : 'Build / Sync Knowledge Base'}
              </button>
            </div>
          )}

          {phase === 'search' && (
            <div className="phase-container">
              <div className="input-group">
                <label>Natural Language Query</label>
                <input 
                  type="text" 
                  value={query} 
                  onChange={(e) => setQuery(e.target.value)} 
                  placeholder="Search or ask natural language questions..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.shiftKey ? handleAsk() : handleSearch();
                    }
                  }}
                />
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button className="btn btn-primary" style={{flex: 1}} onClick={handleSearch} disabled={loading || !query.trim()}>
                  {loading ? 'Searching...' : 'Search Only'}
                </button>
                <button className="btn btn-ai" style={{flex: 1}} onClick={handleAsk} disabled={loading || !query.trim()}>
                  {loading ? 'Thinking...' : 'Ask AI Assistant'}
                </button>
              </div>

              {aiResponse && (
                <div className="ai-response-panel">
                  <div className="ai-badge">AI ASSISTANT</div>
                  <div className="ai-answer">{aiResponse.answer}</div>
                  {aiResponse.sources.length > 0 && (
                    <div className="ai-sources">
                      <span style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>SOURCES:</span>
                      {aiResponse.sources.reduce((acc: any[], current) => {
                        if (!acc.find(item => item.file_path === current.file_path)) {
                          acc.push(current);
                        }
                        return acc;
                      }, []).map((source, i) => (
                        <span 
                          key={i} 
                          className="source-tag clickable" 
                          onClick={() => handleDeepLink(source.file_path)}
                        >
                          {source.file_name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {results.length > 0 && (
                <div className="results-container">
                  {results.map((res, i) => (
                    <div key={i} className="result-card">
                      <div className="result-header">
                        <div className="result-file-name">{res.file_name}</div>
                        <button className="btn btn-ghost btn-sm" onClick={() => handleDeepLink(res.file_path)}>
                          Open in Obsidian
                        </button>
                      </div>
                      <div className="result-snippet">{res.chunk_text}</div>
                      <div className="result-distance">
                        Score: {(1 - res.distance).toFixed(4)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {results.length === 0 && !aiResponse && query && !loading && !error && (
                <p style={{ color: 'var(--text-secondary)', marginTop: '2rem' }}>
                  No significant matches found.
                </p>
              )}
              
            </div>
          )}

          {phase === 'discover' && (
            <div className="phase-container">
              <h3>Hidden Connections</h3>
              <p style={{ color: 'var(--text-secondary)' }}>
                The AI has proactively found these related notes that are not yet linked.
              </p>

              {discovering && (
                <div style={{ color: 'var(--accent-primary)', marginTop: '1rem' }}>
                  Analyzing vector distances and asking Ollama for justifications...
                </div>
              )}

              {!discovering && suggestions.length === 0 && (
                <p style={{ color: 'var(--text-secondary)', marginTop: '1rem' }}>
                  No new strong connections found at this time.
                </p>
              )}

              {!discovering && suggestions.length > 0 && (
                <div className="results-container">
                  {suggestions.map((s, i) => (
                    <div key={i} className="result-card">
                      <div className="result-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
                          <span className="source-tag">{s.file1_name}</span>
                          <span style={{ color: 'var(--text-secondary)' }}>↔</span>
                          <span className="source-tag">{s.file2_name}</span>
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button className="btn btn-ghost btn-sm" onClick={() => dismissLink(s)}>
                            Dismiss
                          </button>
                          <button className="btn btn-primary btn-sm" onClick={() => confirmLink(s)}>
                            Confirm Link
                          </button>
                        </div>
                      </div>
                      
                      <div className="ai-response-panel" style={{ marginTop: '1rem', padding: '1rem' }}>
                        <div className="ai-badge" style={{ position: 'relative', display: 'inline-block', marginBottom: '0.5rem', top: 0, right: 0 }}>OLLAMA REASONING</div>
                        <div style={{ color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                          {s.reason}
                        </div>
                      </div>
                      
                      <div className="result-distance" style={{ marginTop: '0.5rem' }}>
                        Vector Distance: {s.distance.toFixed(3)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  )
}

export default App
