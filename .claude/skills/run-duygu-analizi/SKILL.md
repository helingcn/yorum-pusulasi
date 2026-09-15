---
name: run-duygu-analizi
description: Build, launch, and drive the Türkçe Duygu Analizi Streamlit app (3-class olumlu/nötr/olumsuz sentiment classifier). Use when asked to run, start, test, or screenshot this project, or verify a change works in the running app.
---

# Run: Türkçe Duygu Analizi (Streamlit + BERT)

Paths below are relative to the project root (`duygu-analizi-projesi/`),
not to this skill directory.

This is a Streamlit web app (`app.py`) backed by a HuggingFace BERT
sentiment pipeline (`sentiment.py`). `chromium-cli` is not installed in
this environment, so the agent path is a small bundled Playwright
driver (`driver.mjs`) instead.

## Prerequisites

- Python 3 (verified with 3.14 — no compatibility issues found).
- Node.js + npm (for the Playwright driver only — not a runtime dep of
  the app itself).

## Build / Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

The driver's own dependency (Playwright) lives in this skill dir and is
already installed:

```bash
cd .claude/skills/run-duygu-analizi && npm install   # already done; re-run if node_modules is missing
npx playwright install chromium                       # already done; browser cached in ~/Library/Caches/ms-playwright
```

## Run (agent path)

1. Start the app in the background and wait for the port:

```bash
source venv/bin/activate
streamlit run app.py --server.headless true --server.port 8501 &
i=0; until curl -sf http://localhost:8501 >/dev/null || [ $i -ge 30 ]; do sleep 1; i=$((i+1)); done
```

(`timeout` isn't available by default on macOS — the loop above works
on both macOS and Linux.)

The app loads `./duygu_finetuned_v3` if present (the fine-tuned production
model, ~1.1GB, built by `finetune3.py` — see the fine-tuning gotcha below).
If that folder is missing, `sentiment.py` falls back to downloading the base
`cardiffnlp/twitter-xlm-roberta-base-sentiment` (~1.1GB, one-time, cached in
`~/.cache/huggingface`) — this is an XLM-RoBERTa model, its tokenizer needs
the `sentencepiece` package, already in `requirements.txt`.

2. Drive it and take screenshots:

```bash
cd .claude/skills/run-duygu-analizi
node driver.mjs all      # or: single | batch
```

Screenshots land in `.claude/skills/run-duygu-analizi/screenshots/`
(`single.png`, `batch.png`). The script also prints `CONSOLE_ERRORS:` —
check it's `[]`.

3. Stop the server when done:

```bash
lsof -ti:8501 -sTCP:LISTEN | xargs -r kill
```

## Run (human path)

```bash
source venv/bin/activate
streamlit run app.py
```

Opens in the browser automatically. Use the "Tek Yorum" tab for a
single comment, or "Toplu Analiz" to upload `ornek_yorumlar.csv` (or your
own CSV/Excel/JSON — must have a `yorum` column/field).

## Direct invocation (no web UI)

For changes confined to `sentiment.py`, skip Streamlit entirely:

```bash
source venv/bin/activate
python sentiment.py
```

Runs `toplu_analiz` over 3 built-in example comments and prints
label + confidence — the fastest smoke test for model/logic changes.

## Fine-tuning

`./duygu_finetuned_v3` (the production model) was built by:

```bash
source venv/bin/activate
python finetune3.py     # took 29.5 min and 25.5 min (round 2) on separate
                         # runs when the machine was otherwise idle; round 1
                         # took 428 min once when other load was competing —
                         # don't assume the fast number, monitor it
```

