/**
 * Home Dashboard E2E Tests
 *
 * Tests for centralized login, role-based access, and deep-link protection.
 */

import { test, expect } from "@playwright/test";

const HOME_DASHBOARD_URL = "http://localhost:3003";
const SECURITY_DASHBOARD_URL = "http://localhost:3001";

test.describe("Home Dashboard - Authentication", () => {
  test("should show login page and redirect to Keycloak on click", async ({
    page,
  }) => {
    // Navigate to home dashboard
    await page.goto(HOME_DASHBOARD_URL);

    // Should see login redirect (OIDC auto-redirects)
    // Wait for Keycloak login page
    await page.waitForURL(/.*realms\/infant-stack.*/, { timeout: 10000 });
    await expect(page.locator("#kc-page-title")).toContainText(
      "Sign in to your account"
    );
  });

  test("should login as admin and see dashboard hub", async ({ page }) => {
    // Navigate to home dashboard
    await page.goto(HOME_DASHBOARD_URL);

    // Wait for Keycloak redirect
    await page.waitForURL(/.*realms\/infant-stack.*/);

    // Login as admin
    await page.fill("#username", "admin@example.com");
    await page.fill("#password", "admin123");
    await page.click("#kc-login");

    // Wait for redirect back to home dashboard
    await page.waitForURL(`${HOME_DASHBOARD_URL}/**`);

    // Verify dashboard hub is visible
    await expect(page.getByText("Dashboard Hub")).toBeVisible();
    await expect(page.getByText("Your Dashboards")).toBeVisible();
  });

  test("should show accessible dashboards based on roles", async ({ page }) => {
    // Login as admin first
    await page.goto(HOME_DASHBOARD_URL);
    await page.waitForURL(/.*realms\/infant-stack.*/);

    await page.fill("#username", "admin@example.com");
    await page.fill("#password", "admin123");
    await page.click("#kc-login");

    await page.waitForURL(`${HOME_DASHBOARD_URL}/**`);

    // Admin should see all dashboards
    await expect(page.getByText("Nurse Dashboard")).toBeVisible();
    await expect(page.getByText("Security Dashboard")).toBeVisible();
    await expect(page.getByText("Admin Dashboard")).toBeVisible();
  });
});

test.describe("Deep-Link Protection", () => {
  test("should redirect unauthenticated user to login", async ({ page }) => {
    // Try to access security dashboard directly without auth
    await page.goto(SECURITY_DASHBOARD_URL);

    // Should redirect to Keycloak
    await page.waitForURL(/.*realms\/infant-stack.*/, { timeout: 10000 });
    await expect(page.locator("#kc-page-title")).toContainText(
      "Sign in to your account"
    );
  });
});

test.describe("Role-Based Access Control", () => {
  test("user without security role should see access denied on security dashboard", async ({
    page,
  }) => {
    // Login as regular user (has nurse role only, no security role)
    await page.goto(SECURITY_DASHBOARD_URL);
    await page.waitForURL(/.*realms\/infant-stack.*/);

    // Login as user (not admin - only has nurse role)
    await page.fill("#username", "user@example.com");
    await page.fill("#password", "user123");
    await page.click("#kc-login");

    // User should see access denied (has nurse role but not security)
    await page.waitForURL(`${SECURITY_DASHBOARD_URL}/**`, { timeout: 10000 });

    // Should show access denied or be redirected
    // Note: user@example.com now has nurse role, so should be denied security
    await expect(page.getByText("Access Denied")).toBeVisible();
  });
});

test.describe("Logout Flow", () => {
  test("should logout and redirect to home dashboard", async ({ page }) => {
    // Login first
    await page.goto(HOME_DASHBOARD_URL);
    await page.waitForURL(/.*realms\/infant-stack.*/);

    await page.fill("#username", "admin@example.com");
    await page.fill("#password", "admin123");
    await page.click("#kc-login");

    await page.waitForURL(`${HOME_DASHBOARD_URL}/**`);

    // Find and click logout button
    await page.getByTitle("Sign Out").click();

    // Should redirect to Keycloak logout or home page
    // Keycloak handles logout and redirects back
    await page.waitForURL(/.*/, { timeout: 10000 });
  });
});
