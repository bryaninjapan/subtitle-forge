#!/bin/bash

# Subtitle Forge - ET LM1-4 Regeneration Batch (v5)
source venv/bin/activate
export GEMINI_API_KEY=$(grep "export GEMINI_API_KEY=" ~/.zshrc | cut -d'"' -f2)

echo "Starting ET LM1-4 Quality Regeneration..."

python main.py --input \
  "input/2026 L1 ET LM1 EOCQ_540p.mp4" \
  "input/2026 L1 ET LM1 Video_540p.mp4" \
  "input/2026 L1 ET LM2 EOCQ_540p.mp4" \
  "input/2026 L1 ET LM2 Video_540p.mp4" \
  "input/2026 L1 ET LM3 EOCQ1_540P.mp4" \
  "input/2026 L1 ET LM3 EOCQ2_540p.mp4" \
  "input/2026 L1 ET LM3 Review_540p.mp4" \
  "input/2026 L1 ET LM3 Update_540p.mp4" \
  "input/2026 L1 ET LM3 Video1_540p.mp4" \
  "input/2026 L1 ET LM3 Video2_540p.mp4" \
  "input/2026 L1 ET LM3 Video3_540p.mp4" \
  "input/2026 L1 ET LM4 EOCQ_540p.mp4" \
  "input/2026 L1 ET LM4 Video_540p.mp4"

echo -e "\nET Regeneration Batch Complete! Check pipeline_report.md for details."
