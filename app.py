"""
Streamlit arayüzü — Türkçe Duygu Analizi
Çalıştırmak için: streamlit run app.py
"""

import html
import json

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import altair as alt
from sentiment import analiz_et, duygu_olasiliklari, toplu_analiz, kelime_onemleri, konu_analizi, aktif_model_adi
from geri_bildirim import kaydet as geri_bildirim_kaydet
from pdf_raporu import pdf_raporu_olustur

st.set_page_config(page_title="Türkçe Duygu Analizi", page_icon="💬", layout="wide")


def guven_durumu(guven: float) -> tuple[str, str, str]:
    if guven < 0.65:
        return "İnceleme önerilir", "low", "Model bu yorumda kararsız. Sonucu manuel olarak kontrol etmeni öneririz."
    if guven < 0.80:
        return "Orta güven", "medium", "Sonuç kullanılabilir; önemli kararlar için yorumu da incelemeni öneririz."
    return "Yüksek güven", "high", "Modelin bu sınıflandırmaya güveni yüksek."


def geri_bildirim_formunu_kaydet(metin: str, tahmin: str, guven: float) -> None:
    karar = st.session_state["geri_bildirim_karar"]
    dogru_etiket = tahmin if karar == "Doğru" else st.session_state["geri_bildirim_etiket"]
    geri_bildirim_kaydet(metin, tahmin, guven, karar.lower(), dogru_etiket)
    st.session_state["geri_bildirim_mesaji"] = "Geri bildirimin kaydedildi. Teşekkürler!"


def yeni_analiz_baslat() -> None:
    st.session_state["yorum_metni"] = ""
    st.session_state.pop("tekil_analiz_verisi", None)


def yeni_dosya_analizi_baslat() -> None:
    st.session_state["dosya_yukleyici_no"] = st.session_state.get("dosya_yukleyici_no", 0) + 1
    st.session_state.pop("toplu_analiz_sonuclari", None)


UYGULAMA_STILI = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

/* ============================================================
   1) TEMEL TEMA — ilk tasarım katmanı: renk tokenleri (:root),
      kart/sekme/buton gibi temel bileşen stilleri.
   ============================================================ */

:root {
  --page-plane: #f9f9f7;
  --surface-1: #fcfcfb;
  --surface-2: rgba(11,11,11,0.04);
  --text-primary: #0b0b0b;
  --text-secondary: #52514e;
  --text-muted: #898781;
  --border: rgba(11,11,11,0.10);
  --gridline: #e1e0d9;
  --good: #0ca30c;
  --critical: #d03b3b;
  --neutral: #fab219;
  --neutral-text: #9a6700;
  --accent: #4a3aa7;
  --accent-ink: #ffffff;
  --accent-wash: rgba(74,58,167,0.08);
}
/* NOT: burada bilerek bir @media (prefers-color-scheme: dark) bloğu YOK.
   Önceden vardı ama aşağıdaki "2) ÜRÜN TEMASI" bölümü aynı :root
   değişkenlerini koşulsuz (sabit açık renklerle) yeniden tanımladığı için
   CSS önceliği gereği hiçbir zaman uygulanmıyordu — OS karanlık modunu
   destekliyormuş
   gibi görünen, gerçekte çalışmayan ölü kod. Tema artık TEK kaynaktan
   yönetiliyor: aşağıdaki `karanlik_mod` toggle'ı (bkz. sayfanın altındaki
   OS tercihi ön yükleme mantığı — toggle'ın İLK değeri OS tercihinden
   okunuyor, ama ondan sonra tamamen kullanıcının elindedir, CSS ile
   yarışan ikinci bir otomatik kaynak yok). */

html, body, [class*="st-emotion-cache"]:not([data-testid="stIconMaterial"]) {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
.stApp { background: var(--page-plane); }
footer { visibility: hidden; }
.block-container { padding-top: 2.5rem; max-width: 780px; }

/* ---- sidebar / brand ---- */
[data-testid="stSidebar"] {
  background: var(--surface-1);
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div { padding-top: 1.75rem; }
.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.brand-badge {
  width: 36px; height: 36px; border-radius: 9px; flex-shrink: 0;
  background: var(--accent); color: var(--accent-ink);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
}
.brand-name { font-weight: 800; font-size: 16px; color: var(--text-primary); letter-spacing: -0.01em; }
.brand-desc { font-size: 13.5px; color: var(--text-secondary); line-height: 1.5; margin: 0 0 18px 0; }
.side-divider { height: 1px; background: var(--border); margin: 16px 0; border: none; }
.side-title {
  font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--text-muted); margin-bottom: 10px;
}
.side-steps { margin: 0 0 4px 0; padding: 0; list-style: none; }
.side-steps li {
  display: flex; align-items: flex-start; gap: 9px; font-size: 13.5px;
  color: var(--text-secondary); margin-bottom: 10px; line-height: 1.4;
}
.side-steps .n {
  flex-shrink: 0; width: 18px; height: 18px; border-radius: 5px;
  background: var(--accent-wash); color: var(--accent);
  font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center;
  margin-top: 1px;
}
.model-tag {
  display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--text-muted);
}
.model-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--good); flex-shrink: 0; }

/* ---- header ---- */
.eyebrow {
  font-size: 11.5px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--accent); margin-bottom: 8px;
}
h1.page-title { font-size: 27px; font-weight: 800; margin: 0; color: var(--text-primary); letter-spacing: -0.015em; }
.subtitle { color: var(--text-secondary); margin: 6px 0 24px 0; font-size: 15px; }

/* ---- pill tabs ---- */
[data-testid="stTabs"] [role="tablist"] {
  display: inline-flex; gap: 2px; background: var(--surface-2);
  padding: 4px; border-radius: 11px; border-bottom: none !important;
}
[data-testid="stTab"] {
  border-radius: 8px !important; padding: 7px 18px !important; border: none !important;
}
[data-testid="stTab"] p { font-size: 13.5px; font-weight: 600; color: var(--text-secondary); margin: 0; }
[data-testid="stTab"][aria-selected="true"] { background: var(--surface-1); box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
[data-testid="stTab"][aria-selected="true"] p { color: var(--accent); }
[data-testid="stTabs"] .react-aria-SelectionIndicator { display: none !important; }

/* ---- cards ---- */
.card-title { font-size: 13px; font-weight: 700; color: var(--text-secondary); margin-bottom: 10px; }
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface-1) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}

/* ---- result card w/ confidence ring ---- */
.result-card {
  display: flex; align-items: center; gap: 18px;
  border-radius: 14px; padding: 20px 22px; margin-top: 16px;
  border: 1px solid var(--border);
  border-left: 4px solid var(--rc-color);
  background: var(--surface-1);
}
.conf-ring {
  width: 68px; height: 68px; border-radius: 50%; flex-shrink: 0;
  background: conic-gradient(var(--rc-color) calc(var(--pct) * 3.6deg), var(--gridline) 0deg);
  display: flex; align-items: center; justify-content: center;
}
.conf-ring-inner {
  width: 52px; height: 52px; border-radius: 50%; background: var(--surface-1);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: var(--text-primary);
}
.rc-icon-row { display: flex; align-items: center; gap: 8px; }
.rc-icon { font-size: 20px; }
.rc-label { font-size: 18px; font-weight: 800; letter-spacing: -0.01em; }
.rc-conf { font-size: 13px; color: var(--text-secondary); margin-top: 3px; }

/* ---- kelime vurgulama (explainability) ---- */
.vurgu-metin { line-height: 2.1; font-size: 15px; color: var(--text-primary); }
.vurgu-metin span.k { padding: 1px 4px; border-radius: 4px; }
.vurgu-not { font-size: 12.5px; color: var(--text-muted); margin-top: 10px; }