Trains from the original `cardiffnlp/twitter-xlm-roberta-base-sentiment`
(not from an already-fine-tuned checkpoint) on 6000 negative + 6000 positive
from `maydogan/Turkish_SentimentAnalysis_TRSAv1`, plus a neutral class made
of 4500 real TRSAv1 examples + 1500 synthetic template-generated "procedural
neutral" sentences (`sentetik_notr.py` — see the gotcha below on why).
Holds out 150 real TRSAv1 examples/class to `./trsav1_held_out.json` for
evaluation (same seed as round 2, so the held-out set is identical — a fair
v2-vs-v3 comparison), and saves only the final model (`save_strategy="no"`
— no checkpoint accumulation). Needs `accelerate` (in `requirements.txt`).

**Before trusting a new fine-tune, evaluate on both benchmarks** — see the
gotcha below on why winvoker alone is misleading:

```bash
python evaluate.py --model ./duygu_finetuned_v3          # vs. winvoker (Wikipedia neutral)
python evaluate_trsav1.py --model ./duygu_finetuned_v3   # vs. TRSAv1 (real neutral) — the one that matters
```

`finetune.py` (round 1, produced the abandoned `./duygu_finetuned`) and
`finetune2.py` (round 2, produced the abandoned `./duygu_finetuned_v2`) are
kept in the repo as a record of what was tried and why it wasn't enough —
see the Gotchas entries below before reusing either approach.

## Test

```bash
source venv/bin/activate
pytest test_sentiment.py -v
```

15 tests, real model (no mocking) — covers `analiz_et`, `toplu_analiz`,
`kelime_onemleri`, `ETIKET_MAP`. ~6-7s once the model is warm (lru_cache).
Verified live that these actually catch regressions: deliberately corrupted
`ETIKET_MAP["positive"]` and confirmed exactly the 2 expected tests failed,
the other 13 stayed green — not just tests that trivially pass.

## Gotchas

- **`st.markdown` with a multi-line, indentation-heavy f-string silently
  renders as a literal code block instead of HTML — verified live while
  building `konu_analizi`'s UI.** Building each `<div class="konu-satir">`
  row as a multi-line triple-quoted f-string (readable in the Python source,
  each line indented to match the surrounding `for`/`if` nesting) produced a
  page where the *first* row rendered fine but subsequent rows showed up as
  raw HTML text. Cause: each line of a multi-line triple-quoted string
  keeps the Python source's leading whitespace verbatim, and CommonMark
  treats 4+ leading spaces as an indented code block — deeply-nested Python
  code trivially exceeds that. Fixed by building each row as a **single-line**
  string (concatenated f-strings, no embedded newlines), matching the
  pattern already used for `kelime_onemleri`'s word-highlight spans (which
  never hit this because it was already single-line). **Rule of thumb: any
  HTML fragment built inside a loop for `st.markdown(unsafe_allow_html=True)`
  must be single-line, or built with `textwrap.dedent`/no leading whitespace
  — never a triple-quoted string indented to match surrounding code.**
- **`konu_analizi` (aspect-based breakdown, "Tek Yorum" tab only) is rule-based,
  not a trained ABSA model — no new data or training involved.** Splits the
  comment on `ama/fakat/ancak/lakin` and commas, keyword-matches each clause
  against `KONU_SOZLUGU` (kargo/kalite/fiyat/beden/renk/müşteri hizmetleri),
  and runs the existing `analiz_et` on each matched clause independently.
  Verified live on the motivating case: "Kargo hızlıydı ama kalite kötüydü,
  fiyatı da pahalıydı." → kargo: nötr, kalite: olumsuz (0.94), fiyat: olumsuz
  (0.63) — correctly separates mixed-sentiment clauses. **But it inherits
  the base model's unreliability on very short, low-context clauses**: "Beden
  tam oturdu, renk de fotoğraftaki gibiydi." → beden classified **olumsuz
  (0.886)**, even though "the size fit perfectly" is clearly positive — same
  family of issue as the other single-clause/short-phrase gotchas above, not
  a bug in the splitting/keyword logic itself. Returns `[]` when no aspect
  keyword matches (e.g. "Harika bir ürün, çok memnun kaldım!" — no specific
  topic mentioned) — `app.py` only renders the card when the list is
  non-empty. `KONU_SOZLUGU` is a fixed, hand-written keyword list, not
  exhaustive — topics outside it (e.g. bare "ürün" without a more specific
  word) are silently not detected.
