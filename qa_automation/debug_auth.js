const { chromium } = require('@playwright/test');

(async () => {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('Navigating to Hub (http://localhost:3003)...');
    await page.goto('http://localhost:3003', { timeout: 60000 });
    
    console.log('Waiting for Dashboard OR Login Form...');
    
    // Check for dashboard text or user profile
    const dashboardText = page.getByText('Your Dashboards');
    const userProfileText = page.getByText('Omar Salem'); 
    const usernameInput = page.getByLabel(/username|email/i);

    // Use a race condition to detect state
    // We catch errors to return null/false instead of throwing
    const state = await Promise.race([
        dashboardText.waitFor({ state: 'visible', timeout: 30000 }).then(() => 'dashboard'),
        userProfileText.waitFor({ state: 'visible', timeout: 30000 }).then(() => 'dashboard'),
        usernameInput.waitFor({ state: 'visible', timeout: 30000 }).then(() => 'login')
    ]).catch(e => 'timeout');

    console.log('Detected state: ' + state);

    if (state === 'login') {
        console.log('Login form detected. Filling credentials...');
        await usernameInput.fill('omarsl530@gmail.com');
        
        const passwordInput = page.getByLabel(/password/i);
        await passwordInput.fill('12345678');
        
        console.log('Submitting form...');
        await page.getByRole('button', { name: /sign in|login/i }).click();

        console.log('Waiting for redirect back to Hub...');
        await page.waitForURL('http://localhost:3003/', { timeout: 30000 });
        console.log('Redirect complete.');
    } else if (state === 'dashboard') {
        console.log('Already logged in! Skipping credentials.');
    } else {
        console.log('State detection timed out! Dumping page text/content...');
        const content = await page.content(); // HTML
        const text = await page.innerText('body');
        console.log('Page Text Snapshot: ' + text.substring(0, 500)); // First 500 chars
        throw new Error('Could not detect login state');
    }
    
    console.log('Login Successful!');
    
    // Check for success message
    const welcome = await page.getByText('Welcome, Omar!').isVisible();
    console.log('Welcome message visible: ' + welcome);

  } catch (error) {
    console.error('Test Failed:', error);
    await page.screenshot({ path: 'debug_failure.png' });
  } finally {
    console.log('Closing browser in 5 seconds...');
    await new Promise(r => setTimeout(r, 5000));
    await browser.close();
  }
})();
