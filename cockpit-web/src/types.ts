export interface Domain {
  id: string;
  name: string;
  icon?: string | null;
  unreadCount?: number;
  urgent?: boolean;
}

export interface DomainDetail extends Domain {
  confidence?: number;
  summary?: string;
  tasks: Array<{
    id: string;
    title: string;
    priority: 'low' | 'med' | 'high' | 'urgent' | string;
    dueAt?: string | null;
  }>;
  subdomains: Array<{ id: string; name: string }>;
}

export interface ActivityEntry {
  id: string;
  createdAt: string;
  source: string;
  text: string;
}

export interface BriefingData {
  date: string;
  calendar: Array<{ title: string; start: string; end: string }>;
  urgent: string[];
  overnight: string[];
  decisions: string[];
  weather?: { tempF: number; summary: string };
}

export interface RookResponse {
  reply: string;
  route?: string;
  confidence?: number;
}

export interface VoiceContext {
  page: string;
  domainId?: string;
}