/* ---- konu bazlı analiz ---- */
.konu-liste { display: flex; flex-direction: column; gap: 10px; }
.konu-satir { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.konu-ad { font-weight: 700; font-size: 13.5px; color: var(--text-primary); min-width: 130px; text-transform: capitalize; }
.konu-parca { font-size: 13px; color: var(--text-secondary); flex: 1; font-style: italic; }
.konu-pill { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; white-space: nowrap; }

/* ---- stat tiles ---- */
.stat-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 4px 0 20px 0; }
.stat-tile {
  background: var(--surface-1); border: 1px solid var(--border); border-radius: 14px;
  padding: 15px 16px;
}
.stat-tile .label {
  font-size: 11px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--text-muted); margin-bottom: 7px;
}
.stat-tile .value { font-size: 25px; font-weight: 800; color: var(--text-primary); letter-spacing: -0.01em; }

/* ---- buttons ---- */
button[kind="primary"], [data-testid="stBaseButton-primary"] {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
  color: var(--accent-ink) !important;
  border-radius: 9px !important;
  font-weight: 600 !important;
}
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
  filter: brightness(1.08);
}
button[kind="secondary"], [data-testid="stBaseButton-secondary"] {
  border-radius: 9px !important;
  font-weight: 600 !important;
}

/* ---- chat_input (tek yorum girişi) ---- */
[data-testid="stChatInput"] {
  border-radius: 10px !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 1px var(--accent) !important;
}
[data-testid="stChatInputSubmitButton"]:not([disabled]) {
  background-color: var(--accent) !important;
}

/* ============================================================
   2) ÜRÜN TEMASI — uygulamayı klasik Streamlit görünümünden daha
      ürün odaklı bir analiz çalışma alanına taşımak için 1)'in
      ÜZERİNE BİNEN tema. Buradaki :root aynı değişkenleri KASITLI
      olarak yeniden tanımlayıp yukarıdaki temel temayı geçersiz
      kılıyor — yani şu an fiilen görünen renkler burasıdır, 1)
      değil. İki katman aynı class'ları defalarca override ettiği
      için bunu düzenlerken 1)'i de kontrol et (bkz. SKILL.md
      Gotchas — ikon fontu kırılması tam bu yüzden yaşanmıştı).
   ============================================================ */
