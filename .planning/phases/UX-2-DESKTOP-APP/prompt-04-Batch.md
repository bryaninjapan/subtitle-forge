Create src/pages/Batch.tsx — batch processing page for a subtitle processing app.

### Setup
- Import { useState, useEffect } from 'react'
- Import { api } from '../api'
- Import type { TaskProgress } from '../types'

### State
- files: File[] (selected files)
- tasks: Record<string, { file: string; progress: TaskProgress | null }> (tracked by task_id)
- diarize: boolean (false)
- numSpeakers: string ('auto')

### Layout

Title:
```
批次辨識
```

Control bar:
```
[＋ 加入檔案]  [▶ 全部開始]    說話者分離: [○]    人數: [自動 ▼]    0 / 3 完成
```

Task list (one row per file):
```
夏天這一站.mp3      ████████████░░░░  60%  轉換中  [⋮]
月宮・換裝夢遊.mp3   ░░░░░░░░░░░░░░   0%  待處理  [⋮]
華裳夢遊.mp3        ░░░░░░░░░░░░░░   0%  待處理  [⋮]
```

### Behavior
- Add files button → multiple file selection (input accept="audio/*,video/*")
- Each file appears in the task list with status "待處理"
- Click "全部開始" → for each file, call api.runPipeline(file, { translate: false, notes: false })
  - Store task_id from response
  - Start polling api.getProgress() every 2 seconds for all task_ids
- Progress bar visual:
  - Background: var(--bg-hover)
  - Filled: var(--accent) while processing, var(--success) when done
  - Width: (pct / 100) * available width
- Status labels (colored badges):
  - 待處理 (queued/pending): var(--text-muted)
  - 轉換中 (processing): var(--accent)
  - 完成 (done): var(--success)
  - 失敗 (error): var(--error)
- Counter at top: completedCount / totalCount
- Three-dot menu per task: "取消" option calls api.cancelTask(taskId)
- When all tasks done, "全部開始" button shows "全部清除" to clear the list
- Handle empty state: show "尚無任務" with illustration

### Styling
- Use CSS variables: var(--bg-card), var(--bg-primary), var(--accent), var(--text-primary), var(--text-secondary), var(--text-muted), var(--border), var(--radius), var(--bg-hover), var(--success), var(--error)
- Dark theme throughout
- Cards have background var(--bg-card), border-radius var(--radius), padding 20px
- Buttons: padding 8px 16px, border-radius var(--radius), border none, cursor pointer
- Primary button (添加、全部開始): accent background
- Task row: display flex, gap 16px, items center, background var(--bg-card), border-radius var(--radius), padding 12px 16px
- Progress bar container: height 8px, background var(--bg-hover), border-radius 4px, flex 1
- Progress bar fill: height 100%, border-radius 4px, transition width 0.5s
- Status badge: padding 4px 10px, border-radius 12px, font-size 12px, font-weight 500
- Three-dot menu: transparent button, cursor pointer

Return the COMPLETE file content only.
