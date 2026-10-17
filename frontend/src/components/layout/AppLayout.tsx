import type { ReactNode } from 'react'
import { ExternalLink, Zap } from 'lucide-react'
import { Badge } from '@/components/ui'
import { useAppMeta } from '@/context/MetaContext'
import './layout.css'

interface AppLayoutProps {
  children: ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { meta, healthy } = useAppMeta()

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div>
          <div className="app-brand">
            <div className="app-brand__icon"><Zap size={20} /></div>
            <div>
              <div className="app-brand__title">{meta?.app_name || 'ForteWatch'}</div>
              <div className="small faint">v0.1.0 • {meta?.environment || 'dev'}</div>
            </div>
          </div>
          <nav className="app-nav">
            <a href="/" className="app-nav__item">Анализ видео</a>
            <a href="/api/docs" target="_blank" rel="noreferrer" className="app-nav__item">
              <ExternalLink size={18} />
              <span className="grow">API docs (Swagger)</span>
            </a>
          </nav>
        </div>
        <div className="app-sidebar__bottom">
          <div className="row between" style={{ fontSize: '0.82rem' }}>
            <span className="muted">Backend</span>
            {healthy === null ? (
              <Badge tone="neutral">Checking…</Badge>
            ) : healthy ? (
              <Badge tone="success" dot>Online</Badge>
            ) : (
              <Badge tone="danger" dot>Offline</Badge>
            )}
          </div>
          <div className="small faint" style={{ textAlign: 'center', fontSize: '0.75rem' }}>
            Local video review
          </div>
        </div>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  )
}
