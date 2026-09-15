"""Toplu analiz sonuçlarından PDF özet raporu üretir.

app.py'den ayrı bir modülde tutuluyor — Streamlit'e (st.*) hiçbir bağımlılığı
olmayan saf bir fonksiyon; app.py'nin içinde kalması, bu fonksiyonu test
etmek için tüm Streamlit script'ini (widget'lar, formlar) çalıştırmayı
gerektirirdi. Nitekim `import app` ile doğrudan test edilmeye çalışıldığında,
app.py'nin üst düzeyde çalışan kodu Streamlit'in dahili form/sayfa state'ini
kirletip AŞAĞIDAKİ AppTest tabanlı testleri "Forms cannot be nested in other
forms" hatasıyla bozmuştu — bu modülün ayrılma sebebi budur.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
from fpdf import FPDF

# Önceden sabit bir macOS sistem yoluydu (/System/Library/Fonts/...) — Docker/
# Linux/Windows'ta dosya bulunamadığı için PDF indirme düğmesi doğrudan
# çöküyordu (canlı doğrulanmış bir taşınabilirlik hatası). Artık Türkçe
# karakterleri (ş, ğ, ı, ö, ü, ç) destekleyen bir Unicode font, işletim
# sisteminden bağımsız olması için doğrudan repo içine gömülü (fonts/).
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
