import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.describe('Compliance Disclaimers and Custom Fees E2E Tests', () => {
  test('should block wallet connection until human steward disclaimer is checked', async ({ page }) => {
    await page.goto('http://localhost:3000/');
    await page.waitForTimeout(1000);

    // Open wallet connect dropdown
    await page.locator('#wallet-connect-btn').click();
    await page.waitForSelector('#agent-steward-checkbox');

    // Confirm that wallet buttons are disabled
    const peraBtn = page.locator('#connect-pera');
    await expect(peraBtn).toBeDisabled();

    // Check the human steward checkbox
    await page.locator('#agent-steward-checkbox').check();

    // Confirm that wallet buttons are now enabled
    await expect(peraBtn).toBeEnabled();
  });

  test('should block bounty creation until tax disclaimer is checked and validate custom fees', async ({ page }) => {
    // Inject mock creator credentials
    const tokensPath = path.join(process.cwd(), 'session_tokens.json');
    let creatorJwt = 'mock_jwt';
    let creatorAddress = 'AAAABBBBC3GDV6N4Z6XN2L6X7T2H6XN2L6XN2L6XN2L6XN2L6XN2L6XN2L';
    if (fs.existsSync(tokensPath)) {
      const tokens = JSON.parse(fs.readFileSync(tokensPath, 'utf-8'));
      creatorJwt = tokens.CREATOR.jwt;
      creatorAddress = tokens.CREATOR.address;
    }

    await page.goto('http://localhost:3000/');
    await page.waitForTimeout(1000);
    await page.evaluate((creds) => {
      window.localStorage.setItem('algobounty_jwt', creds.jwt);
      window.localStorage.setItem('algobounty_address', creds.address);
      window.localStorage.setItem('algobounty_connected', 'true');
      window.localStorage.setItem('algobounty_wallet_type', 'pera');
    }, { jwt: creatorJwt, address: creatorAddress });

    // Navigate to create page
    await page.goto('http://localhost:3000/create');
    await page.waitForTimeout(1000);
    await page.waitForSelector('#description');

    // Fill details
    await page.fill('#description', 'E2E test for custom fees and disclaimers');
    await page.fill('#amount', '100');
    await page.fill('#repo-url', 'https://github.com/IcanBENCHurCAT/algo-bounty');

    // Submit button should be disabled by default
    const submitBtn = page.locator('#create-bounty-btn');
    await expect(submitBtn).toBeDisabled();

    // Open Advanced Settings accordion
    await page.locator('#advanced-settings-toggle').click();
    await page.waitForSelector('#platformFee');

    // Test validation for Platform Fee > 10%
    await page.fill('#platformFee', '12.0');
    await page.fill('#developerFee', '5.0');
    
    // Check tax disclaimer to enable the submit button (to trigger validation onSubmit)
    await page.locator('#tax-disclaimer-checkbox').check();
    await expect(submitBtn).toBeEnabled();

    // Click submit and check for fee validation errors
    await submitBtn.click();
    await expect(page.locator('text=Platform fee must be between 0% and 10%')).toBeVisible();

    // Set correct values
    await page.fill('#platformFee', '5.0');
    await page.fill('#developerFee', '2.5');

    // Submit form (in local sandbox mode, backend skips signature/broadcasting or mocks it)
    await submitBtn.click();
    await page.waitForURL(/\/bounties\//, { timeout: 10000 });
    expect(page.url()).toContain('/bounties/');
  });
});
