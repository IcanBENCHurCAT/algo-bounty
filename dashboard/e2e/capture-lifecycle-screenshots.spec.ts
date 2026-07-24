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
  console.log('--- Step 1: Navigate to Marketplace & Pick Open Bounty ---');
  await page.goto('http://localhost:3000/');
  await page.waitForTimeout(1000);

  // Click first bounty card or link
  const firstBountyLink = page.locator('a[href^="/bounties/"]').first();
  if (await firstBountyLink.isVisible()) {
    await firstBountyLink.click();
  } else {
    // Navigate directly to a bounty detail page or b_1
    await page.goto('http://localhost:3000/bounties/b_1');
  }

  await page.waitForTimeout(1000);

  // Inject Worker (Bob) Wallet Session to simulate worker claiming
  console.log('--- Step 2: Simulate Worker Claim & Capture Claim Modal ---');
  await page.evaluate(() => {
    window.localStorage.setItem('algobounty_jwt', 'mock_jwt_worker_token');
    window.localStorage.setItem('algobounty_address', 'WORKER_ADDRESS_987654321');
    window.localStorage.setItem('algobounty_connected', 'true');
    window.localStorage.setItem('algobounty_wallet_type', 'pera');
  });

  await page.reload();
  await page.waitForTimeout(1000);

  // Take screenshot of Bounty Detail View as Worker
  await page.screenshot({ path: `${DOCS_IMG_DIR}/bounty_detail_view.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/bounty_detail_view.png` });

  const claimBtn = page.locator('#claim-btn');
  if (await claimBtn.isVisible()) {
    await claimBtn.click();
    await page.waitForTimeout(600);
    await page.screenshot({ path: `${DOCS_IMG_DIR}/claim_bounty_modal.png` });
    await page.screenshot({ path: `${BRAIN_DIR}/claim_bounty_modal.png` });
  } else {
    // If claim button not visible due to state, take screenshot of the action section
    await page.screenshot({ path: `${DOCS_IMG_DIR}/claim_bounty_modal.png` });
    await page.screenshot({ path: `${BRAIN_DIR}/claim_bounty_modal.png` });
  }

  console.log('--- Step 3: Simulate Submitting Work (PR Link Input) ---');
  const prInput = page.locator('#pr-url-input');
  if (await prInput.isVisible()) {
    await prInput.fill('https://github.com/IcanBENCHurCAT/algo-bounty/pull/42');
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${DOCS_IMG_DIR}/submit_work_view.png` });
    await page.screenshot({ path: `${BRAIN_DIR}/submit_work_view.png` });
  } else {
    await page.screenshot({ path: `${DOCS_IMG_DIR}/submit_work_view.png` });
    await page.screenshot({ path: `${BRAIN_DIR}/submit_work_view.png` });
  }

  console.log('--- Step 4: Simulate Creator Approval & Fee Breakdown Modal ---');
  // Inject Creator session
  await page.evaluate(() => {
    window.localStorage.setItem('algobounty_jwt', 'mock_jwt_creator_token');
    window.localStorage.setItem('algobounty_address', 'CREATOR_ADDRESS_123456789');
    window.localStorage.setItem('algobounty_connected', 'true');
  });

  await page.reload();
  await page.waitForTimeout(1000);

  const approveBtn = page.locator('#approve-btn');
  if (await approveBtn.isVisible()) {
    await approveBtn.click();
    await page.waitForTimeout(600);
    await page.screenshot({ path: `${DOCS_IMG_DIR}/approve_payout_modal.png` });
    await page.screenshot({ path: `${BRAIN_DIR}/approve_payout_modal.png` });
  } else {
    await page.screenshot({ path: `${DOCS_IMG_DIR}/approve_payout_modal.png` });
    await page.screenshot({ path: `${BRAIN_DIR}/approve_payout_modal.png` });
  }

  console.log('Lifecycle screenshots capture complete.');
});
