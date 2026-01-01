import { test, expect } from "@playwright/test";

const todayPayload = {
  active_books: [
    { id: 1, title: "Sample Book", author: "Author", status: "active" },
  ],
  review_items: [
    {
      id: 10,
      reading_part_id: 5,
      interval_days: 1,
      due_date: "2024-10-10",
      status: "planned",
      book_id: 1,
      book_title: "Sample Book",
      part_index: 1,
      label: null,
    },
    {
      id: 11,
      reading_part_id: 6,
      interval_days: 7,
      due_date: "2024-10-16",
      status: "planned",
      book_id: 1,
      book_title: "Sample Book",
      part_index: 2,
      label: "Part 2",
    },
  ],
};

test("dashboard summary uses today data", async ({ page }) => {
  await page.route("**/api/v1/today", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(todayPayload),
    });
  });

  await page.goto("/");
  const modal = page.locator(".modal");
  await expect(modal).toBeVisible();

  const summaryBlocks = modal.locator(".summary-block");
  await expect(summaryBlocks).toHaveCount(2);
  await expect(summaryBlocks.nth(0).locator(".summary-list li")).toHaveCount(1);
  await expect(summaryBlocks.nth(1).locator(".summary-list li")).toHaveCount(2);
});

test("review flow completes", async ({ page }) => {
  await page.route("**/api/v1/reviews/today", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 1,
          reading_part_id: 2,
          interval_days: 1,
          due_date: "2024-10-10",
          status: "planned",
          book_id: 1,
          book_title: "Sample Book",
          part_index: 1,
          label: null,
        },
      ]),
    });
  });

  await page.route("**/api/v1/reviews/1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 1,
        reading_part_id: 2,
        interval_days: 1,
        due_date: "2024-10-10",
        status: "planned",
        book_id: 1,
        book_title: "Sample Book",
        part_index: 1,
        label: null,
        summary: "Summary text",
        questions: ["Question 1", "Question 2"],
      }),
    });
  });

  await page.route("**/api/v1/reviews/1/complete", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok" }),
    });
  });

  await page.goto("/reviews");
  await page.locator(".review-list-item .primary-button").first().click();

  const detail = page.locator(".review-detail");
  await expect(detail).toBeVisible();

  const answers = detail.locator(".question-card textarea");
  await answers.nth(0).fill("Answer 1");
  await answers.nth(1).fill("Answer 2");
  await detail.locator(".primary-button").click();

  await expect(page.locator(".alert.success")).toBeVisible();
});
