import { NavLink, Route, Routes, useLocation } from 'react-router-dom';
import VoiceTextBar from './components/VoiceTextBar';
import BriefingPage from './pages/Briefing';
import DomainDetailPage from './pages/DomainDetail';
import Home from './pages/Home';

function useVoiceContext() {
  const location = useLocation();
  if (location.pathname.startsWith('/domains/')) {
    const domainId = location.pathname.split('/')[2];
    return { page: 'domain', domainId };
  }
  if (location.pathname.startsWith('/briefing')) return { page: 'briefing' };
  return { page: 'home' };
}

export default function App() {
  const context = useVoiceContext();

  return (
    <div className="app-shell">
      <nav className="top-nav">
        <NavLink to="/">Domains</NavLink>
        <NavLink to="/briefing">Briefing</NavLink>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/domains/:id" element={<DomainDetailPage />} />
          <Route path="/briefing" element={<BriefingPage />} />
        </Routes>
      </main>
      <VoiceTextBar context={context} />
    </div>
  );
}
