// Drives the Streamlit app at http://localhost:8501 with Playwright.
// chromium-cli isn't available in this environment, so this is the fallback driver
// per the /run skill instructions. Requires: streamlit already running (see SKILL.md).
//
// Usage: node driver.mjs single   -> fill "Tek Yorum" tab, screenshot result
//        node driver.mjs batch    -> upload ornek_yorumlar.csv on "Toplu Analiz" tab, screenshot result
//        node driver.mjs all      -> run both (default)

import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
const APP_URL = 'http://localhost:8501';
const PROJECT_ROOT = path.resolve(__dirname, '..', '..', '..');

async function runSingle(page) {
  await page.getByRole('tab', { name: 'Tek Yorum' }).click();
  // Tek yorum girişi st.chat_input (Enter'a basınca gönderir, ayrı bir buton yok).
  const girdi = page.locator('[data-testid="stChatInputTextArea"]');
  await girdi.click();
  await girdi.type('Ürün çok hızlı geldi, çok memnun kaldım!');
  await page.keyboard.press('Enter');
  await page.waitForSelector('.result-card', { timeout: 30000 });
  const shot = path.join(SCREENSHOT_DIR, 'single.png');
  await page.screenshot({ path: shot });
  console.log('single: OK ->', shot);
}

async function runBatch(page) {
  await page.getByRole('tab', { name: 'Toplu Analiz' }).click();
  const csvPath = path.join(PROJECT_ROOT, 'ornek_yorumlar.csv');
  await page.setInputFiles('input[type="file"]', csvPath);
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: 'Toplu Analiz Yap' }).click();
  await page.waitForSelector('.stat-grid', { timeout: 60000 });
  await page.waitForTimeout(1000);
  const shot = path.join(SCREENSHOT_DIR, 'batch.png');
  await page.screenshot({ path: shot, fullPage: true });
  console.log('batch: OK ->', shot);
}

const mode = process.argv[2] || 'all';

const browser = await chromium.launch();
// Streamlit scrolls inside [data-testid="stMain"] rather than growing <body>,
// so a tall viewport is needed for fullPage screenshots to capture everything.
const page = await browser.newPage({ viewport: { width: 1280, height: 1600 } });
const consoleErrors = [];
page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

await page.goto(APP_URL, { waitUntil: 'networkidle' });
await page.waitForSelector('text=Müşteri Yorumu Duygu Analizi', { timeout: 15000 });

if (mode === 'single' || mode === 'all') await runSingle(page);
if (mode === 'batch' || mode === 'all') await runBatch(page);

console.log('CONSOLE_ERRORS:', JSON.stringify(consoleErrors));
await browser.close();