:root { --page-plane:#f4f6fb; --surface-1:#fff; --surface-2:#f7f8fc; --text-primary:#17213c; --text-secondary:#536079; --text-muted:#8a94a9; --border:#e5e9f2; --gridline:#e8ebf2; --good:#159b6b; --critical:#db5361; --neutral:#f1ad34; --neutral-text:#ae6f08; --accent:#4f46e5; --accent-wash:#eeedff; --shadow:0 12px 30px rgba(36,47,79,.06); }
html, body, [class*="st-emotion-cache"]:not([data-testid="stIconMaterial"]) { font-family:'DM Sans',system-ui,sans-serif; }
[data-testid="stIconMaterial"] {
  font-family:"Material Symbols Rounded","Material Icons" !important;
  font-weight:normal !important;
  font-style:normal !important;
  font-size:20px !important;
  line-height:1 !important;
  letter-spacing:normal !important;
  text-transform:none !important;
  white-space:nowrap !important;
  word-wrap:normal !important;
  direction:ltr !important;
  font-feature-settings:"liga" !important;
  -webkit-font-feature-settings:"liga" !important;
  -webkit-font-smoothing:antialiased !important;
}
.stApp { background:var(--page-plane); }
/* stHeader, sayfanın üst 60px'ini position:absolute + çok yüksek z-index ile
   kaplıyor. Şeffaf olduğu için görünmüyor ama pointer-events'i kapatılmadıkça
   altındaki gerçek içeriğe (marka satırındaki karanlık mod toggle'ı tam bu
   bandın içinde) yapılan tıklamaları yutmaya devam ediyor — canlı Playwright
   testinde doğrulanan gerçek bir hata, toggle'a tıklanamamasının sebebi
   buydu. stToolbar (hamburger menü) zaten display:none olduğu için
   stHeader'ın artık tıklanması gereken hiçbir içeriği yok, tamamen
   tıklama-geçirmez yapmak güvenli. */
[data-testid="stHeader"] { background:transparent; pointer-events:none; }
[data-testid="stToolbar"] { display:none !important; }
.stApp, [data-testid="stAppViewContainer"], .topbar-divider, .model-status,
.feature-strip, [data-testid="stTabs"] [role="tablist"], [data-testid="stTab"],
[data-testid="stVerticalBlockBorderWrapper"], .result-card, .conf-ring-inner,
.probability-list, .probability-track, .preview-result, .preview-bar,
.analysis-detail, .stat-tile, .results-table-wrap, .results-table th,
.results-table td, [data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"] > div, [data-testid="stFileUploaderDropzone"] button,
div[data-testid="stTextArea"] textarea, button, .card-title, .card-note,
.page-title, .subtitle, .brand-name, .table-confidence {
  transition: background-color .32s ease, background .32s ease, color .26s ease,
              border-color .32s ease, box-shadow .32s ease, opacity .26s ease;
}
.block-container { max-width:1320px; padding:1rem 2.2rem 3.5rem; }
[data-testid="stSidebar"] { display:none; }
.topbar-divider { height:1px; background:var(--border); margin:10px 0 1.35rem; }
/* İçerik viewport'un yalnızca üst kısmını dolduruyor, sayfa ortada kesiliyormuş
   gibi bitiyordu (footer/kapanış yok). Sahte dolgu içerik eklemek yerine
   gerçek bilgi taşıyan bir alt bilgi satırı ekleniyor — hangi model
   çalışıyor, bu şeffaflık zaten kullanıcı için değerli. */
.app-footer { margin-top:56px; padding-top:20px; border-top:1px solid var(--border); display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; color:var(--text-muted); font-size:12px; }
.app-footer a { color:var(--text-muted); }
@media (max-width:760px) { .app-footer { margin-top:36px; } }
.st-key-karanlik_mod { display:flex; justify-content:flex-end; min-width:150px; }
.st-key-karanlik_mod [data-testid="stWidgetLabel"] p { color:var(--text-secondary); font-size:12px; font-weight:600; }
.st-key-karanlik_mod [data-testid="stToggle"] { gap:7px; }
.brand { display:flex; align-items:center; gap:10px; } .brand-badge { width:36px; height:36px; border-radius:9px; background:#554ce3; color:#fff; box-shadow:0 5px 14px rgba(79,70,229,.18); } .brand-badge svg { display:block; width:100%; height:100%; } .brand-name,h1.page-title,.stat-tile .value,.rc-label { font-family:'Plus Jakarta Sans',sans-serif; }
.brand-name { letter-spacing:-.025em; } .model-status { display:flex; align-items:center; gap:7px; font-size:12px; color:var(--text-secondary); background:var(--surface-1); border:1px solid var(--border); border-radius:99px; padding:7px 11px; } .model-dot { width:7px; height:7px; background:var(--good); box-shadow:0 0 0 3px rgba(21,155,107,.12); }
.eyebrow { font-size:10.5px; letter-spacing:.1em; margin-bottom:6px; } h1.page-title { font-size:34px; letter-spacing:-.045em; } .subtitle { margin:8px 0 20px; line-height:1.55; font-size:15.5px; }
.feature-strip { display:flex; align-items:center; flex-wrap:wrap; gap:7px; margin:0 0 20px; }
.feature-pill { padding:5px 9px; background:var(--accent-wash); border:1px solid rgba(79,70,229,.14); border-radius:999px; color:var(--accent); font-size:10.5px; font-weight:700; }
[data-testid="stTabs"] [role="tablist"] { width:max-content; background:#e9edf6; border-radius:10px; padding:4px; gap:3px; margin-bottom:12px; } [data-testid="stTab"] { padding:8px 18px !important; } [data-testid="stTab"][aria-selected="true"] { background:var(--surface-1); box-shadow:0 2px 7px rgba(40,53,91,.11); }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px !important; border:1px solid #dce2ed !important; box-shadow:0 8px 22px rgba(36,47,79,.055); } [data-testid="stVerticalBlockBorderWrapper"] > div { padding:1.1rem !important; }
/* "Tekil analiz" sekmesinde sonuç geldiğinde sağ sütun (kart+olasılıklar+
   geri bildirim formu) sol sütundan (kısa metin kutusu) çok daha uzuyor,
   göz asimetrik bir sayfa görüyordu. st.columns zaten flex satırı — kartları
   o satırın tam yüksekliğine geriyoruz, kısa taraf da uzun tarafla aynı
   yükseklikte bitiyor (içerik üstte kalır, altta boşluk oluşur — asimetri
   yerine simetrik bir "boşluk" daha az rahatsız edici).
   ÖNEMLİ: [role="tabpanel"] ile kapsamlı — bu kural önce TÜM
   stHorizontalBlock'lara uygulanmıştı, bu da sekmelerin ÜSTÜNDEKİ marka/
   karanlık-mod toggle satırını da gerdi ve toggle'ın tıklama alanını
   kaydırıp tekrar tıklanamaz hâle getirdi (canlı Playwright testinde
   doğrulanan gerçek bir regresyon — o satır st.tabs()'ten önce render
   edildiği için hiçbir tabpanel içinde değil, bu yüzden bu seçici onu
   hariç tutuyor). */
[role="tabpanel"] [data-testid="stHorizontalBlock"] { align-items:stretch; }
[role="tabpanel"] [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlockBorderWrapper"] { height:100%; }
.card-title { color:var(--text-primary); margin-bottom:5px; font-size:14px; } .card-note { color:var(--text-muted); font-size:13px; line-height:1.5; }
.result-card { border-radius:16px; padding:20px; border:1px solid color-mix(in srgb,var(--rc-color) 24%,white); background:linear-gradient(145deg,var(--rc-wash),#fff 72%); box-shadow:0 14px 34px rgba(36,47,79,.10); } .conf-ring { width:76px; height:76px; box-shadow:0 7px 18px rgba(36,47,79,.10); } .conf-ring-inner { width:58px; height:58px; font-size:14px; } .rc-label { letter-spacing:-.03em; font-size:22px; } .rc-conf { font-size:12.5px; }
.sentiment-badge { display:inline-flex; align-items:center; gap:7px; margin-bottom:5px; padding:5px 10px; border-radius:999px; background:var(--rc-color); color:#fff; font-size:11px; font-weight:800; letter-spacing:.055em; text-transform:uppercase; }
.probability-list { display:flex; flex-direction:column; gap:10px; margin:17px 1px 3px; padding-top:16px; border-top:1px solid rgba(23,33,60,.08); }
.probability-row { display:grid; grid-template-columns:62px 1fr 43px; gap:9px; align-items:center; color:var(--text-secondary); font-size:12px; font-weight:600; }
.probability-track { height:8px; overflow:hidden; border-radius:99px; background:#e7eaf1; }
.probability-fill { height:100%; min-width:2px; border-radius:99px; background:var(--bar-color); }
.probability-value { text-align:right; color:var(--text-primary); font-variant-numeric:tabular-nums; }
.vurgu-metin { font-size:14px; } .vurgu-not { font-size:12px; line-height:1.45; } .konu-ad { min-width:100px; font-size:13px; } .konu-parca { font-size:12.5px; }
.stat-grid { margin-bottom:18px; } .stat-tile { border-color:var(--border); box-shadow:0 5px 15px rgba(36,47,79,.035); } .stat-tile .value { font-size:23px; letter-spacing:-.04em; }
/* 430px iken sayfada bolca boş alan varken tablo iç kaydırmaya giriyordu
   (10-15 satırlık tipik bir dosyada bile) — iki tasarım kararı birbiriyle
   çelişiyordu. 700px, çoğu küçük/orta dosyanın (ör. örnek 13 satırlık CSV)
   hiç iç kaydırma olmadan sığmasını sağlıyor; büyük dosyalar (MAKSIMUM_
   TOPLU_YORUM=500'e kadar) için üst sınır olarak kalıyor. */
.results-table-wrap { max-height:700px; overflow:auto; margin-top:12px; border:1px solid var(--border); border-radius:12px; background:var(--surface-1); }
.results-table { width:100%; border-collapse:separate; border-spacing:0; color:var(--text-primary); font-size:13px; }
.results-table th { position:sticky; top:0; z-index:2; padding:12px 14px; background:var(--surface-2); color:var(--text-secondary); border-bottom:1px solid var(--border); text-align:left; font-size:11px; letter-spacing:.04em; text-transform:uppercase; }
.results-table td { padding:11px 14px; border-bottom:1px solid var(--border); vertical-align:middle; line-height:1.4; }
.results-table tr:last-child td { border-bottom:0; }
.results-table tbody tr:hover td { background:var(--accent-wash); }
.results-table th:nth-child(2), .results-table td:nth-child(2) { width:120px; }
.results-table th:nth-child(3), .results-table td:nth-child(3) { width:95px; text-align:right; }
.table-sentiment { display:inline-flex; align-items:center; gap:6px; padding:5px 9px; border-radius:999px; font-size:11px; font-weight:700; }
.table-sentiment::before { content:""; width:6px; height:6px; border-radius:50%; background:currentColor; }
.table-sentiment.olumlu { color:var(--good); background:rgba(21,155,107,.12); }
.table-sentiment.notr { color:var(--neutral-text); background:rgba(241,173,52,.14); }
.table-sentiment.olumsuz { color:var(--critical); background:rgba(219,83,97,.12); }
.table-confidence { color:var(--text-secondary); font-weight:700; font-variant-numeric:tabular-nums; }
.analysis-detail { margin-top:14px; padding:18px 20px; background:#fff; border:1px solid #dce2ed; border-radius:14px; box-shadow:0 8px 22px rgba(36,47,79,.045); }
.confidence-note { margin-top:14px; padding:12px 14px; border-radius:11px; font-size:13px; line-height:1.45; } .confidence-note strong { display:block; margin-bottom:2px; }
.confidence-note.low { background:#fff4e5; color:#8a5507; border:1px solid #f5d59e; } .confidence-note.medium { background:#f4f0ff; color:#55469f; border:1px solid #dcd4ff; } .confidence-note.high { background:#ecf8f3; color:#167052; border:1px solid #c8ebdc; }
.feedback-title { font-size:13px; font-weight:700; color:var(--text-primary); margin:18px 0 5px; }
.analysis-progress { display:flex; align-items:center; gap:10px; margin:10px 0 2px; padding:11px 14px; border:1px solid var(--border); border-radius:11px; background:var(--surface-1); color:var(--text-secondary); font-size:13px; font-weight:700; }
.analysis-progress span { width:16px; height:16px; flex:0 0 16px; border:2px solid var(--border); border-top-color:var(--accent); border-radius:50%; animation:analysis-spin .8s linear infinite; }
@keyframes analysis-spin { to { transform:rotate(360deg); } }
.analysis-complete { display:flex; align-items:center; gap:9px; margin:10px 0 2px; padding:11px 14px; border:1px solid rgba(21,155,107,.28); border-radius:11px; background:rgba(21,155,107,.08); color:var(--good); font-size:13px; font-weight:700; }
.analysis-complete span { display:flex; align-items:center; justify-content:center; width:20px; height:20px; flex:0 0 20px; border-radius:50%; background:var(--good); color:#fff; font-size:12px; line-height:1; }
.empty-result { height:100%; min-height:245px; display:flex; flex-direction:column; justify-content:center; padding:5px 9px; } .empty-result-icon { width:42px; height:42px; display:flex; align-items:center; justify-content:center; border-radius:10px; color:#fff; background:#554ce3; box-shadow:0 5px 14px rgba(79,70,229,.16); margin-bottom:14px; } .empty-result-icon svg { width:100%; height:100%; display:block; }
.preview-result { margin-top:17px; padding:13px 14px; border:1px solid #e3e1ff; border-radius:12px; background:linear-gradient(135deg,#f4f3ff,#fff); }
.preview-top { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; font-size:12px; font-weight:700; color:#159b6b; }
.preview-bar { height:6px; background:#e8eaf1; border-radius:99px; overflow:hidden; } .preview-bar span { display:block; width:87%; height:100%; background:#159b6b; border-radius:inherit; }
.preview-caption { margin-top:7px; color:var(--text-muted); font-size:10.5px; }
.quick-steps { display:flex; flex-direction:column; gap:10px; margin-top:17px; }
.quick-step { display:flex; align-items:center; gap:9px; color:var(--text-secondary); font-size:12px; }
.quick-step span { width:22px; height:22px; flex:0 0 22px; display:flex; align-items:center; justify-content:center; border-radius:7px; background:var(--accent-wash); color:var(--accent); font-size:10px; font-weight:800; }
.upload-head { display:flex; align-items:center; gap:10px; margin-bottom:5px; } .upload-icon { width:32px; height:32px; display:flex; align-items:center; justify-content:center; background:#eeedff; color:#4f46e5; border-radius:9px; font-size:16px; }
[data-testid="stChatInput"] { border:1px solid var(--border) !important; border-radius:12px !important; background:var(--surface-2) !important; } [data-testid="stFileUploader"] { background:#fafaff; border:2px dashed #b9b5f4; border-radius:15px; padding:12px; box-shadow:inset 0 0 0 4px #fff; } div[data-testid="stFileUploaderDropzone"] { border:0 !important; background:transparent !important; min-height:130px; } [data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:10px; overflow:hidden; }
/* Tarayıcının koyu mod tercihini uygulama bileşenlerine yansıtma. */
div[data-testid="stTextArea"] textarea { background:#fff !important; color:#17213c !important; border:1px solid #dce2ef !important; border-radius:12px !important; font-size:15px !important; line-height:1.55 !important; }
div[data-testid="stTextArea"] textarea::placeholder { color:#8a94a9 !important; opacity:1 !important; }
div[data-testid="stTextArea"] textarea:focus { border-color:#4f46e5 !important; box-shadow:0 0 0 3px rgba(79,70,229,.12) !important; }
div[data-testid="stFormSubmitButton"] button[kind="primary"], button[kind="primary"], [data-testid="stBaseButton-primary"] { background:#4f46e5 !important; color:#fff !important; border:1px solid #4f46e5 !important; border-radius:10px !important; min-height:44px; box-shadow:0 7px 16px rgba(79,70,229,.18); }
div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover, button[kind="primary"]:hover { background:#4238cf !important; border-color:#4238cf !important; }
div[data-testid="stFormSubmitButton"] button[kind="secondary"] { min-height:44px; background:transparent !important; color:var(--text-secondary) !important; border:1px solid var(--border) !important; box-shadow:none !important; }
div[data-testid="stFormSubmitButton"] button[kind="secondary"]:hover { color:var(--accent) !important; border-color:var(--accent) !important; background:var(--accent-wash) !important; }
div[data-testid="stVerticalBlockBorderWrapper"] { background:#fff !important; }
/* Streamlit bu alanı section olarak üretiyor; dosya seçici de açık kalmalı. */
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzone"] > div { background:#fff !important; border-color:#c7d0e3 !important; }
[data-testid="stFileUploaderDropzone"] button { background:#fff !important; color:#25314b !important; border:1px solid #d7deec !important; border-radius:9px !important; box-shadow:none !important; min-height:38px; }
[data-testid="stFileUploaderDropzone"] button:hover { background:#f4f5ff !important; border-color:#aaa4f5 !important; }
[data-testid="stFileUploaderDropzone"] small, [data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] p { color:#6c7890 !important; }
@media (max-width:760px) { .block-container { padding:1rem 1rem 2.5rem; } .brand-name { font-size:14px; } .model-status { width:max-content; padding:7px 9px; } .model-status .status-label { display:none; } .st-key-karanlik_mod { min-width:auto; } h1.page-title { font-size:26px; } .subtitle { font-size:14px; } .card-title { font-size:13px; } .card-note { font-size:12.5px; } .empty-result { min-height:225px; } .stat-grid { grid-template-columns:repeat(2,1fr); } .feature-strip { flex-wrap:wrap; width:auto; } .probability-row { grid-template-columns:58px 1fr 40px; } .results-table th:nth-child(2), .results-table td:nth-child(2) { width:92px; } }
@media (prefers-reduced-motion:reduce) {
  .stApp, .stApp * { transition:none !important; animation:none !important; }
}
</style>
"""
st.markdown(UYGULAMA_STILI, unsafe_allow_html=True)

# Karanlık mod: TEK kaynak `karanlik_mod` toggle'ı (session_state). OS'un
# karanlık tercihini CSS @media sorgusuyla otomatik uygulamıyoruz — bu,
# kullanıcı toggle'ı tersine çevirdiğinde iki kaynağın çakışmasına yol
# açan asıl hataydı (STYLE'ın @media bloğu, DESIGN_OVERRIDE'ın koşulsuz
# :root'u tarafından hep eziliyordu). JS ile OS tercihini okuyup URL'ye
# yönlendirerek toggle'ın başlangıç değerini otomatik ayarlamak da
# denendi, ama Streamlit'in components.html iframe'i sandbox'lı ve üst
# pencereyi yönlendirme (top-level navigation) iznine sahip değil —
# canlı Playwright testinde doğrulandı: `window.parent.location.replace`
# "permission" hatasıyla reddediliyor ve sayfa hiç render olmuyor. Bu
# yüzden en sağlam çözüm en basiti: toggle varsayılanı sabit "aydınlık",
# tamamen kullanıcı kontrolünde, hiçbir otomatik/gizli ikinci kaynak yok.
marka_alani, tema_alani = st.columns([6, 1.25], vertical_alignment="center", gap="small")
with marka_alani:
    st.markdown(
        '''<div class="brand">
          <div class="brand-badge" aria-hidden="true">
            <svg viewBox="0 0 36 36" role="img">
              <path d="M10.3 8.5h15.4c2 0 3.8 1.7 3.8 3.8v8.8c0 2.1-1.8 3.8-3.8 3.8h-7.6l-5.3 3.6.9-3.6h-3.4c-2.1 0-3.8-1.7-3.8-3.8v-8.8c0-2.1 1.7-3.8 3.8-3.8Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
              <path d="m21.8 12.8-2.1 5.1-5.5 2.4 2.2-5.3 5.4-2.2Z" fill="currentColor"/>
              <circle cx="18" cy="16.6" r="1.35" fill="#554ce3"/>
            </svg>
          </div>
          <div class="brand-name">Yorum Pusulası</div>
        </div>''',
        unsafe_allow_html=True,
    )
with tema_alani:
    # Sabit bir etiket kullanılıyor (önceden duruma göre "☾ Karanlık" /
    # "☀ Aydınlık" arası değişiyordu). Ekran okuyucular switch'in açık/kapalı
    # durumunu zaten role="switch"/aria-checked ile anons ediyor; etiketin
    # kendisinin duruma göre değişmesi hem gereksiz hem de bazı ekran
    # okuyucularda "ay Karanlık" gibi garip okunmalara yol açabiliyordu.
    karanlik_mod = st.toggle("🌙 Karanlık mod", key="karanlik_mod")

st.markdown('<div class="topbar-divider"></div>', unsafe_allow_html=True)
if karanlik_mod:
    st.markdown(
        """
        <style>
        :root {
          --page-plane:#0c1120; --surface-1:#151c2e; --surface-2:#1b2438;
          --text-primary:#f4f6fc; --text-secondary:#b7c0d3; --text-muted:#7f8ba3;
          --border:#29344a; --gridline:#303b50; --accent:#7770ff;
          --accent-wash:#282650; --shadow:0 14px 34px rgba(0,0,0,.24);
          --neutral-text:#ffc45c;
        }
        html { color-scheme:dark; }
        .stApp, [data-testid="stAppViewContainer"] { background:#0c1120 !important; }
        [data-testid="stHeader"] { background:transparent !important; }
        .app-topbar { border-color:#29344a; }
        .model-status { background:#151c2e; border-color:#29344a; color:#b7c0d3; }
        .feature-pill { background:#242447; border-color:#383864; color:#c4c0ff; }
        [data-testid="stTabs"] [role="tablist"] { background:#11182a; }
        [data-testid="stTab"][aria-selected="true"] { background:#202940; }
        [data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stVerticalBlockBorderWrapper"] { background:#151c2e !important; border-color:#29344a !important; box-shadow:0 12px 28px rgba(0,0,0,.18); }
        .result-card { border-color:var(--rc-color); background:linear-gradient(145deg,var(--rc-wash),#151c2e 72%); }
        .conf-ring-inner { background:#151c2e; }
        .probability-list { border-color:#29344a; }
        .probability-track { background:#303b50; }
        .preview-result { background:linear-gradient(135deg,#252448,#171e31); border-color:#383864; }
        .preview-bar { background:#303b50; }
        .analysis-detail, .stat-tile { background:#151c2e; border-color:#29344a; box-shadow:0 10px 24px rgba(0,0,0,.16); }
        div[data-testid="stTextArea"] textarea { background:#11182a !important; color:#f4f6fc !important; border-color:#34405a !important; }
        div[data-testid="stTextArea"] textarea::placeholder { color:#77839a !important; }
        [data-testid="stFileUploader"] { background:#11182a; border-color:#5a57a5; box-shadow:inset 0 0 0 4px #151c2e; }
        [data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzone"] > div { background:#11182a !important; border-color:#34405a !important; }
        [data-testid="stFileUploaderDropzone"] button { background:#202940 !important; color:#edf0f8 !important; border-color:#3a4761 !important; }
        [data-testid="stFileUploaderDropzone"] button:hover { background:#292f58 !important; border-color:#7770ff !important; }
        [data-testid="stFileUploaderDropzone"] small, [data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] p { color:#9ca8be !important; }
        .upload-icon { background:#282650; color:#9d98ff; border:1px solid #3b396b; }
        [data-testid="stFileUploaderFile"] { background:#202940 !important; border:1px solid #34405a !important; border-radius:11px !important; }
        [data-testid="stFileUploaderFile"] > div { background:transparent !important; }
        [data-testid="stFileUploaderFile"] span, [data-testid="stFileUploaderFile"] p { color:#edf0f8 !important; }
        [data-testid="stFileUploaderFile"] small { color:#9ca8be !important; }
        [data-testid="stFileUploaderFile"] svg { color:#9d98ff !important; fill:currentColor !important; }
        [data-testid="stFileUploaderFile"] button { background:#182033 !important; color:#c6cee0 !important; border:1px solid #3a4761 !important; box-shadow:none !important; }
        [data-testid="stFileUploaderFile"] button:hover { background:#292f58 !important; color:#fff !important; border-color:#7770ff !important; }
        [data-testid="stFileChips"] { background:transparent !important; }
        [data-testid="stFileChip"] { background:#202940 !important; color:#edf0f8 !important; border:1px solid #3a4761 !important; box-shadow:none !important; }
        [data-testid="stFileChip"] > div { background:transparent !important; }
        [data-testid="stFileChipName"], [data-testid="stFileChipName"] * { color:#edf0f8 !important; }
        [data-testid="stFileChip"] small { color:#9ca8be !important; }
        [data-testid="stFileChip"] svg { color:#9d98ff !important; }
        [data-testid="stFileChipDeleteBtn"] { background:#182033 !important; color:#c6cee0 !important; border-color:#3a4761 !important; }
        [data-testid="stFileChipDeleteBtn"]:hover { background:#292f58 !important; color:#fff !important; border-color:#7770ff !important; }
        [data-testid="stDataFrame"] { border-color:#29344a; }
        [data-testid="stDataFrame"] iframe { color-scheme:dark; }
        button[kind*="secondary"], [data-testid^="stBaseButton-secondary"], div[data-testid="stFormSubmitButton"] button[kind*="secondary"] { background:#202940 !important; color:#edf0f8 !important; border-color:#3a4761 !important; box-shadow:none !important; }
        button[kind*="secondary"]:hover, [data-testid^="stBaseButton-secondary"]:hover, div[data-testid="stFormSubmitButton"] button[kind*="secondary"]:hover { background:#292f58 !important; color:#fff !important; border-color:#7770ff !important; }
        [data-testid="stRadio"] label, [data-testid="stSelectbox"] label { color:#b7c0d3 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
if mesaj := st.session_state.pop("geri_bildirim_mesaji", None):
    st.toast(mesaj, icon="✅")

st.markdown(
    """
    <h1 class="page-title">Yorumların ne söylüyor?</h1>
    <div class="subtitle">Tek bir geri bildirimi keşfet ya da dosyanı yükleyip müşteri duygusunun genel görünümünü çıkar.</div>
    <div class="feature-strip"><span class="feature-pill">3 duygu sınıfı</span><span class="feature-pill">Konu bazlı analiz</span><span class="feature-pill">Toplu dosya desteği</span></div>
    """,
    unsafe_allow_html=True,
)

sekme1, sekme2 = st.tabs(["Tekil analiz", "Dosya analizi"])

with sekme1:
    giris_alani, ipucu_alani = st.columns([1.08, 1], gap="medium")
    with giris_alani:
        with st.container(border=True):
            st.markdown('<div class="card-title">Yorumu incele</div><div class="card-note">Müşterinin yazdığı geri bildirimi aşağıya yapıştır.</div>', unsafe_allow_html=True)
            with st.form("tek_yorum_formu", clear_on_submit=False, border=False):
                metin = st.text_area(
                    "Yorum metni",
                    placeholder="Örn: Kargo çok hızlıydı ama ürünün kalitesi beklediğim gibi değildi.",
                    height=120,
                    key="yorum_metni",
                    label_visibility="collapsed",
                )
                analiz_dugmesi, yeni_dugmesi = st.columns([1.7, 1], gap="small")
                with analiz_dugmesi:
                    tiklandi = st.form_submit_button("Analiz et  →", type="primary", use_container_width=True)
                with yeni_dugmesi:
                    st.form_submit_button("↻ Yeni analiz", type="secondary", on_click=yeni_analiz_baslat, use_container_width=True)
    sonuc_panel = ipucu_alani.empty()
    with sonuc_panel.container(border=True):
        st.markdown(
            '''<div class="empty-result">
              <div class="empty-result-icon" aria-hidden="true">
                <svg viewBox="0 0 36 36">
                  <path d="M10.3 8.5h15.4c2 0 3.8 1.7 3.8 3.8v8.8c0 2.1-1.8 3.8-3.8 3.8h-7.6l-5.3 3.6.9-3.6h-3.4c-2.1 0-3.8-1.7-3.8-3.8v-8.8c0-2.1 1.7-3.8 3.8-3.8Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
                  <path d="m21.8 12.8-2.1 5.1-5.5 2.4 2.2-5.3 5.4-2.2Z" fill="currentColor"/>
                  <circle cx="18" cy="16.6" r="1.35" fill="#554ce3"/>
                </svg>
              </div>
              <div class="card-title">Analiz sonucu burada oluşacak</div>
              <div class="card-note">Üç kısa adımda yorumunun genel tonunu ve kararın ayrıntılarını keşfet.</div>
              <div class="quick-steps">
                <div class="quick-step"><span>1</span>Yorumunu giriş alanına yapıştır</div>
                <div class="quick-step"><span>2</span>Analiz et düğmesine bas</div>
                <div class="quick-step"><span>3</span>Duygu ve konu sonuçlarını incele</div>
              </div>
            </div>''',
            unsafe_allow_html=True,
        )

    kayitli_analiz = st.session_state.get("tekil_analiz_verisi")
    if not tiklandi and kayitli_analiz:
        metin = kayitli_analiz["metin"]
        tiklandi = True

    if tiklandi:
        if metin.strip():
            if kayitli_analiz and kayitli_analiz["metin"] == metin:
                sonuc = kayitli_analiz["sonuc"]
                olasiliklar = kayitli_analiz["olasiliklar"]
            else:
                with st.status("Model hazırlanıyor ve yorum analiz ediliyor...", expanded=True) as analiz_durumu:
                    sonuc = analiz_et(metin)
                    olasiliklar = duygu_olasiliklari(metin)
                    analiz_durumu.update(label="Analiz tamamlandı", state="complete", expanded=False)
                analiz_durumu.empty()
                kayitli_analiz = {"metin": metin, "sonuc": sonuc, "olasiliklar": olasiliklar}
                st.session_state["tekil_analiz_verisi"] = kayitli_analiz
            # Konu bazlı analiz burada, sonuç kartından ÖNCE hesaplanıyor —
            # "karma duygular" rozetini kartın üstünde gösterebilmek için.
            # Önceden bu hesap sayfanın en altındaki (kapalı) accordion'a
            # kadar ertelenmişti, bu yüzden konu bazlı analiz gibi öne çıkan
            # bir özellik sonuç kartında hiç ipucu vermeden gömülü kalıyordu.
            if "konu_sonuclari" in kayitli_analiz:
                konu_sonuclari = kayitli_analiz["konu_sonuclari"]
            else:
                konu_sonuclari = konu_analizi(metin)
                kayitli_analiz["konu_sonuclari"] = konu_sonuclari
                st.session_state["tekil_analiz_verisi"] = kayitli_analiz
            karma_duygu_var = len({k["etiket"] for k in konu_sonuclari}) > 1
            DURUM = {
                "olumlu": ("var(--good)", "var(--good)", "12,163,12", "👍", "Olumlu"),
                "nötr": ("var(--neutral)", "var(--neutral-text)", "154,103,0", "😐", "Nötr"),
                "olumsuz": ("var(--critical)", "var(--critical)", "208,59,59", "👎", "Olumsuz"),
            }
            renk, metin_renk, rgb, ikon, baslik = DURUM[sonuc["etiket"]]
            yuzde = round(sonuc["guven"] * 100, 1)
            guven_baslik, guven_sinif, guven_aciklama = guven_durumu(sonuc["guven"])
            cubuklar = []
            for cubuk_etiket, cubuk_baslik, cubuk_renk in [
                ("olumlu", "Olumlu", "#159b6b"),
                ("nötr", "Nötr", "#f1ad34"),
                ("olumsuz", "Olumsuz", "#db5361"),
            ]:
                cubuk_yuzde = olasiliklar.get(cubuk_etiket, 0) * 100
                cubuklar.append(f'''<div class="probability-row"><span>{cubuk_baslik}</span><div class="probability-track"><div class="probability-fill" style="--bar-color:{cubuk_renk};width:{cubuk_yuzde:.1f}%"></div></div><span class="probability-value">%{cubuk_yuzde:.1f}</span></div>''')
            with sonuc_panel.container(border=True):
                st.markdown(f"""
                <div class="result-card" style="--rc-color:{renk};--rc-wash:rgba({rgb},.10);">
                  <div class="conf-ring" style="--pct: {yuzde};">
                    <div class="conf-ring-inner">%{yuzde}</div>
                  </div>
                  <div class="rc-body">
                    <div class="sentiment-badge">{ikon} Baskın duygu</div>
                    <div class="rc-icon-row"><span class="rc-label" style="color:{metin_renk}">{baslik}</span></div>
                    <div class="rc-conf">Model güveni %{yuzde}</div>
                  </div>
                </div>
                <div class="probability-list">{''.join(cubuklar)}</div>
                """, unsafe_allow_html=True)
                st.markdown('''<div style="padding:15px 2px 2px"><div class="card-title">Sonuç özeti</div><div class="card-note">Bu yorumun baskın tonu tekil duygu sınıflandırmasıyla belirlendi. Aşağıdan, kararı etkileyen ifadeleri inceleyebilirsin.</div></div>''', unsafe_allow_html=True)
                if karma_duygu_var:
                    st.markdown(
                        '<div class="confidence-note medium">'
                        '<strong>🔀 Karma duygular tespit edildi</strong>'
                        'Bu yorumda konuya göre farklı tonlar var — aşağıdaki '
                        '"Konu bazlı analiz" bölümünde ayrıştırılmış hâlini görebilirsin.'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(f'''<div class="confidence-note {guven_sinif}"><strong>{guven_baslik} · %{yuzde}</strong>{guven_aciklama}</div>''', unsafe_allow_html=True)
                kopyalanacak_sonuc = f"Duygu: {baslik}\nModel güveni: %{yuzde}\nYorum: {metin}"
                components.html(
                    f'''<button id="copy-result">Sonucu kopyala</button><span id="copy-note"></span>
                    <style>
                    body{{margin:0;background:transparent;font-family:system-ui,sans-serif}}
                    button{{height:38px;padding:0 14px;border:1px solid #d8ddec;border-radius:9px;background:#fff;color:#33405a;font-weight:650;cursor:pointer}}
                    button:hover{{border-color:#7770ff;color:#4f46e5}} #copy-note{{margin-left:9px;color:#159b6b;font-size:12px}}
                    @media(prefers-color-scheme:dark){{button{{background:#202940;color:#edf0f8;border-color:#3a4761}}}}
                    </style><script>
                    document.getElementById('copy-result').onclick=async()=>{{
                      const metin={json.dumps(kopyalanacak_sonuc)};
                      try {{
                        await window.parent.navigator.clipboard.writeText(metin);
                        document.getElementById('copy-note').textContent='Kopyalandı ✓';
                      }} catch (_) {{
                        document.getElementById('copy-note').textContent='Kopyalama izni gerekli';
                      }}
                    }};</script>''',
                    height=43,
                )
                st.markdown('<div class="feedback-title">Bu sonuç doğru mu?</div><div class="card-note">Yanlış tahminler, sonraki model eğitiminde kullanılabilecek ayrı bir düzeltme dosyasına kaydedilir.</div>', unsafe_allow_html=True)
                with st.form("geri_bildirim_formu"):
                    st.radio("Değerlendirmen", ["Doğru", "Yanlış"], horizontal=True, key="geri_bildirim_karar")
                    duzeltme_secenekleri = [etiket for etiket in ["olumlu", "nötr", "olumsuz"] if etiket != sonuc["etiket"]]
                    st.selectbox("Yanlışsa doğru sonuç", duzeltme_secenekleri, key="geri_bildirim_etiket")
                    st.form_submit_button(
                        "Geri bildirimi kaydet",
                        on_click=geri_bildirim_formunu_kaydet,
                        args=(metin, sonuc["etiket"], sonuc["guven"]),
                        use_container_width=True,
                    )

            st.markdown('<div id="analiz-detaylari"></div>', unsafe_allow_html=True)
            if "onemler" in kayitli_analiz:
                onemler = kayitli_analiz["onemler"]
            else:
                with st.spinner("Hangi kelimeler etkiledi hesaplanıyor..."):
                    onemler = kelime_onemleri(metin)
                kayitli_analiz["onemler"] = onemler
                st.session_state["tekil_analiz_verisi"] = kayitli_analiz
            en_yuksek = max((o["onem"] for o in onemler), default=0) or 1
            parcalar = []
            for o in onemler:
                yogunluk = max(o["onem"], 0) / en_yuksek
                kelime_html = html.escape(o["kelime"])
                if yogunluk > 0.25:
                    opaklik = 0.12 + 0.5 * yogunluk
                    parcalar.append(
                        f'<span class="k" style="background-color: rgba({rgb},{opaklik:.2f});">{kelime_html}</span>'
                    )
                else:
                    parcalar.append(kelime_html)
            vurgulu = " ".join(parcalar)
            with st.expander("Hangi kelimeler etkiledi?"):
                st.markdown(f"""
                <div class="vurgu-metin">{vurgulu}</div>
                <div class="vurgu-not">Koyu renk vurgulu kelimeler, modelin "{baslik.lower()}" kararını daha çok destekledi.</div>
                """, unsafe_allow_html=True)

            if konu_sonuclari:
                satirlar_html = []
                for k in konu_sonuclari:
                    k_renk, k_metin_renk, k_rgb, _, k_baslik = DURUM[k["etiket"]]
                    satirlar_html.append(
                        f'<div class="konu-satir">'
                        f'<span class="konu-ad">{html.escape(k["konu"])}</span>'
                        f'<span class="konu-parca">&quot;{html.escape(k["parca"])}&quot;</span>'
                        f'<span class="konu-pill" style="background:rgba({k_rgb},0.16); color:{k_metin_renk};">{k_baslik}</span>'
                        f'</div>'
                    )
                with st.expander("Konu bazlı analiz", expanded=karma_duygu_var):
                    st.markdown(f"""
                    <div class="konu-liste">{''.join(satirlar_html)}</div>
                    <div class="vurgu-not">Yorum, bağlaçlara ve noktalama işaretlerine göre bölünerek konu geçen parçalar ayrı değerlendirilir.</div>
                    """, unsafe_allow_html=True)

            components.html(
                """
                <script>
                  const kaydir = () => {
                    const doc = window.parent.document;
                    const hedef = doc.getElementById('analiz-detaylari');
                    const anaPanel = doc.querySelector('section.main') || doc.querySelector('[data-testid="stMain"]');
                    if (hedef) {
                      hedef.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    } else if (anaPanel) {
                      anaPanel.scrollTo({ top: anaPanel.scrollHeight, behavior: 'smooth' });
                    }
                  };
                  setTimeout(kaydir, 350);
                  setTimeout(kaydir, 1000);
                </script>
                """,
                height=0,
            )
        else:
            st.warning("Lütfen bir yorum gir.")

with sekme2:
    toplu_tiklandi = False
    with st.container(border=True):
        st.markdown('''<div class="upload-head"><div class="upload-icon">↑</div><div><div class="card-title">Yorum dosyanı yükle</div><div class="card-note">CSV, Excel (.xlsx) veya JSON dosyanı analiz edebilirsin. Dosyada <strong style="color:var(--text-primary)">yorum</strong> adlı bir sütun bulunmalı.</div></div></div>''', unsafe_allow_html=True)
        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        dosya_anahtari = f"yorum_dosyasi_{st.session_state.get('dosya_yukleyici_no', 0)}"
        dosya = st.file_uploader("Dosya", type=["csv", "xlsx", "json"], key=dosya_anahtari, label_visibility="collapsed")
        # st.file_uploader'ın "Upload" butonu ve "200MB per file • CSV, XLSX,
        # JSON" alt yazısı Streamlit'in kendi yerleşik metni — resmi bir
        # çeviri/i18n API'si yok, bu yüzden uygulamanın geri kalanı %100
        # Türkçeyken bu iki metin İngilizce kalıyordu. Aynı sayfada zaten
        # kullanılan teknikle (bkz. "Sonucu kopyala" ve tablo filtresi)
        # DOM'a JS ile müdahale edip Türkçeleştiriyoruz. Sadece BEKLENEN
        # İngilizce metinle TAM eşleşirse değiştiriyor — Streamlit ileride
        # metni değiştirirse sessizce hiçbir şey yapmaz, yanlış bir yeri
        # bozmaz. MutationObserver, dosya seçilip yükleyici yeniden
        # render olduğunda da çalışmaya devam etmesini sağlıyor.
        components.html(
            """<script>
            const turkcelestir = () => {
              const kok = window.parent.document;
              kok.querySelectorAll('[data-testid="stFileUploaderDropzoneInstructions"] span').forEach(el => {
                if (el.textContent.trim() === '200MB per file \\u2022 CSV, XLSX, JSON') {
                  el.textContent = '200MB\\'a kadar \\u2022 CSV, XLSX, JSON';
                }
              });
              kok.querySelectorAll('[data-testid="stFileUploaderDropzone"] button p').forEach(el => {
                if (el.textContent.trim() === 'Upload') { el.textContent = 'Dosya seç'; }
                if (el.textContent.trim() === 'Browse files') { el.textContent = 'Dosya seç'; }
              });
            };
            turkcelestir();
            new MutationObserver(turkcelestir).observe(window.parent.document.body, { childList: true, subtree: true });
            </script>""",
            height=0,
        )
        if dosya is None:
            st.caption("↑ Analize başlamak için önce bir dosya seç.")

    df = None
    if dosya is not None:
        uzanti = dosya.name.lower().rsplit(".", 1)[-1]
        try:
            if uzanti == "csv":
                df = pd.read_csv(dosya)
            elif uzanti == "xlsx":
                df = pd.read_excel(dosya)
            elif uzanti == "json":
                veri = json.load(dosya)
                if isinstance(veri, list) and veri and isinstance(veri[0], str):
                    df = pd.DataFrame({"yorum": veri})
                else:
                    df = pd.DataFrame(veri)
        except Exception as e:
            st.error(f"Dosya okunamadı: {e}")

    if df is not None:
        if "yorum" not in df.columns:
            st.error("Dosyada 'yorum' adında bir sütun/alan bulunamadı.")
        else:
            onceki_satir_sayisi = len(df)
            df = df[df["yorum"].notna()].copy()
            df["yorum"] = df["yorum"].astype(str).str.strip()
            df = df[df["yorum"] != ""].reset_index(drop=True)
            atlanan = onceki_satir_sayisi - len(df)
            if atlanan:
                st.info(f"{atlanan} boş yorum satırı otomatik olarak atlandı.")

            if df.empty:
                st.warning("Dosyada analiz edilebilecek dolu bir yorum bulunamadı.")
            else:
                st.caption(f"✓ Toplam {len(df)} geçerli yorum analize hazır.")
                toplu_analiz_dugmesi, yeni_dosya_dugmesi = st.columns([1.7, 1], gap="small")
                with toplu_analiz_dugmesi:
                    toplu_tiklandi = st.button("Toplu Analiz Yap", type="primary", use_container_width=True)
                with yeni_dosya_dugmesi:
                    st.button("↻ Yeni analiz", type="secondary", on_click=yeni_dosya_analizi_baslat, use_container_width=True)

        if "yorum" in df.columns and not df.empty and toplu_tiklandi:
            toplu_durum = st.empty()
            toplu_durum.markdown(
                '<div class="analysis-progress"><span></span>Dosya hazırlanıyor ve model yükleniyor...</div>',
                unsafe_allow_html=True,
            )
            ilerleme = st.progress(0, text=f"0/{len(df)} yorum işlendi...")

            def _ilerleme_guncelle(islenen, toplam_yorum):
                toplu_durum.markdown(
                    f'<div class="analysis-progress"><span></span>Yorumlar analiz ediliyor: {islenen}/{toplam_yorum}</div>',
                    unsafe_allow_html=True,
                )
                ilerleme.progress(islenen / toplam_yorum, text=f"{islenen}/{toplam_yorum} yorum işlendi...")

            sonuclar = toplu_analiz(df["yorum"].astype(str).tolist(), ilerleme_callback=_ilerleme_guncelle)
            ilerleme.empty()
            toplu_durum.markdown(
                f'<div class="analysis-complete"><span>✓</span>Analiz tamamlandı · {len(sonuclar)} yorum işlendi</div>',
                unsafe_allow_html=True,
            )
            sonuc_df = pd.DataFrame(sonuclar)
            st.session_state["toplu_analiz_sonuclari"] = sonuclar

            toplam = len(sonuc_df)
            olumlu_sayi = int((sonuc_df["etiket"] == "olumlu").sum())
            notr_sayi = int((sonuc_df["etiket"] == "nötr").sum())
            olumsuz_sayi = int((sonuc_df["etiket"] == "olumsuz").sum())
            ort_guven = round(sonuc_df["guven"].mean() * 100, 1) if toplam else 0.0

            st.markdown('<div id="toplu-analiz-sonuclari"></div>', unsafe_allow_html=True)
            st.markdown('<div class="card-title" style="font-size:16px;margin:24px 0 10px">Analiz özeti</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="stat-grid">
              <div class="stat-tile"><div class="label">Toplam yorum</div><div class="value">{toplam}</div></div>
              <div class="stat-tile"><div class="label">Olumlu</div><div class="value" style="color:var(--good)">{olumlu_sayi}</div></div>
              <div class="stat-tile"><div class="label">Nötr</div><div class="value" style="color:var(--neutral-text)">{notr_sayi}</div></div>
              <div class="stat-tile"><div class="label">Olumsuz</div><div class="value" style="color:var(--critical)">{olumsuz_sayi}</div></div>
              <div class="stat-tile"><div class="label">Ort. güven</div><div class="value">%{ort_guven}</div></div>
            </div>
            """, unsafe_allow_html=True)

            dagilim_df = pd.DataFrame({
                "etiket": ["Olumlu", "Nötr", "Olumsuz"],
                "adet": [olumlu_sayi, notr_sayi, olumsuz_sayi],
            })
            taban = (
                alt.Chart(dagilim_df)
                .mark_bar(cornerRadiusEnd=4, size=24)
                .encode(
                    y=alt.Y("etiket:N", title=None, sort=["Olumlu", "Nötr", "Olumsuz"],
                            axis=alt.Axis(labelColor="#898781", domain=False, ticks=False, labelFontSize=13)),
                    x=alt.X("adet:Q", title=None,
                            axis=alt.Axis(labelColor="#898781", gridColor="#e1e0d9", domainColor="#e1e0d9",
                                           tickColor="#e1e0d9", tickMinStep=1, format="d")),
                    color=alt.Color("etiket:N",
                                     scale=alt.Scale(domain=["Olumlu", "Nötr", "Olumsuz"],
                                                      range=["#0ca30c", "#fab219", "#d03b3b"]),
                                     legend=None),
                )
            )
            etiketler = taban.mark_text(align="left", dx=6, color="#52514e", fontWeight=600, fontSize=13).encode(text="adet:Q")
            st.altair_chart((taban + etiketler).properties(height=170, background="transparent"), use_container_width=True)

            with st.container(border=True):
                st.markdown('<div class="card-title">Detaylı sonuçlar</div>', unsafe_allow_html=True)
                goruntu_df = sonuc_df.rename(columns={"metin": "Yorum", "etiket": "Sonuç", "guven": "Güven"})
                goruntu_df["Güven"] = goruntu_df["Güven"].map(lambda g: f"%{round(g * 100, 1)}")
                if karanlik_mod:
                    filtre_stili = '<style>:root{--filter-bg:#11182a;--filter-text:#edf0f8;--filter-border:#3a4761;--filter-placeholder:#8995ab}</style>'
                else:
                    filtre_stili = '<style>:root{--filter-bg:#fff;--filter-text:#33405a;--filter-border:#d8ddec;--filter-placeholder:#8a94a9}</style>'
                # Tabloya her render'da benzersiz bir id veriliyor. Önceden
                # filtre script'i "sayfadaki .results-table sınıfına sahip
                # SON eleman" mantığıyla çalışıyordu — birden fazla analiz
                # art arda çalıştırılırsa (veya DOM'da eski bir kopya
                # kalırsa) yanlış tabloyu hedefleme riski vardı.
                # getElementById ile tam olarak bu render'a ait tabloyu
                # hedefliyoruz, tahmine dayalı seçim yok.
                st.session_state["tablo_sayaci"] = st.session_state.get("tablo_sayaci", 0) + 1
                tablo_id = f"results-table-{st.session_state['tablo_sayaci']}"
                components.html(
                    filtre_stili + '''<div class="filters"><input id="search" type="search" placeholder="Yorumlarda ara…"><select id="sentiment"><option value="">Tüm duygular</option><option value="olumlu">Olumlu</option><option value="nötr">Nötr</option><option value="olumsuz">Olumsuz</option></select></div>
                    <style>body{margin:0;background:transparent;font-family:system-ui,sans-serif}.filters{display:flex;gap:9px;padding:3px 0}input,select{height:39px;border:1px solid var(--filter-border);border-radius:9px;background:var(--filter-bg);color:var(--filter-text);padding:0 11px;font-size:13px}input::placeholder{color:var(--filter-placeholder)}input{flex:1;min-width:0}select{width:145px}</style>
                    <script>
                    const tabloId = ''' + json.dumps(tablo_id) + ''';
                    const filterRows=()=>{const table=window.parent.document.getElementById(tabloId);if(!table)return;const q=document.getElementById('search').value.toLocaleLowerCase('tr');const s=document.getElementById('sentiment').value;table.querySelectorAll('tbody tr').forEach(row=>{const text=row.cells[0].innerText.toLocaleLowerCase('tr');const label=row.cells[1].innerText.toLocaleLowerCase('tr');row.style.display=text.includes(q)&&(!s||label===s)?'':'none';});};
                    document.getElementById('search').addEventListener('input',filterRows);document.getElementById('sentiment').addEventListener('change',filterRows);
                    </script>''',
                    height=47,
                )
                tablo_satirlari = []
                for _, tablo_satiri in goruntu_df.iterrows():
                    tablo_etiket = str(tablo_satiri["Sonuç"])
                    css_etiket = "notr" if tablo_etiket == "nötr" else tablo_etiket
                    tablo_satirlari.append(
                        f'<tr><td>{html.escape(str(tablo_satiri["Yorum"]))}</td>'
                        f'<td><span class="table-sentiment {css_etiket}">{html.escape(tablo_etiket.capitalize())}</span></td>'
                        f'<td><span class="table-confidence">{html.escape(str(tablo_satiri["Güven"]))}</span></td></tr>'
                    )
                st.markdown(
                    f'<div class="results-table-wrap"><table class="results-table" id="{tablo_id}">'
                    '<thead><tr><th>Yorum</th><th>Sonuç</th><th>Güven</th></tr></thead>'
                    f'<tbody>{"".join(tablo_satirlari)}</tbody></table></div>',
                    unsafe_allow_html=True,
                )

                csv_verisi = goruntu_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "CSV olarak indir",
                    data=csv_verisi,
                    file_name="duygu_analizi_sonuclari.csv",
                    mime="text/csv",
                )
                pdf_verisi = pdf_raporu_olustur(toplam, olumlu_sayi, notr_sayi, olumsuz_sayi, ort_guven, sonuc_df)
                st.download_button(
                    "PDF özet raporu indir",
                    data=pdf_verisi,
                    file_name="duygu_analizi_raporu.pdf",
                    mime="application/pdf",
                )

            components.html(
                """
                <script>
                  const kaydir = () => {
                    const doc = window.parent.document;
                    const hedef = doc.getElementById('toplu-analiz-sonuclari');
                    if (!hedef) return;
                    hedef.scrollIntoView({ behavior: 'smooth', block: 'start' });

                    // Streamlit sürümlerinde kaydırılabilir alan farklı bir kapsayıcı olabilir.
                    const kapsayicilar = [
                      doc.querySelector('section.main'),
                      doc.querySelector('[data-testid="stMain"]'),
                      doc.querySelector('[data-testid="stAppViewContainer"]')
                    ].filter(Boolean);
                    for (const kapsayici of kapsayicilar) {
                      const fark = hedef.getBoundingClientRect().top - kapsayici.getBoundingClientRect().top;
                      if (Math.abs(fark) > 8) kapsayici.scrollBy({ top: fark - 20, behavior: 'smooth' });
                    }
                  };
                  setTimeout(kaydir, 300);
                  setTimeout(kaydir, 1100);
                  setTimeout(kaydir, 2000);
                </script>
                """,
                height=0,
            )

st.markdown(
    f'''<div class="app-footer">
      <span>Yorum Pusulası · Türkçe müşteri yorumları için 3 sınıflı duygu analizi</span>
      <span>Aktif model: {html.escape(aktif_model_adi())}</span>
    </div>''',
    unsafe_allow_html=True,
)
