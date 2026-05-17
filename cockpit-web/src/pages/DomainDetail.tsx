import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getDomainActivity, getDomainDetail } from '../lib/api';
import type { ActivityEntry, DomainDetail } from '../types';

export default function DomainDetailPage() {
  const { id = '' } = useParams();
  const [domain, setDomain] = useState<DomainDetail | null>(null);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [detail, events] = await Promise.all([getDomainDetail(id), getDomainActivity(id)]);
        setDomain(detail);
        setActivity(events.slice(0, 10));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load domain');
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [id]);

  if (loading) return <section className="page">Loading domain…</section>;
  if (error || !domain)
    return <section className="page state state--error">{error || 'Domain not found.'}</section>;

  return (
    <section className="page">
      <header className="page__header">
        <p>
          <Link to="/">← Domains</Link>
        </p>
        <h1>
          {domain.icon ?? '📁'} {domain.name}
        </h1>
        <p>Context confidence: {domain.confidence ?? 0}</p>
      </header>

      <article className="card">
        <h2>Summary</h2>
        <p>{domain.summary ?? 'No summary available.'}</p>
      </article>

      <article className="card">
        <h2>Tasks</h2>
        {domain.tasks.length === 0 ? (
          <p>No open tasks.</p>
        ) : (
          <ul>
            {domain.tasks.map((task) => (
              <li key={task.id}>
                <strong>{task.title}</strong> · {task.priority}
              </li>
            ))}
          </ul>
        )}
      </article>

      <article className="card">
        <h2>Recent activity</h2>
        <ul>
          {activity.map((entry) => (
            <li key={entry.id}>
              <strong>{new Date(entry.createdAt).toLocaleString()}</strong> — {entry.text}
            </li>
          ))}
        </ul>
      </article>
    </section>
  );
}
