import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  console.log('Navigating to Hub...');
  // Go to Hub, which redirects to Keycloak
  await page.goto('http://localhost:3003', { timeout: 60000 });
  
  // Wait for either the Dashboard (already logged in) OR the Login Form
  // We race these two conditions
  const dashboardText = page.getByText('Your Dashboards');
  const userProfileText = page.getByText('Omar Salem'); // Also check for user profile
  const usernameInput = page.getByLabel(/username|email/i);

  console.log('Waiting for Dashboard OR Login Form...');
  
  // Use a race condition to detect state
  const isLoginNeeded = await Promise.race([
    dashboardText.waitFor({ state: 'visible', timeout: 60000 }).then(() => false),
    userProfileText.waitFor({ state: 'visible', timeout: 60000 }).then(() => false),
    usernameInput.waitFor({ state: 'visible', timeout: 60000 }).then(() => true)
  ]);

  if (isLoginNeeded) {
      console.log('Login form detected. Filling credentials...');
      await usernameInput.fill('omarsl530@gmail.com');
      
      // Use ID selector to avoid ambiguity with "Show Password" button
      await page.locator('#password').fill('12345678');
      
      console.log('Submitting form...');
      await page.getByRole('button', { name: /sign in|login/i }).click();

      console.log('Waiting for redirect back to Hub...');
      await page.waitForURL('http://localhost:3003/', { timeout: 60000 });
  } else {
      console.log('Already logged in! Skipping credentials.');
  }

  // Final Verification
  await expect(page.getByText('Your Dashboards')).toBeVisible({ timeout: 60000 });
  // Wait for redirect back to Hub
  await page.waitForURL('http://localhost:3003/', { timeout: 60000 });
  
  // Verify login success
  await expect(page.getByText('Welcome, Omar!')).toBeVisible({ timeout: 60000 });

  console.log('Saving storage state...');
  // Save storage state
  await page.context().storageState({ path: authFile });
});
