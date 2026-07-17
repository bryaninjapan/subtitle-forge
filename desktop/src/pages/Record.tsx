import { useState, useEffect, useRef } from 'react';

export default function Record() {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [duration, setDuration] = useState<number>(0);
  const [micDevice, setMicDevice] = useState<string>('default');
  const [lang, setLang] = useState<string>('auto');
  const [autosave, setAutosave] = useState<boolean>(false);
  const [subtitles, setSubtitles] = useState<string[]>([]);
  
  const timerRef = useRef<any>(null);
  const simulationRef = useRef<any>(null);

  // Timer effect
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRecording]);

  // Simulation of incoming real-time speech segments
  useEffect(() => {
    if (isRecording) {
      const phrases = [
        '哈囉，測試麥克風音訊收音中。',
        '端點語音活動偵測 (VAD) 運行良好。',
        '偵測到說話停頓，正在串接 Whisper 辨識 API...',
        '今日會議重點為 Subtitle Forge 跨平台介面整合測試。',
        '測試完畢，辨識速度正常，模型輸出繁體中文字幕精確度極高。'
      ];
      let index = 0;

      simulationRef.current = setInterval(() => {
        if (index < phrases.length) {
          const now = new Date();
          const timestamp = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
          setSubtitles((prev) => [...prev, `[${timestamp}] ${phrases[index]}`]);
          index++;
        }
      }, 4000);
    } else {
      if (simulationRef.current) {
        clearInterval(simulationRef.current);
      }
    }
    return () => {
      if (simulationRef.current) {
        clearInterval(simulationRef.current);
      }
    };
  }, [isRecording]);

  const handleToggleRecord = () => {
    if (!isRecording) {
      setIsRecording(true);
      setDuration(0);
    } else {
      setIsRecording(false);
    }
  };

  const handleClear = () => {
    setSubtitles([]);
  };

  const handleSaveSubtitles = () => {
    if (subtitles.length === 0) {
      alert('目前尚無即時辨識字幕可供儲存。');
      return;
    }

    // Build plain text or srt-like format
    const textContent = subtitles.join('\n');
    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `live_record_${new Date().toISOString().slice(0,10)}.txt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleRefreshMics = () => {
    alert('已成功重新整理並讀取系統麥克風與音訊核心通道。');
  };

  const formatTimer = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>錄製轉換</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
          即時錄音、端點切分、語音活動偵測 (VAD) 本地化辨識。
        </p>
      </div>

      {/* Control row */}
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '14px 16px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>麥克風:</span>
          <select
            value={micDevice}
            onChange={(e) => setMicDevice(e.target.value)}
            disabled={isRecording}
            style={{
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              color: 'var(--text-primary)',
              padding: '6px 12px',
              fontSize: '13px',
              outline: 'none',
              cursor: isRecording ? 'not-allowed' : 'pointer',
            }}
          >
            <option value="default">預設麥克風 (System Default)</option>
            <option value="highdef">高解析度立體聲聲卡輸入</option>
            <option value="virtual">虛擬音訊線路 (Virtual Audio Cable)</option>
          </select>
          <button
            onClick={handleRefreshMics}
            disabled={isRecording}
            style={{
              backgroundColor: 'var(--bg-hover)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              padding: '6px 12px',
              fontSize: '13px',
              cursor: isRecording ? 'not-allowed' : 'pointer',
            }}
          >
            重新整理
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>語言:</span>
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value)}
            disabled={isRecording}
            style={{
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              color: 'var(--text-primary)',
              padding: '6px 12px',
              fontSize: '13px',
              outline: 'none',
              cursor: isRecording ? 'not-allowed' : 'pointer',
            }}
          >
            <option value="auto">自動辨識 (Auto Detect)</option>
            <option value="zh">繁體中文 (zh-TW)</option>
            <option value="en">英文 (en-US)</option>
            <option value="ja">日文 (ja-JP)</option>
          </select>
        </div>
      </div>

      {/* Recording card (centered card with large mic button) */}
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '40px 20px',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px',
        }}
      >
        <button
          onClick={handleToggleRecord}
          style={{
            width: '100px',
            height: '100px',
            borderRadius: '50%',
            backgroundColor: isRecording ? 'var(--error)' : 'var(--accent)',
            color: '#ffffff',
            fontSize: '36px',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: isRecording ? '0 0 20px rgba(239, 68, 68, 0.4)' : '0 4px 12px rgba(0,0,0,0.3)',
            transition: 'background-color 0.2s, transform 0.1s, box-shadow 0.2s',
          }}
          onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.95)')}
          onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
        >
          {isRecording ? '⏹' : '🎤'}
        </button>

        <div
          style={{
            fontSize: '36px',
            fontWeight: 'bold',
            fontFamily: 'monospace',
            color: isRecording ? 'var(--error)' : 'var(--text-primary)',
            letterSpacing: '1px',
          }}
        >
          {formatTimer(duration)}
        </div>

        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          {isRecording ? '正在即時辨識中，說話時聲波會自動回傳...' : '錄製轉換：偵測到說話停頓時才自動完成分段辨識'}
        </p>
      </div>

      {/* Real-time subtitle area */}
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 'bold' }}>即時字幕</h3>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Auto save toggle slider */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>即時存檔:</span>
              <label style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer', gap: '6px' }}>
                <input
                  type="checkbox"
                  checked={autosave}
                  onChange={(e) => setAutosave(e.target.checked)}
                  style={{ display: 'none' }}
                />
                <div
                  style={{
                    position: 'relative',
                    width: '36px',
                    height: '18px',
                    backgroundColor: autosave ? 'var(--accent)' : 'var(--bg-hover)',
                    borderRadius: '9px',
                    transition: 'background-color 0.2s',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      top: '2px',
                      left: autosave ? '20px' : '2px',
                      width: '14px',
                      height: '14px',
                      borderRadius: '50%',
                      backgroundColor: '#ffffff',
                      transition: 'left 0.2s',
                    }}
                  />
                </div>
              </label>
            </div>

            <button
              onClick={handleClear}
              style={{
                backgroundColor: 'var(--bg-hover)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                padding: '6px 12px',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              清除
            </button>

            <button
              onClick={handleSaveSubtitles}
              disabled={subtitles.length === 0}
              style={{
                backgroundColor: subtitles.length === 0 ? 'var(--bg-hover)' : 'var(--accent)',
                color: subtitles.length === 0 ? 'var(--text-muted)' : '#ffffff',
                border: 'none',
                borderRadius: 'var(--radius)',
                padding: '6px 14px',
                fontSize: '13px',
                fontWeight: '600',
                cursor: subtitles.length === 0 ? 'not-allowed' : 'pointer',
              }}
            >
              儲存字幕
            </button>
          </div>
        </div>

        {/* Dynamic Speech Display */}
        <div
          style={{
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius)',
            border: '1px solid var(--border)',
            minHeight: '140px',
            maxHeight: '260px',
            overflowY: 'auto',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          {subtitles.length === 0 ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', minHeight: '110px', color: 'var(--text-muted)', fontSize: '13px' }}>
              開始錄音後，辨識結果會在此處逐段且即時出現...
            </div>
          ) : (
            subtitles.map((subtitle, idx) => (
              <div
                key={idx}
                style={{
                  fontSize: '14px',
                  lineHeight: '1.5',
                  color: idx === subtitles.length - 1 ? 'var(--accent)' : 'var(--text-primary)',
                  fontWeight: idx === subtitles.length - 1 ? '500' : '400',
                  paddingBottom: '6px',
                  borderBottom: '1px dashed var(--border)',
                }}
              >
                {subtitle}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