- **`toplu_analiz` now chunks manually (`BATCH_BOYUTU=16`) instead of handing
  the whole list to the pipeline at once**, specifically so `app.py` can show
  a real progress bar (`st.progress`, "47/200 yorum işlendi...") instead of a
  static spinner. Same speed characteristic as before (batching per 16 is
  what the pipeline was doing internally anyway). If you need the progress
  bar to feel meaningful, remember typical batches finish in a couple of
  seconds on this hardware — for a 200-row file it's fast enough that the
  bar may flash through quickly rather than crawl; that's correct, not a
  bug. `ilerleme_callback(islenen, toplam)` is optional and backward
  compatible — omitted, `toplu_analiz` behaves exactly as before.
- **"şaşırdım" (I was surprised) is ambiguous to the model, and how much
  positive emphasis is needed to overcome it is inconsistent — confirmed on
  both the base model and v3, not fixed by fine-tuning.** First found
  pre-fine-tuning: "Beklentimin çok üzerinde bir kalite, gerçekten çok
  şaşırdım." → olumsuz — `kelime_onemleri` showed "şaşırdım" carrying almost
  the entire decision, while "Kalite harikaydı, çok etkilendim." (swap
  "şaşırdım" for "etkilendim") → olumlu 0.94. Re-confirmed live on v3 with a
  shorter, plainer phrasing of the same pattern: "beklentimin üzerinde bir
  çanta çıktı, şaşırdım." → **olumsuz 0.746** (found by the user testing
  manually, not by us). Isolated further:

  | phrasing | result |
  |---|---|
  | "...çanta çıktı, şaşırdım" | olumsuz 0.746 |
  | "...çok üzerinde...gerçekten çok şaşırdım" | olumlu 0.705 |
  | "...çanta çıktı" (no "şaşırdım") | olumlu 0.830 |
  | "...çanta çıktı, çok memnun kaldım" (swap "şaşırdım") | olumlu 0.965 |

  So it's not simply "şaşırdım = negative" — a *sufficiently emphasized*
  positive clause ("çok üzerinde," "gerçekten çok") can still overcome it,
  but a plainer one can't, and the threshold isn't predictable from reading
  the sentence. Same family as "fatura"/"aynı"/procedural-neutral (a single
  word's real-world usage skew overriding compositional meaning) but this
  one is a genuine borderline case rather than a clear-cut miss — expect it
  to resurface in slightly different phrasings; not chased further for the
  same cost/benefit reasons as "fatura."
- **"fatura" (invoice) carries a strong negative bias baked into TRSAv1
  itself — "use more training data" would NOT fix this, verified before
  attempting it.** "kutunun içinde fatura vardı" ("there was an invoice in
  the box" — neutral/factual) → olumsuz 0.853; `kelime_onemleri` shows
  "fatura" alone contributes +0.853 (basically the whole decision). Isolated
  further: "fatura vardı" alone → olumsuz 0.871, and the bias isn't really
  about "fatura" specifically vs. the "kutunun içinde X vardı" template —
  swap in "hediye" (gift) and it's *still* olumsuz 0.796. Before assuming
  "train on more of TRSAv1" would fix it, checked the full 150K dataset
  directly: sentences containing "fatura" split **72 Negative / 7 Positive /
  7 Neutral** — an 84%-negative skew that exists in the *source data itself*,
  not an artifact of the 6000/class training subsample. (For comparison,
  "vardı" alone across the full dataset is well-balanced: 238/196/147 — so
  this is specific to "fatura," not the sentence template.) Pulling from
  more of TRSAv1 would reproduce the same ~84% skew, not dilute it.
  Reflects a real property of the corpus (people who mention "fatura" in a
  Turkish product review usually *are* complaining about it — missing,
  wrong, etc.) that the model over-generalized from. **Deliberately not
  fixed**: the only real fix (oversampling the ~14 unique counter-examples
  that exist across the whole dataset, or sourcing a different dataset) has
  bad cost/benefit — 14 examples repeated risks the model memorizing those
  specific sentences rather than generalizing, and even a successful fix
  only patches this one word; nothing suggests the underlying problem
  (surface lexical correlations learned from real-world-skewed word usage)
  is scoped to just "fatura" and "aynı" — those were found by manually
  testing specific sentences, not a systematic search, so more probably
  exist undiscovered. Accepted as a known limitation rather than chased.
- **v2 misclassified some real neutral sentences — "aynı" (same) carried
  a learned negative bias. Fixed in v3, but not the way you'd expect —
  the aggregate metric barely moved even though the specific bug did.**
  Verified live on v2: "Renk fotoğraftakiyle aynı." → olumsuz 0.724, and
  `kelime_onemleri` showed "aynı." alone carrying +0.724 importance
  (essentially the whole decision). Further testing found this wasn't
  isolated to "aynı" — it was one instance of a broader pattern: any bare
  procedural/transactional statement ("sipariş verildi," "kutunun içinde X
  vardı," "fatura") gets pulled negative, because in real reviews these
  phrases are usually the *lead-in to a complaint* ("sipariş verildi ama
  hâlâ gelmedi"), and standalone neutral procedural reviews (no complaint
  attached) are inherently rare in any review corpus — people who bother to
  write a review usually have an opinion. Confirmed the pattern generalizes
  regardless of specific noun/color: "M beden olarak sipariş verildi." →
  olumsuz 0.976 even with no product/color mentioned at all.

  **The fix that worked:** `sentetik_notr.py` template-generates diverse
  synthetic sentences covering this exact pattern (order status, box
  contents, color/size confirmation, tracking info — ~20 templates ×
  vocab substitution, ~1300 unique combinations) and mixes 1500 of them
  into v3's neutral training class (alongside 4500 real TRSAv1 neutral).
  Verified live: all of "Ürün siyah renkte, M beden olarak sipariş
  verildi.", "Kargo takip numarası SMS ile gönderildi.", "Kutunun içinde
  fatura da vardı.", "Rengi tam fotoğraftakiyle aynıydı." now classify
  nötr at 94.8–99.6% confidence with v3 — a decisive, unambiguous fix for
  this exact failure mode.

  **But `evaluate_trsav1.py`'s aggregate neutral recall barely changed**
  (v2 66.7% → v3 64.0%, a ~4-example swing on n=150, within sampling
  noise) — because TRSAv1's held-out neutral examples are mostly *hedged
  opinion* ("fena değil ama...", "cilt tipine göre değişebilir"), not bare
  procedural statements, so fixing the procedural pattern didn't move the
  metric that's dominated by a different kind of difficulty. Both things
  are true at once: a real, verified bug fix, and a benchmark that doesn't
  reward it much because it wasn't testing for that specific failure mode.
  **Lesson: a metric moving (or not) doesn't tell you whether a specific,
  verified bug got fixed — check the specific case directly, don't infer
  it from the aggregate number alone.** v3 still won on overall accuracy on
  both benchmarks (73.2% vs 70.0% winvoker; 81.6% vs 81.3% TRSAv1), which
  is why it's in production, but that aggregate win is a separate fact
  from the procedural-neutral fix, not evidence for it.
- **A benchmark that scored great (91.8%) turned out to be measuring the
  wrong thing — verified two ways before trusting it.** Round 1 fine-tuning
  (`finetune.py` → `./duygu_finetuned`, no longer in the repo) oversampled
  negative examples and used winvoker's "Notr" class for neutral — but ALL
  of winvoker's neutral examples are Wikipedia sentences (see the neutral-
  detection gotcha below), not product reviews. `evaluate.py` (which also
  samples neutral from winvoker) scored this model at 91.8% overall, 100%
  neutral recall — but neutral recall on 450 *real* product-review examples
  (`evaluate_trsav1.py`, held-out from `maydogan/Turkish_SentimentAnalysis_TRSAv1`,
  real e-commerce reviews) was **0.7%** — worse than the un-fine-tuned base
  model (13.3%). The training had taught the model "Wikipedia-style sentence
  → neutral," which doesn't generalize to short factual e-commerce sentences
  ("Ürün bugün kargoya verildi.") — round 1 made real-world neutral detection
  *worse* while looking like a huge win on the metric everyone was watching.
  Round 2 (`finetune2.py` → `./duygu_finetuned_v2`, superseded by v3) retrained
  from the original base (not continued from round 1) with a **balanced**
  6000/6000/6000 split using TRSAv1 for all three classes — real
  product-review text for neutral too, no domain mismatch. Round 3
  (`finetune3.py` → `./duygu_finetuned_v3`, **current production**) kept v2's
  positive/negative data and added 1500 synthetic procedural-neutral
  sentences to the neutral class (see the "aynı"/procedural-neutral gotcha
  above). Result on the same two benchmarks:

  | | winvoker (Wikipedia neutral) | TRSAv1 (real neutral) |
  |---|---|---|
  | base model | 74.4% | 63.6% |
  | v1 (round 1) | 91.8% | 63.1% (neutral recall 0.7%) |
  | v2 (round 2) | 70.0% | 81.3% (neutral recall 66.7%) |
  | v3 (round 3, **production**) | **73.2%** | **81.6%** (neutral recall 64.0%) |

  **Lesson: when a fine-tune's eval set is sampled from the same source as
  its training data's weak spot, a great score can mean "learned the eval
  set's quirks," not "learned the task."** Always check against a second,
  independently-sourced eval set before trusting a big jump — `evaluate_trsav1.py`
  exists specifically for this ("does it work on real product reviews," not
  just "does it beat winvoker"). If ever fine-tuning again, prefer TRSAv1 (or
  another real-product-review source) for every class, not just the one
  that's convenient.
- **"Toplu Analiz" tab accepts CSV, Excel (.xlsx), and JSON**, not just CSV —
  the tab was renamed from "Toplu Analiz (CSV)" accordingly (drive it via
  `getByRole('tab', { name: 'Toplu Analiz' })`, the old CSV-suffixed name no
  longer matches). Needs `openpyxl` in `requirements.txt` for
  `pd.read_excel` — without it, `.xlsx` uploads fail with an import error
  surfaced as `st.error(f"Dosya okunamadı: {e}")`. JSON accepts either a list
  of `{"yorum": "..."}` objects or a plain list of strings (auto-detected:
  `isinstance(veri[0], str)`); verified all three formats live end-to-end
  (upload → analyze → results table), no console errors.
- **`toplu_analiz` batches instead of looping.** Passes the whole list to the
  pipeline (`model(metinler, batch_size=16)`) instead of calling `analiz_et`
  once per row. Verified live on the same 500-example set used elsewhere:
  1.38x faster (7.1s → 5.1s), **zero label changes**, max confidence-score
  drift 0.000002 (floating-point batching/padding noise, invisible at the
  displayed 1-decimal precision). Safe, measured, not a behavior change.
- **"Tek Yorum" uses `st.chat_input`, not `st.text_area` + a submit button.**
  Deliberate swap: the design needed Enter-to-submit with Shift+Enter for a
  literal newline, which `st.text_area` cannot do — Enter always inserts a
  newline in a textarea, no Streamlit/HTML API changes that. First attempt
  was a JS hack injected via `components.html` that intercepted `keydown` on
  the textarea and called `.click()` (and, when that failed, a full
  `pointerdown/mousedown/pointerup/mouseup/click` dispatch sequence) on the
  "Analiz Et" button — **verified live that neither works**: Streamlit's
  React button never fires its handler for a programmatic/synthetic click,
  only for a real trusted click (confirmed: Playwright's own `.click()` on
  the button always worked fine; only page-JS-dispatched synthetic events
  didn't). `st.chat_input` solves this natively — Enter submits, Shift+Enter
  inserts a newline, no hacks — and it renders fine nested inside
  `st.tabs()` + `st.container(border=True)` despite chat_input's usual
  page-bottom-docking reputation elsewhere. Drive it via
  `[data-testid="stChatInputTextArea"]` + `page.keyboard.press('Enter')`,
  not `getByRole('button', { name: 'Analiz Et' })` — that button no longer
  exists.
- **`kelime_onemleri` (word-importance highlighting, "Tek Yorum" tab only) does
  N+1 model forward passes** (leave-one-word-out occlusion — remove each word,
  re-run the model, measure the confidence drop). For a ~10-15 word review
  that's ~1-3s extra on CPU, acceptable for one comment. It is deliberately
  **not** wired into the batch/CSV tab — doing this per row across a few
  hundred rows would multiply analysis time by roughly the average word count
  and make batch analysis painfully slow. If batch explainability is ever
  wanted, sample a few rows rather than running it on every row.
- **Removing a word can break Turkish grammar and produce a false-positive
  highlight.** Verified live: in "...bu satıcıdan alışveriş yapmam", deleting
  "alışveriş" leaves "...bu satıcıdan yapmam" — grammatically incomplete (the
  object of "yapmam" is gone) — which alone dropped model confidence from
  0.933 to 0.848 (0.086 importance), enough to get highlighted even though
  "alışveriş" carries no sentiment itself. The real signal word in that
  sentence ("berbat") scored 0.484 — 5.6x higher. Fixed by raising the
  highlight threshold in `app.py` from `yogunluk > 0.12` to `> 0.25`, which
  cuts this class of grammar-artifact noise while keeping real signal words
  (verified: "beğendim." in a different sentence still highlights fine at the
  new threshold). This is an inherent limitation of leave-one-word-out
  occlusion, not fully fixable by threshold tuning alone — a lower threshold
  will surface more of these grammar artifacts again.
- **A blanket custom `font-family` on `[class*="st-emotion-cache"]` breaks
  Streamlit's icon-font glyphs.** `app.py` imports Inter and applies it broadly
  to override Streamlit's default sans; the file-uploader's "Add files" `+`
  button is a `[data-testid="stIconMaterial"]` span whose text content (`add`)
  is a ligature rendered by a Material Symbols icon font — the broad selector
  clobbered it, so the literal word "add" appeared next to the file chip
  instead of a `+` glyph. Fixed by excluding that testid:
  `[class*="st-emotion-cache"]:not([data-testid="stIconMaterial"])`. If you add
  more custom fonts/global type overrides later, check the uploader's `+`
  button and any other icon-font spots after.
- **Streamlit scrolls inside `[data-testid="stMain"]`, not `<body>`.** A default
  920px viewport clips the "Detaylı sonuçlar" table out of both a plain and a
  `fullPage: true` screenshot (`document.body.scrollHeight` reports `0` — the
  scrollable element is `stMain`, not `body`). The driver opens the page with a
  1600px-tall viewport to sidestep this instead of scrolling+stitching.
- **`st.markdown('<div class="card">...')` then later `st.markdown('</div>')`
  does NOT wrap the Streamlit widgets in between** — each `st.markdown` call is
  its own DOM node and the browser auto-closes the dangling `<div>` immediately,
  so the "card" background never actually encloses the widget. Use
  `st.container(border=True)` (styled via the `[data-testid="stVerticalBlockBorderWrapper"]`
  CSS rule in `app.py`) for any card that needs to contain real widgets; raw
  `st.markdown(...)` divs are fine only when the entire card's content is HTML
  written in a single call (e.g. the result card, stat tiles).
- **Neutral detection is real but uneven.** The model (`cardiffnlp/twitter-xlm-roberta-base-sentiment`,
  3-class: positive/neutral/negative) correctly labels purely factual
  Turkish sentences as **nötr** (e.g. "Ürün bugün kargoya verildi." →
  nötr 0.83, "Renk fotoğraftakiyle aynı." → nötr 0.59). But ambivalent
  "backhanded compliment" phrasing still gets pulled to a polarity
  instead of nötr — e.g. "Fiyatına göre fena değil, idare eder." →
  **olumlu (0.73)**, "Ortalama bir ürün, ne iyi ne kötü." → **olumsuz
  (0.63)** — even though a human would call both neutral. This was
  verified live before integrating; it's a real model limitation, not
  a wiring bug. Don't "fix" it by adding a confidence-threshold hack
  on top — that was the rejected alternative approach.
- **The model was highly sensitive to sentence-initial capitalization — fixed
  by lowercasing input.** Verified live: "Berbat bir deneyimdi..." (capital B,
  as any real sentence starts) classified **olumlu (0.88)**; the identical
  sentence lowercased ("berbat bir deneyimdi...") classified **olumsuz
  (0.93)** — same meaning, opposite answer, purely from casing. A 2x2 test
  (case × punctuation) isolated casing as the sole cause. Measured on the
  500-example `evaluate.py` set: lowercasing before inference raised accuracy
  73.2% → 74.4% (8 fixed, 2 regressed, net +6/500). Fix applied in both
  `analiz_et` and `kelime_onemleri` in `sentiment.py` (`model(metin.lower())`)
  — both call the model directly, so both needed the fix or the result card
  and the word-highlight base prediction could disagree. Word-highlight
  *display* still uses original casing (`kelimeler = metin.split()` on the
  un-lowered text) — only the model's input is lowercased.
- **`sentiment.py`'s `ETIKET_MAP`** hedges between two label formats
  (`positive/neutral/negative` and `LABEL_2/LABEL_1/LABEL_0`). Verified
  live: this model returns literal `positive`/`neutral`/`negative`, so
  the `LABEL_*` branch is currently dead code for this specific model
  — harmless, but don't assume it's exercised.
- **`--neutral-text` exists because the raw status "warning" hex
  (`#fab219`) fails contrast on the light surface** (1.79:1, per the
  dataviz skill's own palette docs — sub-3:1 "by design"). It's fine on
  dark (9.49:1). `app.py`'s CSS defines `--neutral-text` as a darker
  amber (`#9a6700`) in light mode and the raw warning hex in dark mode,
  and uses it for any literal text coloring (result card label, stat
  tile value). The one place that couldn't use this fix is the
  "Detaylı sonuçlar" table: `st.dataframe` with a pandas Styler renders
  as a canvas grid, not real DOM/CSS, so `var(--neutral-text)` can't be
  read there — that pill uses the plain hex tradeoff directly (same
  pattern as good/critical), which is the documented-acceptable
  compromise, not an oversight.
- **First run downloads ~400MB** and prints an HF Hub auth warning
  (`unauthenticated requests`) — harmless, just slower without a token.
- **chromium-cli unavailable** in this container — that's why this
  skill ships its own Playwright driver instead of the usual
  `chromium-cli` heredoc.

## Troubleshooting

- `ModuleNotFoundError` for torch/streamlit/transformers → venv not
  activated, or setup step skipped. Re-run the Setup commands above.
- Driver hangs on `waitForSelector('text=Sonuç')` → Streamlit likely
  isn't serving yet; confirm `curl -sf http://localhost:8501` returns
  200 before running the driver.
- Port already in use on relaunch → `lsof -ti:8501 -sTCP:LISTEN | xargs -r kill`
  before starting again.
- `ImportError: SentencePieceExtractor requires the SentencePiece library` (or
  a follow-on `ModuleNotFoundError: No module named 'tiktoken'`) when loading
  the model → `sentencepiece` missing from the venv; `pip install -r
  requirements.txt` should cover it, or `pip install sentencepiece` directly.
