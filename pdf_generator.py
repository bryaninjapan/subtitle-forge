from fpdf import FPDF
from pathlib import Path

def create_slide_pdf(frame_paths: list[Path], output_path: Path, title: str):
    """Combine keyframes into a single PDF document."""
    if not frame_paths: return
    
    pdf = FPDF(orientation="landscape", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False, margin=0)
    pdf.set_font("helvetica", "B", 16)
    
    for i, frame in enumerate(sorted(frame_paths)):
        pdf.add_page()
        # Full page width (297mm)
        pdf.image(str(frame), x=0, y=0, w=297)
        # Add index in top-right
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(270, 5)
        pdf.cell(20, 10, f"Slide {i+1}", align="R")
        
    pdf.output(str(output_path))
    print(f"  [PDF] Created slide deck: {output_path.name}")
