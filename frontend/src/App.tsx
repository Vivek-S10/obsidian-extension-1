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

function App() {
  const [vaultPath, setVaultPath] = useState('');
  const [phase, setPhase] = useState<'entry' | 'validation' | 'search'>('entry');
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Result[]>([]);

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

  return (
    <div className="app-container">
      <div className="glass-panel">
        <h1>Semantic Local Discovery</h1>
        
        {error && (
          <div style={{ color: 'var(--danger-color)', marginBottom: '1rem', textAlign: 'center' }}>
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
            <h3 style={{ textAlign: 'center' }}>Vault Analysis Complete</h3>
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
            
            <p style={{color: 'var(--text-secondary)', marginBottom: '1rem', textAlign: 'center'}}>
              {stats.new_or_modified > 0 
                ? `${stats.new_or_modified} files need to be processed to sync the knowledge base.` 
                : 'Knowledge base is completely up to date.'}
            </p>

            <button className="btn btn-primary" onClick={handleEmbed} disabled={loading}>
              {loading ? 'Building Knowledge Base (this may take a while)...' : 'Build / Sync Knowledge Base'}
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
                placeholder="e.g. How do I configure my environment?"
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <button className="btn btn-primary" onClick={handleSearch} disabled={loading || !query}>
              {loading ? 'Searching...' : 'Search'}
            </button>

            {results.length > 0 && (
              <div className="results-container">
                {results.map((res, i) => (
                  <div key={i} className="result-card">
                    <div className="result-file-name">{res.file_name}</div>
                    <div className="result-snippet">"{res.chunk_text}"</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--border-color)', marginTop: '0.5rem', wordBreak: 'break-all' }}>
                      {res.file_path}
                    </div>
                    <div className="result-distance">
                      Proximity Score: {(1 - res.distance).toFixed(4)}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {results.length === 0 && query && !loading && !error && (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '1rem' }}>
                No significant matches found.
              </p>
            )}
            
            <button 
              style={{ marginTop: '2rem', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-secondary)' }} 
              className="btn btn-primary" 
              onClick={() => setPhase('entry')}
            >
              Change Vault Path
            </button>
          </div>
        )}

      </div>
    </div>
  )
}

export default App
