import { useEffect, useState } from 'react';
import { getBriefing } from '../lib/api';
import type { BriefingData } from '../types';

export default function BriefingPage() {
  const [briefing, setBriefing] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        setBriefing(await getBriefing());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load briefing.');
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  return (
    <section className="page">
      <header className="page__header">
        <h1>Daily Briefing</h1>
        <p>{briefing?.date}</p>
      </header>

      {loading ? <p>Loading briefing…</p> : null}
      {error ? <p className="state state--error">{error}</p> : null}

      {briefing ? (
        <>
          <article className="card">
            <h2>Calendar</h2>
            <ul>
              {briefing.calendar.map((item) => (
                <li key={`${item.title}-${item.start}`}>
                  <strong>{item.title}</strong> · {new Date(item.start).toLocaleTimeString()} -{' '}
                  {new Date(item.end).toLocaleTimeString()}
                </li>
              ))}
            </ul>
          </article>

          <article className="card">
            <h2>Urgent</h2>
            <ul>{briefing.urgent.map((item) => <li key={item}>{item}</li>)}</ul>
          </article>

          <article className="card">
            <h2>Overnight handled</h2>
            <ul>{briefing.overnight.map((item) => <li key={item}>{item}</li>)}</ul>
          </article>

          <article className="card">
            <h2>Decisions needed</h2>
            <ul>{briefing.decisions.map((item) => <li key={item}>{item}</li>)}</ul>
            {briefing.weather ? (
              <p>
                Weather: {briefing.weather.tempF}°F, {briefing.weather.summary}
              </p>
            ) : null}
          </article>
        </>
      ) : null}
    </section>
  );
}
