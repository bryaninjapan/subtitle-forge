"""ASR engine using local Qwen3-ASR-0.6B (via mlx-qwen3-asr) for transcription."""

from __future__ import annotations

import sys
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from media_utils import get_media_duration_sec  # type: ignore

from config import (
    ASR_ALIGNER_MODEL,
    ASR_API_MODEL,
    ASR_BACKEND,
    ASR_DIARIZE,
    ASR_DIARIZE_NUM_SPEAKERS,
    ASR_HOTWORDS,
    ASR_MAX_CONCURRENT,
    ASR_MODEL,
    ASR_USE_DRAFT,
    CC_CONVERSION,
    VAD_THRESHOLD,
    AUDIO_SAMPLE_RATE,
    FFMPEG_BIN,
    OUTPUT_DIR,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
)  # type: ignore

# ─────────────────────────── Shared utilities ────────────────────────────────

_last_progress = 0.0


def _default_progress_cb(info: dict) -> None:
    """Default progress callback: prints ASR progress percentage to console.

    Callback signature matches mlx_qwen3_asr transcribe(on_progress=...).
    info dict may contain: 'progress' (0-100), 'chunk', 'total_chunks', etc.
    """
    global _last_progress
    pct = info.get("progress", 0)
    if abs(pct - _last_progress) >= 5 or pct >= 100:
        _last_progress = pct
        print(f"\r  ASR progress: {pct:.0f}%", end="", flush=True)
        if pct >= 100:
            print()


def is_media_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

