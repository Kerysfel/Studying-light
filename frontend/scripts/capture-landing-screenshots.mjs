import { chromium, request } from "@playwright/test";

const BASE_URL = process.env.SCREENSHOT_BASE_URL || "http://host.docker.internal:8000";
const USER_EMAIL = process.env.SCREENSHOT_USER_EMAIL;
const ADMIN_EMAIL = process.env.SCREENSHOT_ADMIN_EMAIL;
const PASSWORD = process.env.SCREENSHOT_PASSWORD || "strongpass123";

if (!USER_EMAIL || !ADMIN_EMAIL) {
  throw new Error("Set SCREENSHOT_USER_EMAIL and SCREENSHOT_ADMIN_EMAIL env vars");
}

const VIEWPORT = { width: 1600, height: 1000 };
const AUTH_TOKEN_STORAGE_KEY = "studying_light_access_token";

const loginAndGetToken = async (apiContext, email) => {
  const response = await apiContext.post("/api/v1/auth/login", {
    data: { email, password: PASSWORD },
  });
  if (!response.ok()) {
    throw new Error(`Login failed for ${email}: ${response.status()} ${await response.text()}`);
  }
  const payload = await response.json();
  return payload.access_token;
};

const capturePublic = async (browser, path, outputFile) => {
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();
  await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await page.screenshot({ path: outputFile, fullPage: false });
  await context.close();
};

const captureAuthed = async (browser, token, path, outputFile) => {
  const context = await browser.newContext({ viewport: VIEWPORT });
  await context.addInitScript(
    ({ storageKey, accessToken }) => {
      localStorage.setItem(storageKey, accessToken);
    },
    {
      storageKey: AUTH_TOKEN_STORAGE_KEY,
      accessToken: token,
    }
  );
  const page = await context.newPage();
  await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  await page.screenshot({ path: outputFile, fullPage: false });
  await context.close();
};

const apiContext = await request.newContext({ baseURL: BASE_URL });
const userToken = await loginAndGetToken(apiContext, USER_EMAIL);
const adminToken = await loginAndGetToken(apiContext, ADMIN_EMAIL);
await apiContext.dispose();

const browser = await chromium.launch({ headless: true });

try {
  await capturePublic(browser, "/login", "frontend/public/landing/landing_auth_login.png");
  await capturePublic(browser, "/register", "frontend/public/landing/landing_auth_register.png");
  await captureAuthed(browser, userToken, "/import", "frontend/public/landing/landing_export.png");
  await captureAuthed(browser, adminToken, "/admin/users", "frontend/public/landing/landing_admin_users.png");
} finally {
  await browser.close();
}
