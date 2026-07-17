import { http, HttpResponse } from 'msw';

const BASE = 'http://localhost:5000';

export const handlers = [
  // Pipeline
  http.post(`${BASE}/pipeline`, () =>
    HttpResponse.json({
      task_id: 'test_task_001',
      file: 'test_audio.mp3',
      status: 'queued',
      translate: false,
      notes: false,
      chapters: false,
    })
  ),

  // Progress
  http.get(`${BASE}/progress`, () =>
    HttpResponse.json({
      test_task_001: {
        file: 'test_audio.mp3',
        pct: 100,
        stage: 'done',
        message: 'Complete!',
      },
    })
  ),

  // Waveform
  http.get(`${BASE}/waveform/:taskId`, () =>
    HttpResponse.json({
      peaks: [0.1, 0.3, 0.5, 0.7, 0.9, 0.6, 0.4, 0.2],
      num_peaks: 8,
    })
  ),

  // Timestamps
  http.get(`${BASE}/timestamps/:taskId`, () =>
    HttpResponse.json({
      words: [
        { text: '歡迎', start: 0.5, end: 1.0 },
        { text: '使用', start: 1.1, end: 1.5 },
        { text: '字幕', start: 1.6, end: 2.0 },
      ],
      language: 'zh',
    })
  ),

  // Settings
  http.get(`${BASE}/settings`, () =>
    HttpResponse.json({
      pipeline: {
        asr_backend: 'local',
        vad_threshold: 0.35,
        cc_conversion: 'taiwan',
      },
    })
  ),

  http.post(`${BASE}/settings`, () =>
    HttpResponse.json({ status: 'ok' })
  ),

  // Models
  http.get(`${BASE}/models/status`, () =>
    HttpResponse.json({
      models: [
        { id: 'qwen3-asr-0.6b', repo: 'Qwen/Qwen3-ASR-0.6B', status: 'downloaded', size_mb: 1200 },
        { id: 'qwen3-fa-0.6b', repo: 'Qwen/Qwen3-ForcedAligner-0.6B', status: 'not_downloaded', size_mb: 1800 },
      ],
    })
  ),

  http.get(`${BASE}/models/download/:modelId`, () =>
    HttpResponse.json({ status: 'already_downloaded' })
  ),

  // Endpoint
  http.get(`${BASE}/endpoint/status`, () =>
    HttpResponse.json({ running: false, port: null, url: null, key: null })
  ),

  http.post(`${BASE}/endpoint/start`, () =>
    HttpResponse.json({ status: 'started', port: 11435, url: 'http://192.168.1.1:11435', key: 'test-key-123' })
  ),

  http.post(`${BASE}/endpoint/stop`, () =>
    HttpResponse.json({ status: 'stopped' })
  ),

  // Cancel
  http.post(`${BASE}/cancel/:taskId`, () =>
    HttpResponse.json({ status: 'cancelled' })
  ),

  // Outputs
  http.get(`${BASE}/outputs`, () =>
    HttpResponse.json([
      { name: 'test_audio', files: ['test_audio.srt', 'test_audio.words.json'] },
    ])
  ),

  // History
  http.get(`${BASE}/history`, () =>
    HttpResponse.json([
      { timestamp: '2026-07-17', category: 'transcribe', detail: 'test_audio.mp3', cost: 0.5 },
    ])
  ),
];
