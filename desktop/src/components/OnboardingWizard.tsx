import { useState, useEffect } from 'react';
import type { CSSProperties } from 'react';

const ONBOARDING_KEY = 'sf_onboarding_done';

interface Step {
  title: string;
  content: string;
  icon: string;
  detail: string[];
}

const steps: Step[] = [
  {
    title: '選擇音檔',
    icon: '🎤',
    content: '上傳或拖曳音訊檔案到「音檔轉字幕」頁面',
    detail: ['支援 MP3, WAV, M4A, FLAC, AAC', '最多 4GB 單檔', '可批次處理多個檔案'],
  },
  {
    title: '設定與辨識',
    icon: '⚙️',
    content: '調整語言、說話者分離、辨識提示',
    detail: ['選擇音檔語言（自動偵測或手動指定）', '啟用說話者分離區分不同發言人', '輸入提示幫助 ASR 辨識專業術語'],
  },
  {
    title: '取得結果',
    icon: '📝',
    content: '轉換完成後可直接下載 SRT 字幕、預覽波形與編輯',
    detail: ['下載 SRT 字幕檔案', '逐字時間軸與波形檢視', '編輯字幕文字後重新下載'],
  },
];

const overlay: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 10000,
  backgroundColor: 'rgba(0,0,0,0.7)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const card: CSSProperties = {
  backgroundColor: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius)',
  padding: '32px',
  maxWidth: '520px',
  width: '90%',
  color: 'var(--text-primary)',
};

export default function OnboardingWizard() {
  const [visible, setVisible] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);

  useEffect(() => {
    const done = localStorage.getItem(ONBOARDING_KEY);
    if (!done) setVisible(true);
  }, []);

  const finish = () => {
    localStorage.setItem(ONBOARDING_KEY, 'true');
    setVisible(false);
  };

  if (!visible) return null;

  const step = steps[stepIdx];
  const isLast = stepIdx === steps.length - 1;

  return (
    <div style={overlay}>
      <div style={card}>
        {/* Progress dots */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 24 }}>
          {steps.map((_, i) => (
            <div
              key={i}
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: i === stepIdx ? 'var(--accent)' : 'var(--border)',
                transition: 'background-color 0.3s',
              }}
            />
          ))}
        </div>

        {/* Step icon */}
        <div style={{ fontSize: 48, textAlign: 'center', marginBottom: 16 }}>
          {step.icon}
        </div>

        {/* Step title */}
        <h2 style={{ textAlign: 'center', fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
          {step.title}
        </h2>

        {/* Step content */}
        <p style={{ textAlign: 'center', fontSize: 14, color: 'var(--text-secondary)', marginBottom: 20 }}>
          {step.content}
        </p>

        {/* Detail list */}
        <ul style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.8, paddingLeft: 16, marginBottom: 24 }}>
          {step.detail.map((d, i) => (
            <li key={i}>{d}</li>
          ))}
        </ul>

        {/* Buttons */}
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
          <button
            onClick={finish}
            style={{
              backgroundColor: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
              padding: '8px 16px',
              borderRadius: 'var(--radius)',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            跳過
          </button>
          <div style={{ display: 'flex', gap: 8 }}>
            {stepIdx > 0 && (
              <button
                onClick={() => setStepIdx((i) => i - 1)}
                style={{
                  backgroundColor: 'var(--bg-hover)',
                  border: 'none',
                  color: 'var(--text-primary)',
                  padding: '8px 16px',
                  borderRadius: 'var(--radius)',
                  cursor: 'pointer',
                  fontSize: 13,
                }}
              >
                上一步
              </button>
            )}
            <button
              onClick={() => (isLast ? finish() : setStepIdx((i) => i + 1))}
              style={{
                backgroundColor: 'var(--accent)',
                border: 'none',
                color: '#fff',
                padding: '8px 20px',
                borderRadius: 'var(--radius)',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {isLast ? '開始使用' : '下一步'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
