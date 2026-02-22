# Subtitle Forge

100% 本地視頻字幕生成與翻譯工具。適用於 Apple Silicon Mac。

## 功能

- **語音辨識 (ASR)**：使用 Qwen3-ASR-1.7B 透過 MLX 生成原文字幕 (SRT)
- **字幕翻譯**：使用 Qwen3-8B-4bit 透過 MLX 翻譯為繁體中文字幕
- **批量處理**：支援整個資料夾的影片批量轉換
- **多語言**：支援英語、日語等 52 種語言自動偵測或手動指定

## 系統需求

- Apple Silicon Mac (M1/M2/M3/M4)
- macOS
- Python 3.10+
- ffmpeg
- 16 GB RAM (建議)
- 首次使用需下載模型 (~8 GB)

## 安裝

```bash
# ffmpeg (如未安裝)
brew install ffmpeg

# 啟動虛擬環境
source venv/bin/activate

# 依賴已安裝；若需重裝：
pip install -r requirements.txt
```

## 使用方式

### 基本用法

```bash
# 啟動虛擬環境
cd subtitle-forge
source venv/bin/activate

# 把影片放入 input/ 資料夾，然後執行：
python main.py

# 結果在 output/{影片名稱}/ 下：
#   {影片名稱}.srt     → 原文字幕
#   {影片名稱}.zh.srt  → 中文字幕
```

### 進階用法

```bash
# 處理單一影片
python main.py --input video.mp4

# 處理指定資料夾
python main.py --input /path/to/videos/

# 指定來源語言（預設自動偵測）
python main.py --language Japanese
python main.py --language English

# 只做語音辨識，不翻譯
python main.py --asr-only

# 只做翻譯（已有原文 SRT 時）
python main.py --translate-only
```

### 支援格式

影片：mp4, mkv, avi, mov, webm, flv, m4v, ts
音頻：wav, mp3, flac, m4a, ogg, aac

## 專案結構

```
subtitle-forge/
├── main.py          # CLI 入口
├── config.py        # 配置（模型、語言、批量大小）
├── asr_engine.py    # ASR 模組
├── translator.py    # 翻譯模組
├── srt_utils.py     # SRT 工具
├── input/           # 放入待處理影片
└── output/          # 輸出結果
```

## 效能預估 (Mac Mini M4, 16GB)

| 影片長度 | ASR 耗時 | 翻譯耗時 | 總計    |
|---------|---------|---------|--------|
| 30 分鐘  | ~8 分鐘  | ~10 分鐘 | ~20 分鐘 |
| 1 小時   | ~16 分鐘 | ~20 分鐘 | ~40 分鐘 |
| 4 小時   | ~65 分鐘 | ~60 分鐘 | ~2 小時  |

## 技術棧

- **ASR**: [mlx-qwen3-asr](https://github.com/moona3k/mlx-qwen3-asr) + Qwen3-ASR-1.7B
- **翻譯**: [mlx-lm](https://github.com/ml-explore/mlx-examples) + Qwen3-8B-4bit
- **音頻處理**: ffmpeg
- **框架**: Apple MLX (Metal GPU 加速)
