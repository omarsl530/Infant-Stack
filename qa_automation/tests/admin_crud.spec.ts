import { test, expect } from '@playwright/test';

// Inline login helper (reused for stability)
async function loginAsAdmin(page) {
    await page.goto('http://localhost:3002');
    // Check if we are already logged in or need to log in
    try {
        await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible({ timeout: 5000 });
        return; // Already logged in
    } catch (e) {
        // Not logged in, proceed
    }

    // Attempt login if redirected to hub/login
    const usernameInput = page.getByLabel(/username|email/i);
    if (await usernameInput.isVisible()) {
        await usernameInput.fill('omarsl530@gmail.com');
        await page.locator('#password').fill('12345678');
        await page.getByRole('button', { name: /sign in|login/i }).click();
        await page.waitForURL('http://localhost:3002/', { timeout: 30000 });
    }
}

test.describe('Admin Dashboard CRUD', () => {

    test('Admin can create a new user', async ({ page }) => {
        // --- DEBUG LOGGING ---
        page.on('console', msg => console.log('PAGE LOG:', msg.text()));
        page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
        page.on('requestfailed', request => {
            console.log(`REQUEST FAILED: ${request.url()} - ${request.failure()?.errorText}`);
        });
        page.on('response', response => {
            if (response.status() >= 400 && response.url().includes('/api')) {
                console.log(`API ERROR: ${response.status()} ${response.url()}`);
            }
        });
        // ---------------------

        // 1. Login and Navigate
        await loginAsAdmin(page);
        await page.goto('http://localhost:3002');
        await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible();

        // 2. Open Add User Modal
        await page.getByRole('button', { name: 'Add User' }).click();
        await expect(page.getByRole('heading', { name: 'Add New User' })).toBeVisible();

        // 3. Fill Form - capture timestamp ONCE to avoid mismatch
        const timestamp = Date.now();
        const testUser = {
            firstName: 'Test',
            lastName: 'User' + timestamp,
            email: `test${timestamp}@example.com`,
            password: 'password123'
        };

        await page.locator('#first_name').fill(testUser.firstName);
        await page.locator('#last_name').fill(testUser.lastName);
        await page.locator('#email').fill(testUser.email);
        
        // Select role directly by value (lowercase from API)
        const roleDropdown = page.locator('#role');
        await roleDropdown.selectOption('nurse');

        await page.locator('#password').fill(testUser.password);
        await page.locator('#confirmPassword').fill(testUser.password);

        // 4. Submit
        await page.getByRole('button', { name: 'Save' }).click();

        // 5. Verify User in Table
        // Wait for modal to close
        await expect(page.getByRole('heading', { name: 'Add New User' })).toBeHidden({ timeout: 10000 });
        
        // Check list for new user by email (most reliable)
        await expect(page.getByText(testUser.email)).toBeVisible({ timeout: 10000 });
    });

});
