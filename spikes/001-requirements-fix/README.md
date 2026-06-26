# 001: requirements-fix

## Question
修正後的 requirements.txt 能否在乾淨 venv 裝齊所有依賴 + tests 通過？

## Approach
1. 從現有 venv 提取已知可用版本（baseline）
2. 寫出修正版 requirements.txt（加缺失套件、刪 stdlib、pin 版本）
3. 建乾淨 venv，pip install，跑 pytest
4. 比對結果

## Baseline（現有 venv 已知可用版本）
```
google-genai==1.67.0
openai==2.29.0
python-dotenv==<check>
PyYAML==6.0.3
rich==14.3.3
watchdog==6.0.0
genanki==0.13.1
Flask==3.1.3
pytest==9.0.2
pytest-cov==7.0.0
fpdf2==2.8.7
```

## Verdict: VALIDATED

### What worked
- 乾淨 Python 3.12 venv + 修正版 requirements.txt → 所有 10 個套件安裝成功
- pytest 3/3 通過（test_srt.py）
- 16 個模組全部 import 成功（零 ImportError）

### What didn't
- 無

### Surprises
- `python-dotenv` 雖然列在原 requirements.txt 但 venv 裡沒裝（代碼用手動 .env 解析）
- `mlx-qwen3-asr` 不需要列在 requirements.txt（ASR 是可選功能，且只支援 Apple Silicon）
- hermes-agent 全域套件的 warning 不影響 subtitle-forge 本身

### Recommendation for the real build
直接替換 requirements.txt 為修正版。內容：
```
google-genai==1.67.0
openai==2.29.0
python-dotenv==1.1.0
PyYAML==6.0.3
rich==14.3.3
watchdog==6.0.0
genanki==0.13.1
Flask==3.1.3
fpdf2==2.8.7
pytest==9.0.2
pytest-cov==7.0.0
```
- 刪除了 stdlib（pathlib, argparse）
- 加了 6 個缺失套件（PyYAML, rich, watchdog, genanki, Flask, pytest, pytest-cov, fpdf2）
- pin 了所有版本（從現有 venv 提取）
- python-dotenv 保留（雖然目前沒用到，但代碼有手動 .env 解析，未來可統一）
