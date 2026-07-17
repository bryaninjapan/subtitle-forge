# Discovery: ASR Pipeline Optimization

**Source:** https://guide.haoai.pro/guide/ + https://github.com/dseditor/QwenASRMiniTool
**Goal:** Identify optimization opportunities for subtitle-forge's local ASR pipeline.

---

## 1. Current State

subtitle-forge 目前 ASR 流程：

```
影片/音檔 → FFmpeg loudnorm + 16kHz WAV → Silence Check → Qwen3-ASR-0.6B (MLX) → Segment Grouping → SRT
```

套件：[`mlx_qwen3_asr`](https://github.com/BryanJin0518/mlx-qwen3-asr) — Apple Silicon MLX 原生加速。

### 已用功能
- `transcribe()` with `return_timestamps=True`
- Language detection/forcing
- 基本 segment → subtitle block grouping

---

## 2. mlx_qwen3_asr 已內建但未使用的功能

library 本身已經支援以下能力，subtitle-forge 完全沒用到：

### 🔤 Forced Aligner (字詞級時間戳)

```python
from mlx_qwen3_asr import ForcedAligner
aligner = ForcedAligner()
aligned_words = aligner.align(audio_path, transcript_text)
# Returns: [AlignedWord(text, start_time, end_time), ...]
```

- Model `Qwen/Qwen3-ForcedAligner-0.6B` **已下載在 cache** (1.8GB)
- 可取得**逐字時間軸**（word-level timestamps），而非目前只有 segment-level
- **haoone 最大賣點之一：字詞級對齊率 98%**

### 🗣️ Speaker Diarization (說話者分離)

```python
result = transcribe(audio_path, diarize=True, diarization_num_speakers=2)
# result.speaker_segments = [{speaker, start, end, text}, ...]
```

- Library 已整合，`TranscriptionResult.speaker_segments` 可直接用
- **QwenASRMiniTool 也有此功能**，支援自動或 2-8 人

### ⚡ Speculative Decoding (推測解碼加速)

```python
result = transcribe(audio_path, draft_model="Qwen/Qwen3-ASR-0.6B")
```

- 用較小的 draft model 加速生成
- 對長音頻有顯著加速效果

### 📦 Batch & Async API

```python
results = transcribe_batch([audio1, audio2, ...])
# or
results = await transcribe_async(audio_path)
```

- library 已提供批次/非同步轉錄，subtitle-forge 自己用 for 循環串接

### 📊 Return Chunks

```python
result = transcribe(audio_path, return_chunks=True)
# result.chunks = [{text, start, end, chunk_index, language}, ...]
```

- 可取得每個 audio chunk 的獨立轉錄結果

---

## 3. 對標 haoone.pro 的功能差距

| 功能 | haoone | subtitle-forge | 優先級 |
|------|--------|----------------|--------|
| 本地轉錄 | ✅ | ✅ | - |
| 字詞級對齊 (word alignment) | ✅ 98% | ❌ segment only | **HIGH** |
| 文稿匹配 (transcript matching) | ✅ | ❌ | **HIGH** (CFA 場景) |
| 智能熱詞/辨識提示 | ✅ "越用越準" | ❌ | **HIGH** |
| 智能拆行 | ✅ | ❌ 簡單分組 | MEDIUM |
| 說話者分離 | ❌ (非核心) | ❌ (但 library 已支援) | MEDIUM |
| 批量轉錄 | ✅ | ✅ | - |
| 批量合成字幕 | ✅ | ❌ | LOW |
| 達芬奇/PR 插件 | ✅ | ❌ | OUT OF SCOPE |
| 字幕編輯器 GUI | ✅ | ❌ | LOW |
| VAD (silero-vad) | ✅ (推測) | ❌ 用 ffmpeg | **HIGH** |
| 長音頻優化 (>1h) | ✅ 2h/10min | ❌ 無壓力測試 | MEDIUM |
| CLI / SDK / Agent skill | ✅ | ✅ CLI | - |
| 收費 | 買斷制 | 開源免費 | - |

---

## 4. 對標 QwenASRMiniTool 的功能差距

| 功能 | QwenASRMiniTool | subtitle-forge | 優先級 |
|------|----------------|----------------|--------|
| Speaker Diarization | ✅ | ❌ (library 有) | MEDIUM |
| 辨識提示 (reference text) | ✅ | ❌ | **HIGH** |
| VAD (silero-vad) | ✅ | ❌ | **HIGH** |
| 即時語音辨識 (mic) | ✅ | ❌ | LOW |
| 字幕編輯器 | ✅ | ❌ | LOW |
| 30 種語言 | ✅ | ✅ (透過 library) | - |
| 批次處理 | ✅ | ✅ | - |
| OpenVINO INT8 (CPU) | ✅ | ❌ (MLX 為主力) | LOW (Windows 版) |
| GPU Vulkan | ✅ | ❌ (MLX = 自家 GPU) | LOW |
| Streamlit 前端 | ✅ | ❌ (有 web dashboard) | LOW |
| CustomTkinter GUI | ✅ | ❌ | LOW |

---

## 5. 關鍵發現與建議

### 🎯 效益最高、成本最低的優化

**1. Forced Aligner（字詞級對齊）**
- 套件已內建，model 已在 cache，**一行 code 啟用**
- 產出 word-level timestamps → 可做更精準的字幕拆行、文稿匹配
- 模仿 haoone 的「字詞級對齊率 98%」

**2. VAD 替代 Silence Check**
- 當前 `check_silence()` 用 ffmpeg silencedetect，精度有限
- 改用 silero-vad (MIT license) 可精準偵測語音段落
- 更好處理長靜音、背景噪音場景
- 更精準的 chunking 邊界

**3. 辨識提示 / 熱詞**
- Qwen3-ASR model 支援 prompt injection（透過 chat template）
- `mlx_qwen3_asr` 的 `tokenizer.build_prompt_tokens()` 可以客製 prompt
- 可傳入 glossary / domain terms 提升準確率
- **CFA 場景尤其重要**：NPV, IRR, duration, convexity 等專有名詞

**4. Speaker Diarization**
- Library 已整合，`diarize=True` 一鍵啟用
- 產出多 speaker 字幕 → 講師 vs 學生問答區分

### 🛠️ 中等效益

**5. Speculative Decoding**
- 用 draft model 加速生成
- 需要下載 draft model（可用同一個 0.6B 或更小的）
- 對長音頻加速有感

**6. 文稿匹配 (Transcript-to-Text Matching)**
- 比對 ASR 結果與已知參考文稿（slides 文字、講義）
- 可修正 ASR 錯誤，提升專有名詞準確率
- **對 CFA 教學影片場景極有價值**（多數影片有 slides/text）

**7. 智能拆行演算法**
- 目前 `_group_words_into_subtitles()` 按 max_duration/max_chars 分段
- 可改進：語義邊界（句號、逗號）、語速感知、斷句規則

### 📋 可行但低優先

- 字幕編輯器 GUI（subtitle-forge 定位是 batch pipeline tool）
- 即時語音辨識（偏離核心用途）
- 達芬奇/PR 插件（外部工具生態）
- OpenVINO/GUI 跨平台（MLX 已是 Apple 最佳方案）

---

## 6. Available but Unused Library Features — Quick Reference

| Feature | Import | Status |
|---------|--------|--------|
| `ForcedAligner` | `from mlx_qwen3_asr import ForcedAligner` | Model cached ✅ |
| Speaker Diarization | `transcribe(..., diarize=True)` | Library built-in |
| Speculative Decoding | `transcribe(..., draft_model=...)` | Library built-in |
| Batch Transcription | `transcribe_batch([...])` | Library built-in |
| Async Transcription | `transcribe_async(...)` | Library built-in |
| Return Chunks | `transcribe(..., return_chunks=True)` | Library built-in |
| Progress Callback | `transcribe(..., on_progress=fn)` | Library built-in |

---

## 7. User Experience / Desktop Mode (New Direction)

根據使用者回饋，希望從 **User Friendly** 層面推進，參考 haoone 的 desktop mode + cli mode 以及 QwenASRMiniTool 的桌面 GUI。

### 對標 UX 功能差距

| 功能 | haoone | QwenASRMiniTool | subtitle-forge | 優先級 |
|------|--------|----------------|----------------|--------|
| 桌面應用 (Desktop App) | ✅ 專業級 | ✅ CustomTkinter | ❌ (只有 Flask web) | **HIGH** |
| Drag & Drop 輸入 | ✅ | ✅ | ❌ (需手動放 input/) | **HIGH** |
| CLI 工具 | ✅ `haoone-cli` | ❌ (只有 GUI) | ✅ `main.py` | - |
| 即時進度可視化 | ✅ 桌面進度條 | ✅ GUI progress | ✅ Rich TUI | - |
| 一鍵安裝/免配置 | ✅ 買斷制安裝 | ✅ Portable EXE | ❌ (需 python venv) | **HIGH** |
| 檔案管理/佇列 | ✅ 內建 | ✅ Batch queue tab | ✅ (input/output dir) | MEDIUM |
| 字幕編輯器 | ✅ 內建 | ✅ 內建 playback | ❌ | LOW |
| 桌面通知 | ✅ 推測 | ❌ | ❌ | MEDIUM |
| 插件生態 (達芬奇/PR) | ✅ | ❌ | ❌ | OUT OF SCOPE |

### 可行的 UX 改善方案

#### 方案 A: Rich Desktop GUI (CustomTkinter / PyQt6)
- 類似 QwenASRMiniTool 的 CustomTkinter 桌面應用
- Drag-and-drop 影片/音檔
- 批次佇列管理 + 即時進度
- 內建字幕預覽/編輯
- 設定面板 (model、語言、並發數)
- 桌面通知 (完成/錯誤)
- **優點**：用戶體驗最佳，非技術人員也能用
- **缺點**：開發量大，需維護兩種 UI

#### 方案 B: 強化 Web Dashboard (取代 Flask 簡陋版)
- 升級 `server.py` 為完整 SPA 後端
- 現代化 UI (React/Vue 或 HTMX + 模板)
- Drag-and-drop 上傳 → 自動觸發 Pipeline
- 即時 WebSocket 進度推送
- 輸出預覽 (字幕、影片)
- 歷史任務管理
- **優點**：跨平台、本地訪問、可結合 CLI
- **缺點**：無桌面原生整合

#### 方案 C: CLI 體驗強化
- **Interactive mode**：引導式操作 (選擇檔案、參數)
- **Better --help**：分組參數、範例
- **Shell completion**：zsh/bash 自動補全
- **Output browsing**：`ls output/` 的結構化顯示
- **Watch mode 強化**：目前已有 watchdog，可加桌面通知
- **優點**：開發量最小，改善日常使用
- **缺點**：仍有 terminal 門檻

### 方案比較

| 維度 | A: Desktop GUI | B: Web SPA | C: CLI 強化 |
|------|---------------|-----------|------------|
| 開發量 | 🔴 大 (數週) | 🟡 中 (1-2 週) | 🟢 小 (2-3 天) |
| UX 提升 | 🔥 最大 | 👍 佳 | 👍 不錯 |
| 非技術用戶 | ✅ 可用 | ✅ 可用 | ❌ 需 terminal |
| 跨平台 | 🟡 需適配 | ✅ 瀏覽器即可 | ✅ terminal |
| 與現有整合 | 🔴 全新 UI | 🟡 可重用 logic | 🟢 直接強化 |

### 建議優先順序

```
Phase UX-1 (Quick wins, 2-3 天)
├── 升級 CLI: interactive mode + shell completion + 桌面通知
├── 升級 Web Dashboard: HTMX/輕量 SPA + drag-drop upload + WebSocket 進度
└── input/ 的 drag-and-drop 支援 (簡單 watchdog 強化)

Phase UX-2 (Desktop App, 1-2 週)
├── Streamlit 前端 (快速原型，與 QwenASRMiniTool 做法類似)
├── 或 CustomTkinter 桌面應用
├── 或 Tauri + React 原生桌面 (更現代)
└── 一鍵安裝腳本 (brew / curl 安裝)

Phase UX-3 (Polish)
├── 桌面通知 (完成/錯誤)
├── 設定面板 UI
├── 輸出預覽
└── 插件生態 (可選)
```

---

## 8. 綜合建議下一步

```diff
 Phase A: Low-hanging fruit (ASR 引擎強化)
 ├── A1: 啟用 ForcedAligner → word-level timestamps
 ├── A2: VAD 取代 ffmpeg silence check
 ├── A3: Speaker Diarization (diarize=True)
 └── A4: ASR model / aligner model 路徑移至 settings.yaml

 Phase B: Accuracy boost
 ├── B1: 熱詞注入 (prompt injection via glossary)
 ├── B2: 文稿匹配 (slides/reference text alignment)
 └── B3: 智能拆行演算法

 Phase C: Performance
 ├── C1: Speculative decoding
 ├── C2: Async/batch parallelism
 └── C3: 長音頻 chunking 優化

+Phase UX: User Experience (新方向)
+├── UX-1: CLI 強化 + Web Dashboard 升級 + input drag-drop
+├── UX-2: Desktop GUI (Streamlit / CustomTkinter / Tauri)
+└── UX-3: 通知 + 設定面板 + 輸出預覽
```
