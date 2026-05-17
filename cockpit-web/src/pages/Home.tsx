import { useEffect, useState } from 'react';
import DomainTile from '../components/DomainTile';
import { getDomains } from '../lib/api';
import type { Domain } from '../types';

export default function Home() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        setDomains(await getDomains());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load domains.');
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  return (
    <section className="page">
      <header className="page__header">
        <h1>NovaCore Cockpit</h1>
        <p>Domain grid</p>
      </header>
      {loading ? <p>Loading domains…</p> : null}
      {error ? <p className="state state--error">{error}</p> : null}
      {!loading && !error ? (
        <div className="tile-grid">
          {domains.map((domain) => (
            <DomainTile key={domain.id} domain={domain} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
