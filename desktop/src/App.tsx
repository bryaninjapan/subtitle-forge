/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import './styles/global.css';
import type { Page } from './types';
import { ToastContainer } from './components/Toast';

import AudioFile from './pages/AudioFile';
import Batch from './pages/Batch';
import Record from './pages/Record';
import Endpoint from './pages/Endpoint';
import ModelManage from './pages/ModelManage';
import Settings from './pages/Settings';

export default function App() {
  const [page, setPage] = useState<Page>('audio');

  const navItems: { id: Page; label: string; icon: string }[] = [
    { id: 'audio', label: '音檔', icon: '🎬' },
    { id: 'batch', label: '批次', icon: '📋' },
    { id: 'record', label: '錄製', icon: '🎤' },
    { id: 'endpoint', label: '端點', icon: '🔌' },
    { id: 'models', label: '模型', icon: '🤖' },
    { id: 'settings', label: '設定', icon: '⚙️' },
  ];

  const renderContent = () => {
    switch (page) {
      case 'audio':
        return <AudioFile />;
      case 'batch':
        return <Batch />;
      case 'record':
        return <Record />;
      case 'endpoint':
        return <Endpoint />;
      case 'models':
        return <ModelManage />;
      case 'settings':
        return <Settings />;
      default:
        return <AudioFile />;
    }
  };

  return (
    <div id="app-container" style={{ display: 'flex', height: '100vh', width: '100vw' }}>
      {/* Sidebar */}
      <aside
        id="sidebar"
        style={{
          width: 'var(--sidebar-width)',
          minWidth: 'var(--sidebar-width)',
          backgroundColor: 'var(--bg-card)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          height: '100%',
        }}
      >
        <div id="nav-container" style={{ display: 'flex', flexDirection: 'column', paddingTop: '16px' }}>
          {navItems.map((item) => {
            const isActive = page === item.id;
            return (
              <button
                key={item.id}
                id={`nav-item-${item.id}`}
                onClick={() => setPage(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  width: '100%',
                  padding: '12px 16px',
                  border: 'none',
                  borderLeft: isActive ? '4px solid var(--accent)' : '4px solid transparent',
                  backgroundColor: isActive ? 'var(--bg-active)' : 'transparent',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '15px',
                  fontWeight: isActive ? '600' : '400',
                  outline: 'none',
                  transition: 'background-color 0.2s, color 0.2s',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
                }}
              >
                <span style={{ fontSize: '18px' }}>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Sidebar Bottom */}
        <div
          id="sidebar-status"
          style={{
            padding: '16px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: 'var(--success)',
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>模型已就緒</span>
        </div>
      </aside>

      {/* Main Content Area */}
      <main id="main-content" style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
        {renderContent()}
      </main>
      <ToastContainer />
    </div>
  );
}
