import { test, expect } from '@playwright/test';

// Inline login helper to bypass auth.setup.ts issues
async function login(page) {
    await page.goto('http://localhost:3003');
    const dashboardText = page.getByText('Your Dashboards');
    const userProfileText = page.getByText('Omar Salem'); 
    const usernameInput = page.getByLabel(/username|email/i);

    // Race condition to check state
    const state = await Promise.race([
        dashboardText.waitFor({ state: 'visible', timeout: 30000 }).then(() => 'dashboard'),
        userProfileText.waitFor({ state: 'visible', timeout: 30000 }).then(() => 'dashboard'),
        usernameInput.waitFor({ state: 'visible', timeout: 30000 }).then(() => 'login')
    ]).catch(e => 'timeout');

    if (state === 'login') {
        await usernameInput.fill('omarsl530@gmail.com');
        await page.locator('#password').fill('12345678'); // Robust selector
        await page.getByRole('button', { name: /sign in|login/i }).click();
        await page.waitForURL('http://localhost:3003/', { timeout: 30000 });
    }
    // Verify we are logged in
    await expect(page.getByText('Your Dashboards')).toBeVisible({ timeout: 60000 });
}

test.describe('Infant-Stack Dashboards', () => {

    test.beforeEach(async ({ page }) => {
        await login(page);
    });
    
    test('Hub Dashboard loads and shows user', async ({ page }) => {
        await page.goto('http://localhost:3003');
        await expect(page).toHaveTitle(/Infant-Stack/);
        await expect(page.getByText('Omar Salem')).toBeVisible();
        await expect(page.getByText('Your Dashboards')).toBeVisible();
    });

    test('Nurse Dashboard - Add Mother Button works', async ({ page }) => {
        await page.goto('http://localhost:3000');
        
        // Click Add Mother
        await page.getByRole('button', { name: 'Add Mother' }).click();
        
        // Expect modal/form to appear
        await expect(page.locator('div[role="dialog"]')).toBeVisible();
        await expect(page.getByText('Register New Mother')).toBeVisible();
        
        // Close it
        await page.getByRole('button', { name: 'Cancel' }).click();
    });

    test('Nurse Dashboard - Add Baby Button works', async ({ page }) => {
        await page.goto('http://localhost:3000');
        
        // Click Add Baby
        await page.getByRole('button', { name: 'Add Baby' }).click();
        
        // Expect modal
        await expect(page.locator('div[role="dialog"]')).toBeVisible();
        await expect(page.getByText('Register New Infant')).toBeVisible();
        
        // Close it
        await page.getByRole('button', { name: 'Cancel' }).click();
    });

    test('Security Dashboard loads and shows alerts', async ({ page }) => {
        await page.goto('http://localhost:3001');
        await expect(page).toHaveTitle(/Infant-Stack/);
        // Verify metric cards
        await expect(page.getByText('Active Alerts')).toBeVisible();
        await expect(page.getByText('System Status')).toBeVisible();
    });

    test('Admin Dashboard loads and shows user table', async ({ page }) => {
        await page.goto('http://localhost:3002');
        await expect(page).toHaveTitle(/Infant-Stack/);
        await expect(page.getByText('User Management')).toBeVisible();
        await expect(page.getByRole('button', { name: 'Add User' })).toBeVisible();
    });

});
