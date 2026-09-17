"""Generates a PDF summary report from batch analysis results.

Kept in a module separate from app.py — a pure function with no dependency
on Streamlit (st.*); leaving it inside app.py would have required running
the whole Streamlit script (widgets, forms) just to test this function.
Indeed, when it was tried directly via `import app`, app.py's top-level
code polluted Streamlit's internal form/page state and broke the
AppTest-based tests below with a "Forms cannot be nested in other forms"
error — that's why this module was split out.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
from fpdf import FPDF

# Used to be a hardcoded macOS system path (/System/Library/Fonts/...) — the
# PDF download button crashed outright on Docker/Linux/Windows because the
# file couldn't be found there (a live-verified portability bug). Now uses a
# Unicode font that supports Turkish characters (ş, ğ, ı, ö, ü, ç), bundled
# directly into the repo (fonts/) so it's OS-independent.
PDF_FONT = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"


def pdf_raporu_olustur(toplam: int, olumlu: int, notr: int, olumsuz: int, ort_guven: float, sonuc_df: pd.DataFrame) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVuSans", "", PDF_FONT)
    pdf.set_font("DejaVuSans", size=18)
    pdf.cell(text="Duygu Analizi Raporu", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVuSans", size=10)
    pdf.cell(text=f"Oluşturulma: {datetime.now().strftime('%d.%m.%Y %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("DejaVuSans", size=12)
    for satir in [f"Toplam yorum: {toplam}", f"Olumlu: {olumlu}", f"Nötr: {notr}", f"Olumsuz: {olumsuz}", f"Ortalama model güveni: %{ort_guven}"]:
        pdf.cell(text=satir, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(7)
    pdf.set_font("DejaVuSans", size=12)
    pdf.cell(text="İlk 20 sonuç", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVuSans", size=9)
    for _, satir in sonuc_df.head(20).iterrows():
        metin = str(satir["metin"]).replace("\n", " ")[:105]
        pdf.multi_cell(0, 5, text=f"[{satir['etiket'].upper()} · %{satir['guven'] * 100:.1f}] {metin}", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
