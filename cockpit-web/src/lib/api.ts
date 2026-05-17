import { hasSupabaseConfig, supabase } from './supabase';
import type {
  ActivityEntry,
  BriefingData,
  Domain,
  DomainDetail,
  RookResponse,
  VoiceContext
} from '../types';

const apiBase = import.meta.env.VITE_API_BASE_URL;

const fallbackDomains: Domain[] = [
  { id: 'meta', name: 'Meta', icon: '🧠', unreadCount: 0 },
  { id: 'ai_systems', name: 'AI Systems', icon: '🤖', unreadCount: 3, urgent: true },
  { id: 'business', name: 'Business', icon: '💼', unreadCount: 2 },
  { id: 'life', name: 'Life', icon: '🏡', unreadCount: 1 }
];

export async function getDomains(): Promise<Domain[]> {
  if (hasSupabaseConfig && supabase) {
    const { data, error } = await supabase
      .from('domains')
      .select('id, name, icon')
      .is('parent_id', null)
      .order('sort_order', { ascending: true })
      .order('name', { ascending: true });

    if (!error && data) {
      return data.map((row) => ({
        id: String(row.id),
        name: String(row.name),
        icon: row.icon ? String(row.icon) : '📁',
        unreadCount: 0,
        urgent: false
      }));
    }
  }

  if (apiBase) {
    const res = await fetch(`${apiBase}/api/domains`);
    if (res.ok) return (await res.json()) as Domain[];
  }

  return fallbackDomains;
}

export async function getDomainDetail(id: string): Promise<DomainDetail> {
  if (apiBase) {
    const res = await fetch(`${apiBase}/api/domains/${id}`);
    if (res.ok) return (await res.json()) as DomainDetail;
  }

  const domain = fallbackDomains.find((item) => item.id === id) ?? {
    id,
    name: id,
    icon: '📁'
  };

  return {
    ...domain,
    confidence: 76,
    summary: `${domain.name} is stable. Key actions are queued for review.`,
    tasks: [
      { id: `${id}-1`, title: 'Review priority items', priority: 'high' },
      { id: `${id}-2`, title: 'Confirm next action with Rook', priority: 'med' }
    ],
    subdomains: []
  };
}

export async function getDomainActivity(id: string): Promise<ActivityEntry[]> {
  if (apiBase) {
    const res = await fetch(`${apiBase}/api/domains/${id}/activity`);
    if (res.ok) return (await res.json()) as ActivityEntry[];
  }

  return [
    {
      id: `${id}-a1`,
      createdAt: new Date().toISOString(),
      source: 'rook',
      text: `Recent ${id} update captured in hot layer.`
    }
  ];
}

export async function getBriefing(): Promise<BriefingData> {
  if (apiBase) {
    const res = await fetch(`${apiBase}/api/briefing`);
    if (res.ok) return (await res.json()) as BriefingData;
  }

  return {
    date: new Date().toISOString().slice(0, 10),
    calendar: [
      {
        title: "Cooper's Landing walkthrough",
        start: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
        end: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString()
      }
    ],
    urgent: ['Approve lender package'],
    overnight: ['Rook closed two follow-ups'],
    decisions: ['Confirm Friday financing call'],
    weather: { tempF: 29, summary: 'Cloudy' }
  };
}

export async function sendText(text: string, context: VoiceContext): Promise<RookResponse> {
  if (apiBase) {
    const res = await fetch(`${apiBase}/api/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, context })
    });
    if (res.ok) return (await res.json()) as RookResponse;
  }

  return {
    reply: `Rook received: "${text}"${context.domainId ? ` in ${context.domainId}` : ''}.`
  };
}
