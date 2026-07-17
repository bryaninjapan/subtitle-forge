# TODO — Subtitle Forge

> Gaps identified during Milestone 3 (UX-2) dependency analysis.
> Added: 2026-07-17

## 🔴 HIGH (UX-2 前置條件)

- [ ] **G1: Phase A4 — ASR model 路徑移至 settings.yaml**
  - 現在 `QWEN3_ASR_MODEL` 硬編碼在 `asr_engine.py:19`
  - UX-2 設定面板需要讀寫這個值才能生效
  - 建議納入 UX-2 Task 0 或 T2 Python API 一起做

## 🟡 MEDIUM (UX-2 需納入規劃)

- [ ] **G2: Model 下載 UX**
  - 1.8GB~4.4GB 的 ASR model 第一次使用時需下載
  - 需要: server.py 新 API (`GET /models/status`, `POST /models/download`)
  - 前端顯示下載進度 + 完整性檢查 (參考 QwenASRMiniTool downloader.py)

- [ ] **G3: 前端測試策略**
  - Component 測試 (Vitest + Testing Library)
  - Integration 測試 (MSW mock server)
  - 避免 UI 改動全靠手動測

- [ ] **G4: 首次執行體驗 (Onboarding)**
  - Tauri sidecar 自動 spawn `python3 server.py`
  - 啟動狀態檢查 UI (server 是否在跑)
  - Model 下載引導 (第一次開時)
  - 歡迎畫面或 tooltip 引導

- [ ] **G5: Error / Loading / Empty State 覆蓋**
  - server.py 斷線 → 「連線中…」+ 重試按鈕
  - pipeline 失敗 → task row 顯示錯誤訊息 + 重試
  - 無歷史任務 → 「尚無任務」插圖
  - 上傳失敗 → toast 通知 + 原因

## 🟢 LOW (之後再補)

- [ ] **G6: 版本更新機制**
  - Tauri auto-updater 基於 GitHub Releases
  - UX-2 穩定後再實作

- [ ] **G7: Cross-platform (Windows/Linux)**
  - MLX 是 Apple Silicon only
  - Windows 需 OpenVINO 或 Vulkan backend (參考 QwenASRMiniTool)
  - 先鎖定 macOS only