def check_dependencies() -> None:
    """Ensure ffmpeg and ffprobe are installed and available."""
    from config import FFMPEG_BIN  # type: ignore
    for tool in [FFMPEG_BIN, "ffprobe"]:
        try:
            subprocess.run([tool, "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"\n[CRITICAL ERROR] '{tool}' not found!")
            print(f"Subtitle Forge requires {tool} to process video and audio.")
            print("Please install ffmpeg (e.g., 'brew install ffmpeg' on macOS).")
            sys.exit(1)
    print("  [Init] Dependencies check passed: ffmpeg/ffprobe found.")

def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extract full audio from video to 16kHz mono WAV."""
    audio_path = output_dir / f"{video_path.stem}.wav"
    if audio_path.exists():
        dur = get_media_duration_sec(audio_path)
        if dur > 0:
            print(f"  [skip] Audio already extracted: {audio_path.name} ({dur / 60:.1f} min)")
        return audio_path

    cmd = [
        FFMPEG_BIN, "-i", str(video_path),
        "-vn",
        "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample={AUDIO_SAMPLE_RATE}",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-y",
        str(audio_path),
    ]
    print(f"  Extracting & Denoising audio: {video_path.name} -> {audio_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        cmd_fallback = [
            FFMPEG_BIN, "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le",
            "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "1", "-y", str(audio_path),
        ]
        result = subprocess.run(cmd_fallback, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
    
    if audio_path.stat().st_size < 1000:
        raise RuntimeError(f"Extracted audio is too small. Ffmpeg might have failed.")
    return audio_path

def check_silence(audio_path: Path, threshold_db: int = -40) -> bool:
    """Check if the audio file is mostly silent using Silero VAD.

    Returns True if >95% of the audio is silence (no speech detected).
    Much more accurate than ffmpeg silencedetect.
    """
    try:
        import torch
        import torchaudio
        import silero_vad

        # Load VAD model (cached on subsequent calls)
        vad_model = silero_vad.load_silero_vad()

        # Read audio
        wav, sr = torchaudio.load(str(audio_path))
        # Convert to mono if needed
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        # Resample to 16kHz if needed (silero expects 16kHz)
        if sr != 16000:
            resampler = torchaudio.transforms.Resample(sr, 16000)
            wav = resampler(wav)
            sr = 16000

        # Get speech timestamps
        speech_seconds = 0.0
        total_seconds = wav.shape[1] / sr
        if total_seconds <= 0:
            return True

        # Process in chunks (silero_vad.get_speech_timestamps expects specific format)
        from silero_vad import get_speech_timestamps
        speech = get_speech_timestamps(
            wav[0].numpy() if hasattr(wav, 'numpy') else wav[0],
            vad_model,
            sampling_rate=sr,
            threshold=VAD_THRESHOLD,
            min_speech_duration_ms=250,
            min_silence_duration_ms=100,
        )

        if speech:
            speech_seconds = sum((s["end"] - s["start"]) for s in speech) / 1000.0

        silence_ratio = 1.0 - (speech_seconds / total_seconds)
        return silence_ratio > 0.95
    except ImportError:
        # Fallback to ffmpeg if silero-vad not installed
        return _fallback_silence_check(audio_path, threshold_db)
    except Exception:
        # On any error, err on the side of processing (return False)
        return False


def _fallback_silence_check(audio_path: Path, threshold_db: int = -40) -> bool:
    """Fallback: use ffmpeg silencedetect when silero-vad is unavailable."""
    from config import FFMPEG_BIN  # type: ignore
    duration = get_media_duration_sec(audio_path)
    if duration <= 0:
        return True
    cmd = [FFMPEG_BIN, "-i", str(audio_path), "-af", f"silencedetect=n={threshold_db}dB:d=2", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    import re
    silence_durations = re.findall(r"silence_duration: ([\d\.]+)", result.stderr)
    total_silence = sum(float(d) for d in silence_durations)
    return (total_silence / duration) > 0.95

# ─────────────────────────── Qwen3-ASR ──────────────────────────────────────

def _seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _group_words_into_subtitles(
    segments: list[dict],
    max_duration: float = 5.0,
    max_chars: int = 80,
) -> list[dict]:
    """Merge word-level segments into subtitle blocks with smart line splitting.

    - Prefers sentence boundaries (。！？.!?） for breaks
    - Adjusts max_chars based on speaking rate (fast speech = shorter lines)
    - Keeps short phrases together (won't split 2-3 word sentences)
    """
    if not segments:
        return []

    # Calculate speaking rate (words per second) to adjust block sizing
    total_duration = segments[-1]["end"] - segments[0]["start"]
    total_words = sum(1 for s in segments if s["text"].strip())
    wps = total_words / total_duration if total_duration > 0 else 2.0

    # Adjust max_chars based on speaking rate
    # Baseline: 2.5 wps → max_chars=80. Faster → smaller blocks for readability.
    if wps > 3.5:
        adjusted_max = int(max_chars * 0.7)  # fast speech: shorter lines
    elif wps < 1.5:
        adjusted_max = int(max_chars * 1.2)  # slow speech: can fit more
    else:
        adjusted_max = max_chars
    adjusted_max = max(30, min(120, adjusted_max))

    blocks: list[dict] = []
    buf_words: list[str] = []
    buf_start: float = 0.0
    buf_end: float = 0.0
    min_phrase_words = 3  # Don't break very short phrases

    for seg in segments:
        word = seg["text"].strip()
        if not word:
            continue

        is_first = not buf_words
        projected = (" ".join(buf_words + [word])).strip()
        duration = seg["end"] - buf_start
        is_sentence_end = word.endswith((".", "?", "!", "...", "。", "？", "！", ")", "）"))
        is_comma_break = word.endswith((",", "，", ";", "；")) and len(projected) > adjusted_max * 0.6

        if is_first:
            buf_start = seg["start"]
            buf_words.append(word)
            buf_end = seg["end"]
            continue

        # Decision: should we break here?
        force_break = duration > max_duration or len(projected) > adjusted_max
        prefer_break = is_sentence_end or is_comma_break

        if prefer_break and len(buf_words) >= min_phrase_words:
            blocks.append({"text": " ".join(buf_words), "start": buf_start, "end": seg["start"]})
            buf_words = [word]
            buf_start = seg["start"]
            buf_end = seg["end"]
        elif force_break and len(buf_words) >= min_phrase_words:
            # Hard break — best effort at a natural point
            # Check if we can break at the previous word boundary
            blocks.append({"text": " ".join(buf_words), "start": buf_start, "end": buf_end})
            buf_words = [word]
            buf_start = seg["start"]
            buf_end = seg["end"]
        else:
            buf_words.append(word)
            buf_end = seg["end"]

    if buf_words:
        blocks.append({"text": " ".join(buf_words), "start": buf_start, "end": buf_end})

    return blocks


def _transcribe_chunked(
    audio_path: Path,
    language: Optional[str] = None,
    diarize: bool = False,
    num_speakers: Optional[int] = None,
    use_aligner: bool = True,
    use_draft: bool = False,
    chunk_duration: int = 600,
    overlap: int = 3,
    on_progress: Optional[callable] = None,
) -> str:
    """Transcribe long audio in chunks, then merge results with offset correction."""
    from config import FFMPEG_BIN, OUTPUT_DIR  # type: ignore

    total_sec = get_media_duration_sec(audio_path)
    n_chunks = max(1, int(total_sec // chunk_duration) + 1)
    print(f"  Long audio detected ({total_sec/60:.1f} min) — splitting into {n_chunks} chunks")

    all_entries: list = []
    chunk_dir = OUTPUT_DIR / f"{audio_path.stem}_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    for i in range(n_chunks):
        start = max(0, i * chunk_duration - (overlap if i > 0 else 0))
        end = min(total_sec, (i + 1) * chunk_duration + (overlap if i < n_chunks - 1 else 0))
        chunk_path = chunk_dir / f"chunk_{i:03d}.wav"

        # Extract chunk with ffmpeg
        cmd = [
            FFMPEG_BIN, "-y", "-i", str(audio_path),
            "-ss", str(start),
            "-t", str(end - start),
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(chunk_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        # Transcribe chunk
        print(f"  Chunk {i+1}/{n_chunks} ({start:.0f}s–{end:.0f}s)")
        chunk_srt = _transcribe_with_qwen3_asr(
            chunk_path, language, diarize=False,  # disable diarize per-chunk
            num_speakers=num_speakers, use_aligner=use_aligner, use_draft=use_draft,
            on_progress=on_progress,
        )

        # Parse, shift timestamps, collect
        from srt_utils import parse_srt  # type: ignore
        entries = parse_srt(chunk_srt)
        offset = start
        for e in entries:
            shifted = _shift_srt_entry(e, offset)
            all_entries.append(shifted)

        # Cleanup chunk
        try:
            chunk_path.unlink()
        except OSError:
            pass

    # Cleanup chunk dir
    try:
        chunk_dir.rmdir()
    except OSError:
        pass

    # Sort by start time and deduplicate overlapping segments
    all_entries.sort(key=lambda e: e.start)
    merged = _dedup_overlapping_entries(all_entries, overlap_sec=overlap)

    from srt_utils import write_srt  # type: ignore
    return "\n\n".join(
        f"{i}\n{e.start} --> {e.end}\n{e.text}"
        for i, e in enumerate(merged, 1)
    ) + "\n"


def _shift_srt_entry(entry, offset_sec: float):
    """Shift an SRT entry's timestamps forward by offset_sec."""
    import copy
    e = copy.deepcopy(entry)
    e.start = _shift_ts(e.start, offset_sec)
    e.end = _shift_ts(e.end, offset_sec)
    return e


def _shift_ts(ts: str, offset: float) -> str:
    """Add offset seconds to an SRT timestamp string."""
    h, m, s = ts.replace(",", ".").split(":")
    total = int(h) * 3600 + int(m) * 60 + float(s) + offset
    return f"{int(total//3600):02d}:{int((total%3600)//60):02d}:{total%60:06.3f}".replace(".", ",")


def _dedup_overlapping_entries(entries: list, overlap_sec: int = 3) -> list:
    """Remove near-duplicate entries from chunk overlap regions."""
    if not entries:
        return entries

    deduped = [entries[0]]
    for e in entries[1:]:
        prev = deduped[-1]
        # If same text and times overlap, skip duplicate
        gap = _ts_to_sec(e.start) - _ts_to_sec(prev.end)
        if gap < overlap_sec and e.text.strip() == prev.text.strip():
            continue
        # If this entry is contained within the previous one, skip
        if _ts_to_sec(e.end) <= _ts_to_sec(prev.end) and gap < 0:
            continue
        deduped.append(e)

    return deduped


def _ts_to_sec(ts: str) -> float:
    """Convert SRT timestamp to seconds."""
    h, m, s = ts.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _transcribe_with_qwen3_asr(
    audio_path: Path,
    language: Optional[str] = None,
    diarize: bool = False,
    num_speakers: Optional[int] = None,
    use_aligner: bool = True,
    use_draft: bool = False,
    reference_text: Optional[str] = None,
    on_progress: Optional[callable] = None,
) -> str:
    """Transcribe audio locally with Qwen3-ASR-0.6B. Returns SRT-formatted text.

    When use_aligner=True, uses ForcedAligner for word-level timestamps.
    When use_draft=True, uses speculative decoding for faster inference on long audio.
    When reference_text is provided, uses it for ForcedAligner alignment (script matching).
    When on_progress is provided, library calls it with progress info during transcription.
    """
    from mlx_qwen3_asr import transcribe  # type: ignore

    # API backend: delegate to OpenRouter
    if ASR_BACKEND == "api":
        from asr_api import transcribe_via_api  # type: ignore
        print(f"  Using API ASR ({ASR_API_MODEL}) on: {audio_path.name}")
        srt_result = transcribe_via_api(audio_path, language)
        if ASR_HOTWORDS:
            srt_result = _apply_hotwords_to_srt(srt_result)
        srt_result = _apply_cc_conversion(srt_result, mode=CC_CONVERSION)
        return srt_result

    # Chunk long audio (>30min) into 10-min segments for reliable transcription
    duration_sec = get_media_duration_sec(audio_path)
    CHUNK_THRESHOLD = 1800  # 30 min
    CHUNK_DURATION = 600    # 10 min
    CHUNK_OVERLAP = 3       # 3 seconds overlap for boundary safety

    if duration_sec > CHUNK_THRESHOLD:
        return _transcribe_chunked(
            audio_path, language, diarize, num_speakers, use_aligner, use_draft,
            chunk_duration=CHUNK_DURATION, overlap=CHUNK_OVERLAP, on_progress=on_progress,
        )

    # Determine draft model for speculative decoding (only for longer audio)
    draft_model = None
    if use_draft:
        if duration_sec > 600:  # >10 min
            draft_model = ASR_MODEL  # Use same model as draft
            print(f"  Using speculative decoding (audio: {duration_sec/60:.1f} min)")

    print(f"  Running Qwen3-ASR-0.6B on: {audio_path.name}")
    result = transcribe(
        audio_path,
        model=ASR_MODEL,
        draft_model=draft_model,
        language=language,
        return_timestamps=True,
        verbose=False,
        diarize=diarize,
        diarization_num_speakers=num_speakers,
        on_progress=on_progress,
    )

    # Use speaker segments when diarization is enabled
    if diarize and hasattr(result, "speaker_segments") and result.speaker_segments:
        return _format_speaker_srt(result.speaker_segments)

    # ForcedAligner: word-level timestamps for precise subtitle alignment
    if use_aligner and result.text and result.text.strip():
        try:
            srt_result = _align_and_format(audio_path, result.text, language=language,
                                            reference_text=reference_text)
            if ASR_HOTWORDS:
                srt_result = _apply_hotwords_to_srt(srt_result)
            srt_result = _apply_cc_conversion(srt_result, mode=CC_CONVERSION)
            return srt_result
        except Exception as e:
            print(f"  [info] ForcedAligner fell back to segment timestamps: {e}")

    if not result.segments:
        raw = f"1\n00:00:00,000 --> 00:00:01,000\n{result.text.strip()}\n"
        if ASR_HOTWORDS:
            raw = _apply_hotwords_to_srt(raw)
        if CC_CONVERSION != "off":
            raw = _apply_cc_conversion(raw, mode=CC_CONVERSION)
        return raw

    subtitle_blocks = _group_words_into_subtitles(result.segments)

    srt_blocks: list[str] = []
    for i, block in enumerate(subtitle_blocks, 1):
        start = _seconds_to_srt_time(block["start"])
        end = _seconds_to_srt_time(block["end"])
        srt_blocks.append(f"{i}\n{start} --> {end}\n{block['text']}")

    result_srt = "\n\n".join(srt_blocks) + "\n"
    if ASR_HOTWORDS:
        result_srt = _apply_hotwords_to_srt(result_srt)
    if CC_CONVERSION != "off":
        result_srt = _apply_cc_conversion(result_srt, mode=CC_CONVERSION)
    return result_srt


def _load_hotwords_terms() -> set[str]:
    """Load glossary English terms to use as ASR hot words.

    Extracts both full phrases and parenthesized abbreviations (e.g.
    'Net Present Value (NPV)' yields both the full phrase and 'NPV').
    """
    terms: set[str] = set()
    try:
        from config import load_glossary  # type: ignore
        glossary = load_glossary()
        for k in glossary.keys():
            k = k.strip()
            if not k or len(k) <= 1:
                continue
            terms.add(k)
            # Extract parenthesized abbreviations: "Net Present Value (NPV)" → "NPV"
            import re
            m = re.search(r'\(([^)]{2,10})\)', k)
            if m:
                abbr = m.group(1).strip()
                if abbr.isupper() and len(abbr) >= 2:
                    terms.add(abbr)
    except Exception:
        pass
    return terms


def _apply_cc_conversion(srt_text: str, mode: str = "standard") -> str:
    """Convert Simplified Chinese to Traditional Chinese in SRT text.

    mode: "standard" (s2t) or "taiwan" (s2tw) or "off" (passthrough)
    """
    if mode == "off":
        return srt_text
    try:
        from opencc import OpenCC  # type: ignore
        config = "s2tw" if mode == "taiwan" else "s2t"
        converter = OpenCC(config)
        return converter.convert(srt_text)
    except Exception:
        return srt_text


def _apply_hotwords_to_srt(srt_text: str, extra_terms: list[str] | None = None) -> str:
    """Scan SRT text and correct ASR errors against glossary terms.

    extra_terms: additional terms to treat as hot words (from user prompt).
    """
    import re
    terms = _load_hotwords_terms()
    if extra_terms:
        for t in extra_terms:
            # Split multi-word prompt into individual terms
            for word in re.split(r'[\s,，、;；]+', t.strip()):
                word = word.strip()
                if word and len(word) >= 2:
                    terms.add(word)
    if not terms:
        return srt_text

    corrections = 0

    # Sort by length descending to avoid partial matches
    sorted_terms = sorted(terms, key=len, reverse=True)

    def _correct_line(text: str) -> str:
        nonlocal corrections
        original = text
        for term in sorted_terms:
            # Pattern: escaped regex, case-insensitive
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            text, n = pattern.subn(term, text)
            corrections += n

            # Also handle space-inserted acronyms: "N P V" → "NPV"
            if len(term) <= 5 and term.isupper() and term.isalpha():
                spaced = r"\s*".join(re.escape(c) for c in term)
                text, n = re.subn(spaced, term, text, flags=re.IGNORECASE)
                corrections += n

        return text

    # Process each SRT entry's text line
    lines = srt_text.split("\n")
    result_lines = []
    for line in lines:
        # Only correct text lines (not timestamp or index lines)
        if "-->" not in line and not line.strip().isdigit() and line.strip():
            corrected = _correct_line(line)
            result_lines.append(corrected)
        else:
            result_lines.append(line)

    if corrections > 0:
        print(f"  Hot words: {corrections} glossary term(s) corrected")

    return "\n".join(result_lines)


def _align_and_format(audio_path: Path, transcript: str, language: Optional[str] = None,
                      reference_text: Optional[str] = None) -> str:
    """Run ForcedAligner on transcript (or reference), return SRT with word-level timestamps.

    When reference_text is provided, align against the reference (which has correct
    terminology) instead of the raw ASR transcript — used for script matching.
    """
    from mlx_qwen3_asr import ForcedAligner, load_audio  # type: ignore

    aligner = ForcedAligner(ASR_ALIGNER_MODEL)

    # Load audio as MLX array, convert to numpy for aligner
    audio = load_audio(audio_path)
    import mlx.core as mx
    audio_np = mx.eval(audio)
    if hasattr(audio_np, "__array__"):
        audio_np = audio_np.__array__()
    elif isinstance(audio_np, mx.array):
        audio_np = audio_np.tolist()
    audio_np = audio_np.astype("float32")

    # Use reference text for alignment when available (script matching)
    align_text = reference_text or transcript
    source_label = "reference" if reference_text else "transcript"
    print(f"  ForcedAligner ({source_label}): aligning {len(align_text.split())} words")

    aligned_words = aligner.align(audio_np, align_text, language=language or "en")

    if not aligned_words:
        raise RuntimeError("ForcedAligner returned no words")

    print(f"  ForcedAligner: {len(aligned_words)} words aligned")

    # Group aligned words into subtitle blocks
    blocks = _group_aligned_words_into_subtitles(aligned_words)

    srt_blocks: list[str] = []
    for i, block in enumerate(blocks, 1):
        start = _seconds_to_srt_time(block["start"])
        end = _seconds_to_srt_time(block["end"])
        srt_blocks.append(f"{i}\n{start} --> {end}\n{block['text']}")

    # ── Save word-level timestamps as JSON ─────────────────────────────
    words_json = []
    for w in aligned_words:
        wt = getattr(w, "text", None) or (w.get("text", "") if isinstance(w, dict) else "")
        ws = getattr(w, "start", None) or (w.get("start", 0.0) if isinstance(w, dict) else 0.0)
        we = getattr(w, "end", None) or (w.get("end", 0.0) if isinstance(w, dict) else 0.0)
        if wt and wt.strip():
            words_json.append({
                "text": wt.strip(),
                "start": float(ws),
                "end": float(we),
            })
    try:
        import json
        words_path = audio_path.with_suffix(".words.json")
        with open(words_path, "w", encoding="utf-8") as f:
            json.dump({"words": words_json, "language": language or "en"}, f, ensure_ascii=False)
    except Exception:
        pass

    return "\n\n".join(srt_blocks) + "\n"


def _group_aligned_words_into_subtitles(
    words: list,
    max_duration: float = 5.0,
    max_chars: int = 80,
) -> list[dict]:
    """Group word-level aligned words into SRT blocks, preferring sentence boundaries.

    Converts AlignedWord objects to segment dicts and delegates to the shared
    smart splitting logic in _group_words_into_subtitles.
    """
    segments: list[dict] = []
    for w in words:
        if hasattr(w, "text"):
            word_text = w.text.strip()
            word_start = w.start_time if hasattr(w, "start_time") else getattr(w, "start", 0.0)
            word_end = w.end_time if hasattr(w, "end_time") else getattr(w, "end", 0.0)
        else:
            word_text = w.get("text", "").strip()
            word_start = w.get("start", w.get("start_time", 0.0))
            word_end = w.get("end", w.get("end_time", 0.0))
        if word_text:
            segments.append({"text": word_text, "start": word_start, "end": word_end})

    return _group_words_into_subtitles(segments, max_duration=max_duration, max_chars=max_chars)


def _format_speaker_srt(speaker_segments: list[dict]) -> str:
    """Format diarized speaker segments into SRT with speaker labels."""
    srt_blocks: list[str] = []
    for i, seg in enumerate(speaker_segments, 1):
        start = _seconds_to_srt_time(seg["start"])
        end = _seconds_to_srt_time(seg["end"])
        speaker = seg.get("speaker", "Speaker")
        text = seg.get("text", "").strip()
        if text:
            srt_blocks.append(f"{i}\n{start} --> {end}\n[{speaker}] {text}")
    return "\n\n".join(srt_blocks) + "\n"

# ─────────────────────────── Public API ─────────────────────────────────────

def transcribe_files(
    media_files: list[Path],
    language: str | None = None,
    dry_run: bool = False,
    max_concurrent: int | None = None,
    reference_text: str | None = None,
) -> dict[Path, Path]:
    from srt_utils import parse_srt, clean_subtitle_text, write_srt  # type: ignore

    print(f"\n{'='*60}")
    print(f"ASR backend: Qwen3-ASR-0.6B (local MLX) {'[DRY RUN]' if dry_run else ''}")
    print(f"{'='*60}\n")

    results: dict[Path, Path] = {}
    results_lock = threading.Lock()

    if max_concurrent is None:
        max_concurrent = ASR_MAX_CONCURRENT

    def _process_one(media_path: Path) -> tuple[Path, Path | None]:
        """Process a single media file and return (input_path, srt_path or None)."""
        nonlocal language, dry_run
        out_dir = OUTPUT_DIR / media_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        srt_path = out_dir / f"{media_path.stem}.srt"

        if srt_path.exists():
            print(f"  [skip] SRT already exists: {media_path.name}")
            return (media_path, srt_path)

        if dry_run:
            print(f"  [dry-run] Would transcribe {media_path.name}")
            return (media_path, srt_path)

        try:
            upload_path = media_path
            if media_path.suffix.lower() in VIDEO_EXTENSIONS:
                upload_path = extract_audio(media_path, out_dir)

            # Silence cache
            stats = f"{upload_path.stat().st_size}_{upload_path.stat().st_mtime}"
            silence_cache = out_dir / ".silence_cached"
            if silence_cache.exists() and silence_cache.read_text(encoding="utf-8") == stats:
                print(f"  [skip] Silence check cached: {media_path.name}")
            else:
                SILENCE_THRESHOLD = -50
                if check_silence(upload_path, threshold_db=SILENCE_THRESHOLD):
                    from usage_tracker import log_failure  # type: ignore
                    log_failure("ASR", media_path.name, "Audio is mostly silent, skipping transcription")
                    print(f"  [skip] Mostly silent: {media_path.name}")
                    return (media_path, None)
                silence_cache.write_text(stats, encoding="utf-8")

            raw_srt = _transcribe_with_qwen3_asr(upload_path, language, diarize=ASR_DIARIZE, num_speakers=ASR_DIARIZE_NUM_SPEAKERS, use_draft=ASR_USE_DRAFT, reference_text=reference_text, on_progress=_default_progress_cb)

            if not raw_srt.strip():
                from usage_tracker import log_failure  # type: ignore
                log_failure("ASR", media_path.name, "Qwen3-ASR returned empty transcription")
                print(f"  [WARNING] Qwen3-ASR returned EMPTY transcription for {media_path.name}.")
                (out_dir / f"{media_path.stem}_asr_debug.txt").write_text("[EMPTY RESPONSE]", encoding="utf-8")
                return (media_path, None)

            entries = parse_srt(raw_srt)
            if not entries:
                from usage_tracker import log_failure  # type: ignore
                debug_p = out_dir / f"{media_path.stem}_asr_debug.txt"
                debug_p.write_text(raw_srt, encoding="utf-8")
                log_failure("ASR", media_path.name, f"Could not parse SRT format. First 200 chars: {raw_srt[:200]}")
                print(f"  [WARNING] Could not parse SRT format. Raw response saved to {debug_p.name}")
                txt_path = out_dir / f"{media_path.stem}.transcript.txt"
                txt_path.write_text(raw_srt, encoding="utf-8")
                return (media_path, None)

            for e in entries:
                e.text = clean_subtitle_text(e.text)
            entries = [e for e in entries if e.text]
            if not entries:
                from usage_tracker import log_failure  # type: ignore
                log_failure("ASR", media_path.name, "All subtitle entries were empty after cleaning")
                print(f"  [ERROR] All entries were empty after cleaning for {media_path.name}")
                return (media_path, None)

            duration_sec = get_media_duration_sec(upload_path)
            if duration_sec > 300:
                min_expected = max(5, int(duration_sec / 120))
                if len(entries) < min_expected:
                    from usage_tracker import log_failure  # type: ignore
                    log_failure("ASR", media_path.name,
                                f"Suspicious output: {len(entries)} entries for "
                                f"{duration_sec/60:.1f}min audio (expected ≥{min_expected}). "
                                "Qwen3-ASR may have returned garbled SRT format.")
                    print(f"  [WARNING] Only {len(entries)} entries for "
                          f"{duration_sec/60:.1f}min audio — ASR output may be garbled.")

            write_srt(entries, srt_path)
            txt_path = out_dir / f"{media_path.stem}.transcript.txt"
            txt_path.write_text(" ".join(e.text for e in entries) + "\n", encoding="utf-8")

            # Move word-level timestamps JSON if it exists alongside audio
            words_src = upload_path.with_suffix(".words.json")
            if words_src.exists():
                import shutil
                words_dst = out_dir / f"{media_path.stem}.words.json"
                shutil.move(str(words_src), str(words_dst))

            if upload_path != media_path and upload_path.exists():
                try:
                    upload_path.unlink()
                except OSError:
                    pass

            print(f"  Saved: {srt_path.name} ({len(entries)} entries)")
            return (media_path, srt_path)
        except Exception as e:
            from usage_tracker import log_failure  # type: ignore
            log_failure("ASR Pipeline", media_path.name, str(e))
            print(f"  [ERROR] {e}")
            return (media_path, None)

    # Process files in parallel using ThreadPoolExecutor
    from concurrent.futures import ThreadPoolExecutor, as_completed
    n_files = len(media_files)
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {executor.submit(_process_one, p): p for p in media_files}
        for i, future in enumerate(as_completed(futures), 1):
            media_path = futures[future]
            try:
                input_path, srt_path = future.result()
                if srt_path:
                    with results_lock:
                        results[input_path] = srt_path
            except Exception as e:
                print(f"  [ERROR] Unexpected error for {media_path.name}: {e}")

    return results

def transcribe_one_video(audio_16khz_path: str, language: Optional[str], working_directory: str) -> Dict[str, Any]:
    """Single-video ASR wrapper for the Multi-Agent Director."""
    from pathlib import Path
    a_p = Path(audio_16khz_path)
    w_d = Path(working_directory)
    
    # 1. Transcribe locally with Qwen3-ASR-0.6B
    raw_srt = _transcribe_with_qwen3_asr(a_p, language, diarize=ASR_DIARIZE, num_speakers=ASR_DIARIZE_NUM_SPEAKERS, use_draft=ASR_USE_DRAFT)

    # 2. Clean and save result
    from srt_utils import parse_srt, clean_subtitle_text, write_srt # type: ignore
    entries = parse_srt(raw_srt)
    for e in entries:
        e.text = clean_subtitle_text(e.text)
        
    srt_p = w_d / f"{a_p.stem.replace('_16k', '')}.srt"
    write_srt(entries, srt_p)
    
    # 4. Save transcript preview
    txt_p = w_d / f"{srt_p.stem}.transcript.txt"
    txt_p.write_text(" ".join(e.text for e in entries) + "\n", encoding="utf-8")
    
    return {
        "raw_srt_text": raw_srt,
        "transcript_text": txt_p.read_text(encoding="utf-8"),
        "srt_path": str(srt_p)
    }

