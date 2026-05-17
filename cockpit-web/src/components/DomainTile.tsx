import { Link } from 'react-router-dom';
import type { Domain } from '../types';

interface DomainTileProps {
  domain: Domain;
}

export default function DomainTile({ domain }: DomainTileProps) {
  return (
    <Link to={`/domains/${domain.id}`} className="tile" aria-label={`Open ${domain.name}`}>
      <div className="tile__icon">{domain.icon ?? '📁'}</div>
      <div className="tile__name">{domain.name}</div>
      {(domain.unreadCount ?? 0) > 0 ? <span className="tile__badge">{domain.unreadCount}</span> : null}
      {domain.urgent ? <span className="tile__urgent">Urgent</span> : null}
    </Link>
  );
}
