import type { CSSProperties } from 'react';

const s: Record<string, CSSProperties> = {
  wrap: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    gap: '12px',
    color: 'var(--text-secondary)',
    textAlign: 'center',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid var(--border)',
    borderTopColor: 'var(--accent)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  errorBox: {
    backgroundColor: 'rgba(239,68,68,0.1)',
    border: '1px solid var(--error)',
    borderRadius: 'var(--radius)',
    padding: '16px 20px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    color: 'var(--error)',
    fontSize: '14px',
  },
  retryBtn: {
    marginLeft: 'auto',
    backgroundColor: 'var(--bg-hover)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    padding: '6px 14px',
    fontSize: '12px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  emptyIcon: { fontSize: '48px' },
  emptyTitle: { fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' },
  emptyDesc: { fontSize: '13px', color: 'var(--text-muted)', maxWidth: 300 },
};

export function LoadingSpinner({ message = '載入中...' }: { message?: string }) {
  return (
    <div style={s.wrap}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <div style={s.spinner} />
      <span>{message}</span>
    </div>
  );
}

export function ErrorBanner({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div style={s.errorBox}>
      <span>⚠️</span>
      <span>{message}</span>
      {onRetry && (
        <button style={s.retryBtn} onClick={onRetry}>
          重試
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  icon = '📁',
  title,
  description,
}: {
  icon?: string;
  title: string;
  description?: string;
}) {
  return (
    <div style={s.wrap}>
      <div style={s.emptyIcon}>{icon}</div>
      <div style={s.emptyTitle}>{title}</div>
      {description && <div style={s.emptyDesc}>{description}</div>}
    </div>
  );
}
