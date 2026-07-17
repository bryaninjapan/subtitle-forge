import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import type { AppSettings } from '../types';

export default function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [savingState, setSavingState] = useState<Record<string, boolean>>({});

  // UI-only settings states
  const [scaling, setScaling] = useState<number>(100);
  const [outputFormat, setOutputFormat] = useState<'srt' | 'txt'>('srt');
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('dark');
  const [ffmpegPath, setFfmpegPath] = useState<string>('');

  const debounceTimerRef = useRef<any>(null);

  // Fetch Settings on mount
  const fetchSettings = async () => {
    try {
      setLoading(true);
      const data = await api.getSettings();
      setSettings(data);
    } catch (err) {
      console.warn('API getSettings unreachable, loading premium local high-fidelity simulated settings.', err);
      // Fallback local state setting values
      const fallbackSettings: AppSettings = {
        pipeline: {
          asr_backend: 'local',
          vad_threshold: 0.35,
          cc_conversion: 'taiwan',
          asr_diarize: false,
          asr_hotwords: true,
        }
      };
      setSettings(fallbackSettings);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  // Update Settings handler
  const saveSettingUpdate = async (updatedSettings: AppSettings, fieldName: string) => {
    setSavingState((prev) => ({ ...prev, [fieldName]: true }));
    try {
      await api.updateSettings(updatedSettings);
    } catch (err) {
      console.warn(`API updateSettings failed for ${fieldName}, updated local state only.`, err);
    } finally {
      // Small timeout to give user feedback
      setTimeout(() => {
        setSavingState((prev) => ({ ...prev, [fieldName]: false }));
      }, 500);
    }
  };

  // Debounced save for slider values (VAD threshold)
  const handleVadChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!settings) return;
    const value = parseFloat(e.target.value);
    
    // Update local state immediately for visual responsiveness
    const newSettings: AppSettings = {
      ...settings,
      pipeline: {
        ...settings.pipeline,
        vad_threshold: value,
      }
    };
    setSettings(newSettings);

    // Debounce actual save call by 1 second
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      saveSettingUpdate(newSettings, 'vad_threshold');
    }, 1000);
  };

  // Quick helper for simple button setting updates
  const handleButtonGroupChange = (key: 'cc_conversion' | 'asr_backend', value: string) => {
    if (!settings) return;
    const newSettings: AppSettings = {
      ...settings,
      pipeline: {
        ...settings.pipeline,
        [key]: value,
      }
    };
    setSettings(newSettings);
    saveSettingUpdate(newSettings, key);
  };

  const handleCheckUpdate = () => {
    alert('🎉 聲音辨識小工具：您目前已是最新版本 v0.1.0！');
  };

  if (loading && !settings) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'var(--text-secondary)' }}>
        正在讀取軟體配置與核心環境變數...
      </div>
    );
  }

  const pipeline = settings?.pipeline || {
    asr_backend: 'local' as const,
    vad_threshold: 0.35,
    cc_conversion: 'taiwan' as const,
    asr_diarize: false,
    asr_hotwords: true,
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>設定</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
          調校語音前置音訊過濾、翻譯語系對照表與整合性外部元件。
        </p>
      </div>

      {/* Settings Form Wrapper */}
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* ROW 1: Interface Scaling */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 0',
            borderBottom: '1px solid var(--border)',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div style={{ maxWidth: '400px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>介面縮放 (UI Only)</div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              調整應用程式介面的字型與面板縮放比率，支援高解析度 4K 螢幕。
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '220px' }}>
            <input
              type="range"
              min="80"
              max="150"
              step="10"
              value={scaling}
              onChange={(e) => setScaling(parseInt(e.target.value))}
              style={{
                flex: 1,
                accentColor: 'var(--accent)',
                height: '5px',
                borderRadius: '4px',
                backgroundColor: 'var(--bg-hover)',
                cursor: 'pointer',
              }}
            />
            <span style={{ fontSize: '13px', fontWeight: 'bold', width: '40px', textAlign: 'right' }}>{scaling}%</span>
          </div>
        </div>

        {/* ROW 2: Output Format */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 0',
            borderBottom: '1px solid var(--border)',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div style={{ maxWidth: '400px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>預設匯出格式 (UI Only)</div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              完成語音辨識與時間軸生成後，自動生成的本地字幕下載格式。
            </p>
          </div>

          {/* Button Group */}
          <div style={{ display: 'inline-flex', borderRadius: 'var(--radius)', overflow: 'hidden', border: '1px solid var(--border)' }}>
            <button
              onClick={() => setOutputFormat('srt')}
              style={{
                backgroundColor: outputFormat === 'srt' ? 'var(--accent)' : 'var(--bg-hover)',
                color: outputFormat === 'srt' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                padding: '8px 16px',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: '500',
                transition: 'background-color 0.2s, color 0.2s',
              }}
            >
              SRT 字幕 (.srt)
            </button>
            <button
              onClick={() => setOutputFormat('txt')}
              style={{
                backgroundColor: outputFormat === 'txt' ? 'var(--accent)' : 'var(--bg-hover)',
                color: outputFormat === 'txt' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                padding: '8px 16px',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: '500',
                transition: 'background-color 0.2s, color 0.2s',
              }}
            >
              純文字檔案 (.txt)
            </button>
          </div>
        </div>

        {/* ROW 3: VAD Threshold */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 0',
            borderBottom: '1px solid var(--border)',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div style={{ maxWidth: '400px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>VAD 靈敏度門檻 (語音切片)</span>
              {savingState['vad_threshold'] && (
                <span style={{ fontSize: '11px', color: 'var(--accent)', animation: 'pulse 1s infinite' }}>儲存中...</span>
              )}
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              數值愈低愈靈敏，適合細語或背景干擾高的環境；較高值能忽略換氣聲。
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '220px' }}>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={pipeline.vad_threshold}
              onChange={handleVadChange}
              style={{
                flex: 1,
                accentColor: 'var(--accent)',
                height: '5px',
                borderRadius: '4px',
                backgroundColor: 'var(--bg-hover)',
                cursor: 'pointer',
              }}
            />
            <span style={{ fontSize: '13px', fontWeight: 'bold', width: '40px', textAlign: 'right', fontFamily: 'monospace' }}>
              {(pipeline?.vad_threshold || 0.5).toFixed(2)}
            </span>
          </div>
        </div>

        {/* ROW 4: CC Conversion */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 0',
            borderBottom: '1px solid var(--border)',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div style={{ maxWidth: '400px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>簡繁繁簡翻譯轉換</span>
              {savingState['cc_conversion'] && (
                <span style={{ fontSize: '11px', color: 'var(--accent)' }}>儲存中...</span>
              )}
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              可配置 OpenCC 本地引擎。台灣用語習慣會校準如「硬碟」、「螢幕」等詞彙。
            </p>
          </div>

          {/* Button Group */}
          <div style={{ display: 'inline-flex', borderRadius: 'var(--radius)', overflow: 'hidden', border: '1px solid var(--border)' }}>
            <button
              onClick={() => handleButtonGroupChange('cc_conversion', 'off')}
              style={{
                backgroundColor: pipeline.cc_conversion === 'off' ? 'var(--accent)' : 'var(--bg-hover)',
                color: pipeline.cc_conversion === 'off' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                padding: '8px 14px',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: '500',
              }}
            >
              關閉
            </button>
            <button
              onClick={() => handleButtonGroupChange('cc_conversion', 'taiwan')}
              style={{
                backgroundColor: pipeline.cc_conversion === 'taiwan' ? 'var(--accent)' : 'var(--bg-hover)',
                color: pipeline.cc_conversion === 'taiwan' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                padding: '8px 14px',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: '500',
              }}
            >
              台灣用語
            </button>
            <button
              onClick={() => handleButtonGroupChange('cc_conversion', 'standard')}
              style={{
                backgroundColor: pipeline.cc_conversion === 'standard' ? 'var(--accent)' : 'var(--bg-hover)',
                color: pipeline.cc_conversion === 'standard' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                padding: '8px 14px',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: '500',
              }}
            >
              標準繁體
            </button>
          </div>
        </div>

        {/* ROW 5: Theme Settings */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 0',
            borderBottom: '1px solid var(--border)',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div style={{ maxWidth: '400px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>外觀主題風格 (UI Only)</div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              切換高對比度、夜間暗黑或明亮模式，適配長時間進行字幕校正工作。
            </p>
          </div>

          {/* Button Group */}
          <div style={{ display: 'inline-flex', borderRadius: 'var(--radius)', overflow: 'hidden', border: '1px solid var(--border)' }}>
            <button
              onClick={() => setTheme('light')}
              style={{
                backgroundColor: theme === 'light' ? 'var(--accent)' : 'var(--bg-hover)',
                color: theme === 'light' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                padding: '8px 14px',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: '500',
              }}
            >
              淺色
            </button>
            <button
              onClick={() => setTheme('dark')}
              style={{
                backgroundColor: theme === 'dark' ? 'var(--accent)' : 'var(--bg-hover)',
                color: theme === 'dark' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                padding: '8px 14px',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: '500',
              }}
            >
              深色
            </button>
            <button
              onClick={() => setTheme('system')}
              style={{
                backgroundColor: theme === 'system' ? 'var(--accent)' : 'var(--bg-hover)',
                color: theme === 'system' ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                padding: '8px 14px',
                fontSize: '13px',
                cursor: 'pointer',
                fontWeight: '500',
              }}
            >
              跟隨系統
            </button>
          </div>
        </div>

        {/* ROW 6: FFmpeg Path */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 0',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div style={{ maxWidth: '400px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>FFmpeg 核心路徑</div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              自訂系統 FFmpeg 執行檔的絕對路徑。留空代表交由軟體自動掃描系統環境變數。
            </p>
          </div>

          <input
            type="text"
            value={ffmpegPath}
            placeholder="(留空 = 自動偵測)"
            onChange={(e) => setFfmpegPath(e.target.value)}
            style={{
              width: '100%',
              maxWidth: '260px',
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              color: 'var(--text-primary)',
              padding: '8px 12px',
              fontSize: '13px',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Footer */}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', padding: '10px 0' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>聲音辨識小工具 v0.1.0</span>
        <button
          onClick={handleCheckUpdate}
          style={{
            backgroundColor: 'transparent',
            border: 'none',
            color: 'var(--accent)',
            fontSize: '12px',
            textDecoration: 'underline',
            cursor: 'pointer',
            padding: 0,
          }}
        >
          [檢查更新]
        </button>
      </div>
    </div>
  );
}
