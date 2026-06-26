import os
from pathlib import Path

def wipe_stale_outputs(output_dir: Path):
    """
    Safely delete stale output files to trigger a full re-run.
    KEEP: frames/ directory (saves time on extraction).
    DELETE: .srt, .zh.srt, .txt, _StudyNotes.md, _Chapters.txt
    """
    print(f"\n[Wipe] Scanning {output_dir} for stale outputs...")
    
    extensions_to_delete = [".srt", ".txt", ".md"]
    total_deleted = 0
    
    for root, dirs, files in os.walk(output_dir):
        # Skip the frames directory
        if "frames" in root:
            continue
            
        root_path = Path(root)
        for file in files:
            file_path = root_path / file
            
            # Special case: don't delete .gitkeep or system files
            if file.startswith("."):
                continue
                
            if any(file.endswith(ext) for ext in extensions_to_delete):
                print(f"  Deleting: {file_path.relative_to(output_dir)}")
                file_path.unlink()
                total_deleted += 1
                
    print(f"\n[Wipe] Done! Removed {total_deleted} stale output files.")
    print("[Wipe] Keyframes (frames/) have been preserved to speed up regeneration.")

if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).parent
    OUTPUT_DIR = PROJECT_ROOT / "output"
    wipe_stale_outputs(OUTPUT_DIR)
