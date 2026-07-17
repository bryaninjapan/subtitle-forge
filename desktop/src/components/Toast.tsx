import { useState, useCallback, useEffect } from 'react';
import type { CSSProperties } from 'react';

interface ToastMessage {
  id: number;
  type: 'success' | 'error' | 'info';
  message: string;
}

let nextId = 0;
let addToastFn: ((t: Omit<ToastMessage, 'id'>) => void) | null = null;

export function toast(type: ToastMessage['type'], message: string) {
  addToastFn?.({ type, message });
}

const styles: Record<string, CSSProperties> = {
  container: {
    position: 'fixed',
    top: 16,
    right: 16,
    zIndex: 9999,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  item: {
    padding: '10px 16px',
    borderRadius: 'var(--radius)',
    color: '#fff',
    fontSize: 14,
    fontWeight: 500,
    boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
    animation: 'slideIn 0.3s ease',
    minWidth: 200,
    maxWidth: 360,
  },
};

export function ToastContainer() {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const add = useCallback((t: Omit<ToastMessage, 'id'>) => {
    const id = nextId++;
    setMessages((prev) => [...prev, { ...t, id }]);
    setTimeout(() => {
      setMessages((prev) => prev.filter((m) => m.id !== id));
    }, 3000);
  }, []);

  useEffect(() => {
    addToastFn = add;
    return () => { addToastFn = null; };
  }, [add]);

  return (
    <>
      <style>{`@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`}</style>
      <div style={styles.container}>
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              ...styles.item,
              backgroundColor:
                m.type === 'success' ? 'var(--success)' :
                m.type === 'error' ? 'var(--error)' : 'var(--accent)',
            }}
          >
            {m.type === 'success' && '✅ '}
            {m.type === 'error' && '❌ '}
            {m.type === 'info' && 'ℹ️ '}
            {m.message}
          </div>
        ))}
      </div>
    </>
  );
}
