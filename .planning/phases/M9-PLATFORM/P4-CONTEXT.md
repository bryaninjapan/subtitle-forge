# Phase 4: Version Update (Tauri Auto-Updater) — Decisions

**Date:** 2026-07-17

## Decisions

| Area | Decision |
|------|----------|
| Update trigger | Manual (Settings page [檢查更新] button) |
| Update source | GitHub Releases (`update.json`) |
| Code signing | Skipped (for now) |
| Frontend | Dynamic `import()` for browser safety |
| Rust | `tauri-plugin-updater` registered in lib.rs |
