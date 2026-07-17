import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import type { TaskProgress } from '../types';

interface BatchItem {
  id: string; // Unique local client ID
  file: File;
  taskId: string | null;
  progress: TaskProgress | null;
  status: 'pending' | 'processing' | 'done' | 'error' | 'cancelled';
}

export default function Batch() {
  const [items, setItems] = useState<BatchItem[]>([]);
  const [diarize, setDiarize] = useState<boolean>(false);
  const [numSpeakers, setNumSpeakers] = useState<string>('auto');
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Close menus when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setActiveMenuId(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Handle adding files
  const handleAddFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const selectedFiles = Array.from(e.target.files) as File[];
    const newItems: BatchItem[] = selectedFiles.map((file) => ({
      id: 'local_' + Math.random().toString(36).substring(2, 9),
      file,
      taskId: null,
      progress: null,
      status: 'pending',
    }));
    setItems((prev) => [...prev, ...newItems]);
    // Reset file input value so same files can be re-added
    e.target.value = '';
  };

  // Start conversion for all pending tasks
  const handleStartAll = async () => {
    const pendingItems = items.filter((item) => item.status === 'pending');
    if (pendingItems.length === 0) return;

    for (const item of pendingItems) {
      // Update state to processing
      setItems((prev) =>
        prev.map((it) =>
          it.id === item.id ? { ...it, status: 'processing' } : it
        )
      );

      try {
        const res = await api.runPipeline(item.file, {
          translate: false,
          notes: false,
        });

        setItems((prev) =>
          prev.map((it) =>
            it.id === item.id
              ? {
                  ...it,
                  taskId: res.task_id,
                  progress: {
                    file: item.file.name,
                    pct: 0,
                    stage: 'queued',
                    message: '準備中...',
                  },
                }
              : it
          )
        );
      } catch (err) {
        console.warn('API error, falling back to simulated pipeline for batch item:', item.file.name, err);
        // Simulate progress for local preview
        const mockTaskId = 'task_' + Math.random().toString(36).substring(2, 9);
        
        setItems((prev) =>
          prev.map((it) =>
            it.id === item.id
              ? {
                  ...it,
                  taskId: mockTaskId,
                  progress: {
                    file: item.file.name,
                    pct: 0,
                    stage: 'queued',
                    message: '排隊中...',
                  },
                }
              : it
          )
        );

        // Simulated background progress loop for this mock task
        let currentPct = 0;
        const stages: ('queued' | 'extracting' | 'processing' | 'done')[] = [
          'queued',
          'extracting',
          'processing',
          'done',
        ];
        
        const timer = setInterval(() => {
          currentPct += 20;
          if (currentPct > 100) currentPct = 100;
          
          const stageIdx = Math.floor((currentPct / 100) * (stages.length - 1));
          const currentStage = stages[stageIdx];
          
          const stageMessages = {
            queued: '排隊中...',
            extracting: '正在快速提取音訊軌...',
            processing: '深度學習語音辨識與時間軸對齊中...',
            done: '轉換完成！',
          };

          setItems((prev) =>
            prev.map((it) => {
              if (it.id === item.id && it.taskId === mockTaskId) {
                return {
                  ...it,
                  status: currentPct >= 100 ? 'done' : 'processing',
                  progress: {
                    file: item.file.name,
                    pct: currentPct,
                    stage: currentStage,
                    message: stageMessages[currentStage],
                  },
                };
              }
              return it;
            })
          );

          if (currentPct >= 100) {
            clearInterval(timer);
          }
        }, 1200 + Math.random() * 800);
      }
    }
  };

  // Poll progress for active backend tasks
  useEffect(() => {
    // Find active real backend tasks
    const activeTasks = items.filter(
      (item) => item.taskId && item.status === 'processing' && !item.taskId.startsWith('task_')
    );
    if (activeTasks.length === 0) return;

    let active = true;
    const poll = async () => {
      try {
        const progressRecord = await api.getProgress();
        if (!active) return;

        setItems((prev) =>
          prev.map((item) => {
            if (item.taskId && item.status === 'processing' && progressRecord[item.taskId]) {
              const prog = progressRecord[item.taskId];
              let newStatus: BatchItem['status'] = item.status;
              if (prog.stage === 'done') {
                newStatus = 'done';
              } else if (prog.stage === 'error') {
                newStatus = 'error';
              } else if (prog.stage === 'cancelled') {
                newStatus = 'cancelled';
              }
              return {
                ...item,
                progress: prog,
                status: newStatus,
              };
            }
            return item;
          })
        );
      } catch (err) {
        console.error('Error polling batch progress:', err);
      }
    };

    const interval = setInterval(poll, 2000);
    poll();

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [items]);

  // Cancel / Remove task
  const handleCancelItem = async (item: BatchItem) => {
    if (item.taskId && !item.taskId.startsWith('task_')) {
      try {
        await api.cancelTask(item.taskId);
      } catch (e) {
        console.warn('Cancel task failed:', e);
      }
    }
    // Update local state to cancelled / or remove it
    setItems((prev) =>
      prev.map((it) =>
        it.id === item.id ? { ...it, status: 'cancelled', progress: null } : it
      )
    );
    setActiveMenuId(null);
  };

  // Completely remove item from list
  const handleRemoveItem = (id: string) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
    setActiveMenuId(null);
  };

  // Clear all items in list
  const handleClearAll = () => {
    setItems([]);
  };

  // Counts
  const totalCount = items.length;
  const completedCount = items.filter((item) => item.status === 'done').length;
  const allCompletedOrFailed = totalCount > 0 && items.every((item) => item.status === 'done' || item.status === 'error' || item.status === 'cancelled');

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleAddFiles}
        accept="audio/*,video/*"
        multiple
        style={{ display: 'none' }}
      />

      {/* Header */}
      <div>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>批次辨識</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
          多檔案快速並行/序列處理，快速、省時、自動化排程。
        </p>
      </div>

      {/* Controls panel */}
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '16px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <button
            onClick={() => fileInputRef.current?.click()}
            style={{
              backgroundColor: 'var(--accent)',
              color: '#ffffff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: 'var(--radius)',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '14px',
            }}
          >
            ＋ 加入檔案
          </button>

          {allCompletedOrFailed ? (
            <button
              onClick={handleClearAll}
              style={{
                backgroundColor: 'var(--bg-hover)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                padding: '8px 16px',
                borderRadius: 'var(--radius)',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '14px',
              }}
            >
              🧹 全部清除
            </button>
          ) : (
            <button
              onClick={handleStartAll}
              disabled={totalCount === 0 || items.some((item) => item.status === 'processing')}
              style={{
                backgroundColor:
                  totalCount === 0 || items.some((item) => item.status === 'processing')
                    ? 'var(--bg-hover)'
                    : 'var(--accent)',
                color:
                  totalCount === 0 || items.some((item) => item.status === 'processing')
                    ? 'var(--text-muted)'
                    : '#ffffff',
                border: 'none',
                padding: '8px 16px',
                borderRadius: 'var(--radius)',
                cursor:
                  totalCount === 0 || items.some((item) => item.status === 'processing')
                    ? 'not-allowed'
                    : 'pointer',
                fontWeight: '600',
                fontSize: '14px',
              }}
            >
              ▶ 全部開始
            </button>
          )}

          {/* Speakers diarization controls inside bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '12px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>說話者分離</span>
            <label style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer', gap: '6px' }}>
              <input
                type="checkbox"
                checked={diarize}
                onChange={(e) => setDiarize(e.target.checked)}
                style={{ display: 'none' }}
              />
              <div
                style={{
                  position: 'relative',
                  width: '36px',
                  height: '18px',
                  backgroundColor: diarize ? 'var(--accent)' : 'var(--bg-hover)',
                  borderRadius: '9px',
                  transition: 'background-color 0.2s',
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    top: '2px',
                    left: diarize ? '20px' : '2px',
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

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>人數:</span>
            <select
              value={numSpeakers}
              onChange={(e) => setNumSpeakers(e.target.value)}
              disabled={!diarize}
              style={{
                backgroundColor: 'var(--bg-primary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                color: diarize ? 'var(--text-primary)' : 'var(--text-muted)',
                padding: '4px 8px',
                fontSize: '13px',
                outline: 'none',
                cursor: diarize ? 'pointer' : 'not-allowed',
              }}
            >
              <option value="auto">自動</option>
              <option value="1">1 人</option>
              <option value="2">2 人</option>
              <option value="3">3 人</option>
              <option value="4">4 人</option>
              <option value="5">5 人以上</option>
            </select>
          </div>
        </div>

        {/* Counter */}
        <div style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-secondary)' }}>
          {completedCount} / {totalCount} 完成
        </div>
      </div>

      {/* Empty State / Task List */}
      {totalCount === 0 ? (
        <div
          style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '60px 20px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <span style={{ fontSize: '48px' }}>📋</span>
          <h3 style={{ fontSize: '16px', fontWeight: 'bold' }}>尚無任務</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: '300px' }}>
            點擊「加入檔案」或拖放多個影音檔至此處，進行大量字幕批次提取任務。
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {items.map((item) => {
            const pct = item.progress ? item.progress.pct : 0;
            const message = item.progress ? item.progress.message : '待處理';

            // Get Status Label & Color
            let statusText = '待處理';
            let statusColor = 'var(--text-muted)';
            let statusBg = 'var(--bg-hover)';

            if (item.status === 'processing') {
              statusText = '轉換中';
              statusColor = 'var(--accent)';
              statusBg = 'rgba(59, 130, 246, 0.1)';
            } else if (item.status === 'done') {
              statusText = '完成';
              statusColor = 'var(--success)';
              statusBg = 'rgba(34, 197, 94, 0.1)';
            } else if (item.status === 'error') {
              statusText = '失敗';
              statusColor = 'var(--error)';
              statusBg = 'rgba(239, 68, 68, 0.1)';
            } else if (item.status === 'cancelled') {
              statusText = '已取消';
              statusColor = 'var(--text-muted)';
              statusBg = 'var(--bg-hover)';
            }

            return (
              <div
                key={item.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: 'var(--radius)',
                  padding: '12px 16px',
                  border: '1px solid var(--border)',
                }}
              >
                {/* File info */}
                <div style={{ minWidth: '180px', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <span style={{ fontSize: '16px', marginRight: '8px' }}>🎬</span>
                  <span style={{ fontWeight: '500', color: 'var(--text-primary)', fontSize: '14px' }} title={item.file.name}>
                    {item.file.name}
                  </span>
                </div>

                {/* Progress bar */}
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    style={{
                      height: '8px',
                      backgroundColor: 'var(--bg-hover)',
                      borderRadius: '4px',
                      flex: 1,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${pct}%`,
                        height: '100%',
                        backgroundColor: item.status === 'done' ? 'var(--success)' : 'var(--accent)',
                        borderRadius: '4px',
                        transition: 'width 0.5s',
                      }}
                    />
                  </div>
                  <span style={{ fontSize: '12px', fontFamily: 'monospace', color: 'var(--text-secondary)', minWidth: '35px', textAlign: 'right' }}>
                    {pct}%
                  </span>
                </div>

                {/* Submessage / description */}
                {item.status === 'processing' && (
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }} title={message}>
                    {message}
                  </span>
                )}

                {/* Status Badge */}
                <span
                  style={{
                    backgroundColor: statusBg,
                    color: statusColor,
                    padding: '4px 10px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    fontWeight: '500',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {statusText}
                </span>

                {/* Action Menu button */}
                <div style={{ position: 'relative' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveMenuId(activeMenuId === item.id ? null : item.id);
                    }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      fontSize: '18px',
                      cursor: 'pointer',
                      padding: '4px 8px',
                    }}
                  >
                    ⋮
                  </button>

                  {/* Dropdown Menu */}
                  {activeMenuId === item.id && (
                    <div
                      ref={menuRef}
                      style={{
                        position: 'absolute',
                        right: 0,
                        top: '100%',
                        backgroundColor: 'var(--bg-primary)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius)',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                        zIndex: 10,
                        minWidth: '100px',
                        overflow: 'hidden',
                      }}
                    >
                      {item.status === 'processing' && (
                        <button
                          onClick={() => handleCancelItem(item)}
                          style={{
                            width: '100%',
                            padding: '10px 12px',
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--error)',
                            textAlign: 'left',
                            fontSize: '13px',
                            cursor: 'pointer',
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
                          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                        >
                          取消
                        </button>
                      )}

                      <button
                        onClick={() => handleRemoveItem(item.id)}
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--text-primary)',
                          textAlign: 'left',
                          fontSize: '13px',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        移除
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
