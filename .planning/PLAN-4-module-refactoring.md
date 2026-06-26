# PLAN — Phase 4: Module Refactoring

Milestone: 模組重構（srt_utils / media_utils / recover）

## Goal
改善 module 邊界，消除多功能瑞士刀和命名誤導，提高可測試性。

## Done Criteria
- `srt_utils.py` 拆分出 `srt_bilingual.py` 和 `srt_translation.py`
- `media_utils.py` 搬出 `check_audio_quality` 和 `burn_subtitles`
- 所有 test 仍通過
- 無行為變更

## Tasks

| # | Task | Est. | 難度 |
|---|------|------|------|
| 1 | `media_utils.py`: 搬出 `check_audio_quality` → `audio_quality.py` | 10 min | 🔹 |
| 2 | `media_utils.py`: 搬出 `burn_subtitles` → `srt_burn.py` | 10 min | 🔹 |
| 3 | `srt_utils.py`: 拆出 bilingual → `srt_bilingual.py` | 20 min | 🔸 |
| 4 | `srt_utils.py`: 拆出 translation parse → `srt_translation.py` | 15 min | 🔸 |
| 5 | `srt_utils.py`: 縮減（from 342 → ~200 行） | 10 min | 🔹 |
| 6 | 重跑全部 25 tests + import check | 5 min | 🔹 |

總計預計：**~70 min**

---

### Task 1 — `media_utils.py`: 搬出 `check_audio_quality`

- 新檔案：`audio_quality.py`
- 搬入：`check_audio_quality()` function + 相關 import
- `media_utils.py` 不再 import Gemini client
- 範例用法不變：`from audio_quality import check_audio_quality`

### Task 2 — `media_utils.py`: 搬出 `burn_subtitles`

- 新檔案：`srt_burn.py`
- 搬入：`burn_subtitles()` function
- `media_utils.py` 只剩：`get_media_duration_sec`, `get_file_hash`

### Task 3 — `srt_utils.py`: 拆出 bilingual

- 新檔案：`srt_bilingual.py`
- 搬入：`create_bilingual_srt()`, `create_bilingual_srt_from_text()`
- `srt_utils.py` import 此 module 或 caller 直接 import

### Task 4 — `srt_utils.py`: 拆出 translation parse

- 新檔案：`srt_translation.py`
- 搬入：`parse_translation_response()`, `format_batch_for_translation()`
- 這兩個是 translator.py 專用的，不該在 srt_utils

### Task 5 — `srt_utils.py` 縮減

- Task 3+4 完成後，`srt_utils.py` 只剩：
  - `parse_srt`, `write_srt`, `batch_entries`
  - `_srt_time_to_seconds`, `clean_subtitle_text`
  - `split_monolithic_entry`, `validate_srt_completeness`
  - `merge_bilingual`（如果需要保持向後相容）

### Task 6 — 驗證

- `python3 -m pytest -v` (25 tests green)
- `python3 -c "from srt_bilingual import create_bilingual_srt"`
- `python3 -c "from audio_quality import check_audio_quality"`
- `python3 -c "from srt_burn import burn_subtitles"`

### Rollback
如果測試失敗：`git checkout -- .`

### Not in Scope
- `recover.py` 重構（留到 Phase 5）
- 新增測試（但有搬動的話 import test 就是安全網）
- 任何行為變更
