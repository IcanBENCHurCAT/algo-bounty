import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const CONV_ID = "02f516ab-7a8e-4da2-b688-922942ee50d2";
const BRAIN_DIR = `C:/Users/Garret/.gemini/antigravity/brain/${CONV_ID}`;
const DOCS_IMG_DIR = path.join(process.cwd(), '..', 'docs', 'images');

[BRAIN_DIR, DOCS_IMG_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

test('Capture Full Rich UI Lifecycle Screenshots (Marketplace, Claim, Submit, Approve)', async ({ page }) => {
  console.log('--- Step 1: Marketplace Dashboard with Loaded Cards ---');
  await page.goto('http://localhost:3000/', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1');
  await page.waitForTimeout(2000); // Wait for React useEffect fetch to complete

  // Capture full marketplace homepage with loaded cards
  await page.screenshot({ path: `${DOCS_IMG_DIR}/marketplace_dashboard.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/marketplace_dashboard.png` });

  console.log('--- Step 2: Bounty Detail View & Claim Modal ---');
  await page.goto('http://localhost:3000/bounties/b_1001', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1');

  // Inject Worker (Bob) Wallet Session
  await page.evaluate(() => {
    window.localStorage.setItem('algobounty_jwt', 'mock_jwt_worker_token');
    window.localStorage.setItem('algobounty_address', 'WORKER_ADDRESS_987654321');
    window.localStorage.setItem('algobounty_connected', 'true');
    window.localStorage.setItem('algobounty_wallet_type', 'pera');
  });

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1');
  await page.waitForTimeout(1500);

  await page.screenshot({ path: `${DOCS_IMG_DIR}/bounty_detail_view.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/bounty_detail_view.png` });

  // Click Claim button to trigger Claim Confirmation Modal with Fee Breakdown
  const claimBtn = page.locator('#claim-btn');
  if (await claimBtn.isVisible()) {
    await claimBtn.click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${DOCS_IMG_DIR}/claim_bounty_modal.png` });
    await page.screenshot({ path: `${BRAIN_DIR}/claim_bounty_modal.png` });
  }

  console.log('--- Step 3: Submitting Work (PR Link Input) ---');
  await page.goto('http://localhost:3000/bounties/b_1002', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1');

  await page.evaluate(() => {
    window.localStorage.setItem('algobounty_jwt', 'mock_jwt_worker_token');
    window.localStorage.setItem('algobounty_address', 'WORKER_ADDRESS_987654321');
    window.localStorage.setItem('algobounty_connected', 'true');
  });

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1');
  await page.waitForTimeout(1500);

  const prInput = page.locator('#pr-url-input');
  if (await prInput.isVisible()) {
    await prInput.fill('https://github.com/IcanBENCHurCAT/algo-bounty/pull/42');
    await page.waitForTimeout(600);
  }
  await page.screenshot({ path: `${DOCS_IMG_DIR}/submit_work_view.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/submit_work_view.png` });

  console.log('--- Step 4: Creator Approval & Fee Breakdown Modal ---');
  await page.goto('http://localhost:3000/bounties/b_1003', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1');

  await page.evaluate(() => {
    window.localStorage.setItem('algobounty_jwt', 'mock_jwt_creator_token');
    window.localStorage.setItem('algobounty_address', 'CREATOR_ADDRESS_123456789');
    window.localStorage.setItem('algobounty_connected', 'true');
  });

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1');
  await page.waitForTimeout(1500);

  const approveBtn = page.locator('#approve-btn');
  if (await approveBtn.isVisible()) {
    await approveBtn.click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${DOCS_IMG_DIR}/approve_payout_modal.png` });
    await page.screenshot({ path: `${BRAIN_DIR}/approve_payout_modal.png` });
  }

  console.log('Full rich UI lifecycle screenshots captured successfully.');
});
