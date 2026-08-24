import { test } from '@playwright/test';
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

test('Capture Full Rich UI Lifecycle Screenshots (Marketplace, Claim Modal, Submit View, Approve Modal)', async ({ context, page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });

  // Route mock responses for marketplace listing (only matching exact /api/v1/bounties endpoint)
  await context.route(url => url.pathname === '/api/v1/bounties', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          bounties: [
            {
              bounty_id: 'b_1001',
              app_id: 1001,
              status: 'open',
              creator: 'CREATOR_ADDRESS_123456789',
              worker: null,
              amount: 150000000,
              asset_id: 0,
              asset_name: 'ALGO',
              hitm: true,
              description: 'Build a Next.js Landing Page & Wallet Verification Hook',
              repo_url: 'https://github.com/IcanBENCHurCAT/algo-bounty',
              karma_requirement: 10,
              created_at: new Date().toISOString(),
              rejection_count: 0,
              treasury_altered: false
            },
            {
              bounty_id: 'b_1002',
              app_id: 1002,
              status: 'claimed',
              creator: 'CREATOR_ADDRESS_123456789',
              worker: 'WORKER_ADDRESS_987654321',
              amount: 250000000,
              asset_id: 0,
              asset_name: 'ALGO',
              hitm: false,
              description: 'Refactor Puya Smart Contract Escrow State Machine',
              repo_url: 'https://github.com/IcanBENCHurCAT/algo-bounty',
              karma_requirement: 25,
              created_at: new Date().toISOString(),
              rejection_count: 0,
              treasury_altered: false
            },
            {
              bounty_id: 'b_1003',
              app_id: 1003,
              status: 'submitted',
              creator: 'CREATOR_ADDRESS_123456789',
              worker: 'WORKER_ADDRESS_987654321',
              amount: 500000000,
              asset_id: 0,
              asset_name: 'ALGO',
              hitm: true,
              description: 'Implement Automated GitHub OIDC Action Verification',
              repo_url: 'https://github.com/IcanBENCHurCAT/algo-bounty',
              karma_requirement: 15,
              created_at: new Date().toISOString(),
              rejection_count: 0,
              treasury_altered: false
            }
          ],
          total: 3,
          page: 1,
          limit: 20,
          has_more: false
        })
      });
    } else {
      await route.continue();
    }
  });

  // Route mock responses for transaction preparation so modals open cleanly with estimated mediator fee
  await context.route('**/api/v1/bounties/*/claim/txn', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        unsigned_txn: "MOCK_CLAIM_TXN",
        fee_breakdown: {
          escrow_amount: 150000000,
          developer_royalty: 1500000,
          platform_treasury: 1500000,
          mediator_fee: 0,
          estimated_mediator_fee: 375000,
          claimant_payout: 147000000
        },
        fee_breakdown_display: {
          total: "150 ALGO",
          developer_royalty: "1.50 ALGO",
          platform_treasury: "1.50 ALGO",
          mediator_fee: "0 ALGO",
          estimated_mediator_fee: "0.38 ALGO",
          claimant_payout: "147 ALGO"
        }
      })
    });
  });

  await context.route('**/api/v1/bounties/*/approve/txn', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        unsigned_txn: "MOCK_APPROVE_TXN",
        fee_breakdown: {
          escrow_amount: 500000000,
          developer_royalty: 5000000,
          platform_treasury: 5000000,
          mediator_fee: 0,
          estimated_mediator_fee: 1250000,
          claimant_payout: 490000000
        },
        fee_breakdown_display: {
          total: "500 ALGO",
          developer_royalty: "5.00 ALGO",
          platform_treasury: "5.00 ALGO",
          mediator_fee: "0 ALGO",
          estimated_mediator_fee: "1.25 ALGO",
          claimant_payout: "490 ALGO"
        }
      })
    });
  });

  // Load session tokens
  const tokensPath = path.join(process.cwd(), 'session_tokens.json');
  const tokens = JSON.parse(fs.readFileSync(tokensPath, 'utf-8'));
  const creator = tokens.CREATOR;
  const worker = tokens.WORKER;

  console.log('--- Step 1: Marketplace Dashboard with Loaded Cards ---');
  await page.goto('http://localhost:3000/');
  
  // Wait explicitly for .bounty-card element to mount (skipping skeleton boxes)
  await page.waitForSelector('.bounty-card', { timeout: 10000 });
  await page.waitForTimeout(1000);

  // Capture full marketplace homepage with loaded cards
  await page.screenshot({ path: `${DOCS_IMG_DIR}/marketplace_dashboard.png` });
  await page.screenshot({ path: `${BRAIN_DIR}/marketplace_dashboard.png` });

  console.log('--- Step 2: Open Claim Modal on Open Bounty (b_1001) ---');
  const workerPage = await context.newPage();
  await workerPage.setViewportSize({ width: 1280, height: 800 });
  await workerPage.addInitScript((creds) => {
    window.localStorage.setItem('algobounty_jwt', creds.jwt);
    window.localStorage.setItem('algobounty_address', creds.address);
    window.localStorage.setItem('algobounty_connected', 'true');
    window.localStorage.setItem('algobounty_wallet_type', 'pera');
  }, worker);

  await workerPage.goto('http://localhost:3000/bounties/b_1001');
  await workerPage.waitForSelector('#claim-btn', { timeout: 10000 });
  await workerPage.waitForTimeout(1000);

  await workerPage.screenshot({ path: `${DOCS_IMG_DIR}/bounty_detail_view.png` });
  await workerPage.screenshot({ path: `${BRAIN_DIR}/bounty_detail_view.png` });

  const claimBtn = workerPage.locator('#claim-btn');
  await claimBtn.click();
  await workerPage.waitForSelector('#claim-modal-title', { timeout: 5000 });
  await workerPage.waitForTimeout(800);
  await workerPage.screenshot({ path: `${DOCS_IMG_DIR}/claim_bounty_modal.png` });
  await workerPage.screenshot({ path: `${BRAIN_DIR}/claim_bounty_modal.png` });

  console.log('--- Step 3: Submitting Work View on Claimed Bounty (b_1002) ---');
  await workerPage.goto('http://localhost:3000/bounties/b_1002');
  await workerPage.waitForSelector('#pr-url-input', { timeout: 10000 });
  await workerPage.waitForTimeout(1000);

  const prInput = workerPage.locator('#pr-url-input');
  await prInput.fill('https://github.com/IcanBENCHurCAT/algo-bounty/pull/42');
  await workerPage.waitForTimeout(600);
  await workerPage.screenshot({ path: `${DOCS_IMG_DIR}/submit_work_view.png` });
  await workerPage.screenshot({ path: `${BRAIN_DIR}/submit_work_view.png` });

  console.log('--- Step 4: Open Approval Modal on Submitted Bounty (b_1003) ---');
  const creatorPage = await context.newPage();
  await creatorPage.setViewportSize({ width: 1280, height: 800 });
  await creatorPage.addInitScript((creds) => {
    window.localStorage.setItem('algobounty_jwt', creds.jwt);
    window.localStorage.setItem('algobounty_address', creds.address);
    window.localStorage.setItem('algobounty_connected', 'true');
    window.localStorage.setItem('algobounty_wallet_type', 'pera');
  }, creator);

  await creatorPage.goto('http://localhost:3000/bounties/b_1003');
  await creatorPage.waitForSelector('#approve-btn', { timeout: 10000 });
  await creatorPage.waitForTimeout(1000);

  const approveBtn = creatorPage.locator('#approve-btn');
  await approveBtn.click();
  await creatorPage.waitForSelector('#approve-modal-title', { timeout: 5000 });
  await creatorPage.waitForTimeout(800);
  await creatorPage.screenshot({ path: `${DOCS_IMG_DIR}/approve_payout_modal.png` });
  await creatorPage.screenshot({ path: `${BRAIN_DIR}/approve_payout_modal.png` });

  console.log('Full rich UI lifecycle screenshots captured successfully.');
});
