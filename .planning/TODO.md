# TODO — Subtitle Forge

> Added: 2026-07-17
> Updated: 2026-07-17 (G1 done, G7 refined)

## 🔴 HIGH (UX-2 前置條件)

- [x] **G1: Phase A4 — ASR model 路徑移至 settings.yaml** ✅ Done

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

- [ ] **G8: Windows ASR Backend**
  - MLX 是 Apple Silicon only → Windows 無法用 Local ASR
  - 需要: faster-whisper (CUDA/CPU) 或 QwenASRMiniTool 的 OpenVINO INT8 backend
  - Scope: 新增一個 Windows 專用的 ASR backend class
  - 優先度: LOW（目前 Windows 用戶可走 API ASR）
