import { test, expect } from '@playwright/test';

test('Admin Login Flow', async ({ page }) => {
  // 1. Navigate to Admin Dashboard
  await page.goto('/');

  // 2. Expect redirect to Keycloak (check URL or specific element)
  // Note: Depending on existing auth state, it might go straight to dashboard.
  // Assuming clean slate or incognito context usually used by Playwright.
  
  // Click the "Sign In with SSO" button
  await page.getByRole('button', { name: 'Sign In with SSO' }).click();

  // Wait for Keycloak login page (Keycloak 24+ uses /realms/...)
  await page.waitForURL(/.*realms\/infant-stack.*/);
  await expect(page.locator('#kc-page-title')).toContainText('Sign in to your account');

  // 3. Perform Login
  await page.fill('#username', 'admin@example.com');
  await page.fill('#password', 'admin123');
  await page.click('#kc-login');

  // 4. Verify Redirect back to Dashboard
  // 4. Verify Redirect back to Dashboard
  await page.waitForURL(/^http:\/\/localhost:\d+\/$/); // Specific port agnostic match or specific if known
  
  // 5. Verify Dashboard Content (e.g., Header, User Name)
  // Adjust selector based on actual Dashboard UI
  await expect(page.getByText('Admin Dashboard')).toBeVisible();
});
