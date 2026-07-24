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

test('Capture Bounty Lifecycle Screenshots (Claim, Submit, Approve)', async ({ page }) => {
  console.log('--- Step 1: Navigate to Marketplace Dashboard ---');
  await page.goto('http://localhost:3000/');
  await page.waitForSelector('h1');
  await page.waitForTimeout(1000);

  // Capture full marketplace homepage with loaded cards
  await page.screenshot({ path: `${DOCS_IMG_DIR}/marketplace_dashboard.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/marketplace_dashboard.png` });

  console.log('--- Step 2: Open Bounty Detail Page & Capture Detail View ---');
  await page.goto('http://localhost:3000/bounties/b_12345');
  await page.waitForSelector('h1');
  await page.waitForTimeout(1000);

  // Inject Worker (Bob) Wallet Session
  await page.evaluate(() => {
    window.localStorage.setItem('algobounty_jwt', 'mock_jwt_worker_token');
    window.localStorage.setItem('algobounty_address', 'WORKER_ADDRESS_987654321');
    window.localStorage.setItem('algobounty_connected', 'true');
    window.localStorage.setItem('algobounty_wallet_type', 'pera');
  });

  await page.reload();
  await page.waitForSelector('h1');
  await page.waitForTimeout(1000);

  // Take screenshot of fully rendered Bounty Detail View as Worker
  await page.screenshot({ path: `${DOCS_IMG_DIR}/bounty_detail_view.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/bounty_detail_view.png` });

  console.log('--- Step 3: Trigger Claim Action / Capture Claim Interface ---');
  const claimBtn = page.locator('#claim-btn');
  if (await claimBtn.isVisible()) {
    await claimBtn.click();
    await page.waitForTimeout(600);
  }
  await page.screenshot({ path: `${DOCS_IMG_DIR}/claim_bounty_modal.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/claim_bounty_modal.png` });

  console.log('--- Step 4: Simulate Submitting Work (PR Link Input) ---');
  const prInput = page.locator('#pr-url-input');
  if (await prInput.isVisible()) {
    await prInput.fill('https://github.com/IcanBENCHurCAT/algo-bounty/pull/42');
    await page.waitForTimeout(400);
  }
  await page.screenshot({ path: `${DOCS_IMG_DIR}/submit_work_view.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/submit_work_view.png` });

  console.log('--- Step 5: Simulate Creator Approval & Fee Breakdown ---');
  await page.evaluate(() => {
    window.localStorage.setItem('algobounty_jwt', 'mock_jwt_creator_token');
    window.localStorage.setItem('algobounty_address', 'CREATOR_ADDRESS_123456789');
    window.localStorage.setItem('algobounty_connected', 'true');
  });

  await page.reload();
  await page.waitForSelector('h1');
  await page.waitForTimeout(1000);

  const approveBtn = page.locator('#approve-btn');
  if (await approveBtn.isVisible()) {
    await approveBtn.click();
    await page.waitForTimeout(600);
  }
  await page.screenshot({ path: `${DOCS_IMG_DIR}/approve_payout_modal.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/approve_payout_modal.png` });

  console.log('Lifecycle screenshots capture complete.');
});
