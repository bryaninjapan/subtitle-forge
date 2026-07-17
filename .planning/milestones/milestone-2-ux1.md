# Milestone Archive: User Experience Enhancement (UX-1)

**Completed:** 2026-07-17
**Branch:** `feature/local-asr-qwen3` (not merged to main)

## Goal

Make subtitle-forge more **user-friendly** by strengthening CLI, Web Dashboard, and adding desktop notifications.

## Phases Completed

| Phase | Status | Description |
|-------|--------|-------------|
| ASR model switch | ✅ | Qwen3-ASR 1.7B → 0.6B (RAM 省 2GB+) |
| UX-1 | ✅ | CLI 強化 + Web Dashboard 升級 + Input Drag-Drop |

## UX-1 Deliverables

### CLI 強化
| Feature | Flags/Commands | Description |
|---------|---------------|-------------|
| Interactive mode | `--interactive`, `-i` | 引導式檔案選擇 + 語言/風格/章節設定 |
| Shell completion | `--completion zsh` / `bash` | zsh/bash 自動補全（flags, language, style, files） |
| Desktop notification | (auto) | pipeline 完成後 macOS 通知（osascript / terminal-notifier） |
| Suppress notify | `--no-notify` | 抑制桌面通知 |

### Web Dashboard
| Feature | Route | Description |
|---------|-------|-------------|
| Drop-zone upload | `POST /upload` | HTML5 drag-and-drop，檔案儲存至 `input/` |
| Real-time progress | `GET /progress` + HTMX polling (2s) | 進度條、階段訊息、百分比 |
| Task history | `GET /history` | 從 `usage_log.jsonl` 讀取 |
| Output browser | `GET /outputs` | 列出已處理影片與輸出檔案 |
| 4GB upload limit | (config) | `MAX_CONTENT_LENGTH` 保護 |

### Code Quality
| Item | Detail |
|------|--------|
| `build_parser()` extracted | 從 `main()` 抽出，可供測試 |
| `generate_completion()` | zsh/bash 補全腳本產生器 |
| `send_notification()` | 雙 fallback (terminal-notifier → osascript) |
| `server.py` rewrite | 398 行單檔、暗色主題、HTMX 驅動 |
| 48 tests (25 → 48) | +23 個新測試（CLI parser + completion + notification + server routes） |
| Code review | 0 HIGH, 2 MEDIUM fixed |

## Testing Status

- Before: 25 tests
- After: **48 tests** (srt + director + state_store + cli_server)
- Coverage: CLI flags, completion output, notification, server routes, upload validation

## Files Changed

| File | Change |
|------|--------|
| `asr_engine.py` | Qwen3-ASR 1.7B → 0.6B |
| `main.py` | +`build_parser`, +`interactive_mode`, +`generate_completion`, +`send_notification`, 5 new flags |
| `server.py` | Complete rewrite (83 → 398 lines) |
| `tests/test_cli_server.py` | New file, 23 tests |
| `.planning/phases/DISCOVERY-ASR-OPTIMIZATION.md` | Discovery: haoone + QwenASRMiniTool 對標分析 |
| `.planning/phases/UX-1-WEB-CLI-ENHANCEMENT/PLAN.md` | UX-1 執行計畫 (6 tasks) |
| `STATE.md` | 更新完成狀態 |

## Key Decisions

- **Keep feature branch separate**: `feature/local-asr-qwen3` not merged to `main` (user preference)
- **HTMX over SSE/WebSocket**: 更簡單、零依賴（CDN only），3 個 partial endpoints
- **osascript over terminal-notifier**: macOS 內建，無需安裝額外套件
- **Single-file server.py**: 維持 Flask template_string 模式，便於快速迭代

## Learnings

1. **Characterization tests first** — 抽出 `build_parser()` 後馬上寫測試，確保後續改動不破壞既有 flags
2. **HTMX polling 適合 local dashboard** — 2s interval 零負擔，不需 WebSocket 複雜度
3. **Dependency graph for parallel work** — Task 1/2/4 可並行，但 max concurrent 3 需調度
4. **osascript 比 terminal-notifier 更 portable** — 內建、無需安裝、跨 macOS 版本
