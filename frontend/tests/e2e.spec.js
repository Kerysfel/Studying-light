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

test("session prompt -> import part -> open review", async ({ page }) => {
  const markdownSummary =
    "## Сводка\n\n### Ключевые идеи\n- Идея 1\n- Идея 2\n\n### Термины/инварианты\n- Термин 1\n";

  await page.route("**/api/v1/books", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: 1, title: "Sample Book", author: "Author", status: "active" },
      ]),
    });
  });

  await page.route("**/api/v1/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });

  await page.route("**/api/v1/parts?book_id=1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 10,
          book_id: 1,
          part_index: 1,
          label: "Part 1",
          created_at: "2024-10-10T10:00:00",
          gpt_summary: markdownSummary,
        },
      ]),
    });
  });

  await page.route("**/api/v1/algorithm-groups", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/prompts/generate_summary_and_questions", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/plain",
      body: "Prompt {{book_title}} {{part_index}}",
    });
  });

  await page.route("**/api/v1/parts/10/import_gpt", async (route) => {
    const request = route.request();
    const payload = JSON.parse(request.postData() || "{}");
    expect(payload.gpt_summary).toBe(markdownSummary);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        reading_part: {
          id: 10,
          book_id: 1,
          part_index: 1,
          label: "Part 1",
          created_at: "2024-10-10T10:00:00",
          gpt_summary: markdownSummary,
        },
        review_items: [
          {
            id: 55,
            reading_part_id: 10,
            interval_days: 1,
            due_date: "2024-10-11",
            status: "planned",
            book_id: 1,
            book_title: "Sample Book",
            part_index: 1,
            label: "Part 1",
          },
        ],
      }),
    });
  });

  await page.route("**/api/v1/reviews/today", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 55,
          reading_part_id: 10,
          interval_days: 1,
          due_date: "2024-10-11",
          status: "planned",
          book_id: 1,
          book_title: "Sample Book",
          part_index: 1,
          label: "Part 1",
          gpt_rating_1_to_5: 4,
        },
      ]),
    });
  });

  await page.route("**/api/v1/reviews/stats", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/api/v1/algorithm-reviews/today", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/api/v1/algorithm-reviews/stats", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/api/v1/reviews/55", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 55,
        reading_part_id: 10,
        interval_days: 1,
        due_date: "2024-10-11",
        status: "planned",
        book_id: 1,
        book_title: "Sample Book",
        part_index: 1,
        label: "Part 1",
        summary: markdownSummary,
        questions: ["Question 1", "Question 2"],
      }),
    });
  });

  await page.route("**/api/v1/reviews/55/complete", async (route) => {
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

  await page.goto("/session");
  await page
    .locator('.form-block:has(label:has-text("Книга")) select')
    .selectOption("1");
  await page.getByRole("button", { name: "Сгенерировать промпт" }).click();
  await expect(page.locator(".modal")).toBeVisible();
  await page.getByRole("button", { name: "Закрыть" }).first().click();

  await page.goto("/import");
  await page
    .locator('.form-block:has(label:has-text("Книга")) select')
    .selectOption("1");
  await page
    .locator('.form-block:has(label:has-text("Часть")) select')
    .selectOption("10");
  const partPanel = page.locator("section.panel").first();
  await partPanel
    .locator("textarea")
    .fill(
      JSON.stringify(
        {
          gpt_summary: markdownSummary,
          gpt_questions_by_interval: {
            1: ["Q1"],
            7: ["Q2"],
            16: ["Q3"],
            35: ["Q4"],
            90: ["Q5"],
          },
        },
        null,
        2
      )
    );
  await partPanel.getByRole("button", { name: "Импортировать" }).click();
  await expect(page.locator(".alert.success")).toBeVisible();

  await page.goto("/reviews");
  await page.locator(".review-list-item .primary-button").first().click();
  const detail = page.locator(".review-detail");
  await expect(detail).toBeVisible();
  const answers = detail.locator(".question-card textarea");
  await answers.nth(0).fill("Answer 1");
  await answers.nth(1).fill("Answer 2");
  await detail.getByRole("button", { name: "Завершить повторение" }).click();
  await expect(page.locator(".alert.success")).toBeVisible();
});

test("import algorithms -> dictionary -> detail", async ({ page }) => {
  await page.route("**/api/v1/books", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/api/v1/algorithm-groups", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 5,
          title: "Graphs",
          description: "Graph algorithms",
          notes: null,
          algorithms_count: 1,
        },
      ]),
    });
  });

  await page.route("**/api/v1/algorithms/import", async (route) => {
    const payload = JSON.parse(route.request().postData() || "{}");
    expect(payload.algorithms).toHaveLength(1);
    expect(payload.algorithms[0].group_id).toBe(5);
    expect(payload.algorithms[0].group_title_new).toBeUndefined();
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        groups_created: 0,
        algorithms_created: [
          {
            algorithm_id: 12,
            group_id: 5,
          },
        ],
        review_items_created: 5,
      }),
    });
  });

  await page.route("**/api/v1/algorithm-groups/5", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 5,
        title: "Graphs",
        description: "Graph algorithms",
        notes: null,
        algorithms_count: 1,
        algorithms: [
          {
            id: 12,
            title: "BFS",
            summary: "Traversal",
            complexity: "O(V+E)",
          },
        ],
      }),
    });
  });

  await page.route("**/api/v1/algorithms/12", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 12,
        group_id: 5,
        group_title: "Graphs",
        title: "BFS",
        summary: "Traversal",
        when_to_use: "Graph traversal",
        complexity: "O(V+E)",
        invariants: ["Queue keeps frontier"],
        steps: ["Init", "Visit"],
        corner_cases: ["Disconnected"],
        source_part: null,
        code_snippets: [
          {
            id: 1,
            code_kind: "pseudocode",
            language: "text",
            code_text: "BFS(G)",
            is_reference: true,
            created_at: "2024-10-10T10:00:00",
          },
        ],
        review_items_count: 5,
      }),
    });
  });

  await page.route("**/api/v1/algorithm-trainings?algorithm_id=12", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.goto("/import");
  const panels = page.locator("section.panel");
  const algorithmPanel = panels.nth(1);
  await algorithmPanel
    .locator("textarea")
    .fill(
      JSON.stringify(
        {
          group_suggestions: ["Graphs"],
          algorithms: [
            {
              title: "BFS",
              summary: "Traversal",
              when_to_use: "Graph traversal",
              complexity: "O(V+E)",
              invariants: ["Queue keeps frontier"],
              steps: ["Init", "Visit"],
              corner_cases: ["Disconnected"],
              review_questions_by_interval: {
                1: ["Q1"],
                7: ["Q2"],
                16: ["Q3"],
                35: ["Q4"],
                90: ["Q5"],
              },
              code: {
                code_kind: "pseudocode",
                language: "text",
                code_text: "BFS(G)",
              },
              suggested_group: "Graphs",
            },
          ],
        },
        null,
        2
      )
    );
  await algorithmPanel.getByRole("button", { name: "Разобрать JSON" }).click();
  const groupSelect = algorithmPanel.locator(".algorithm-card select");
  await groupSelect.selectOption("existing-5");
  await algorithmPanel.getByRole("button", { name: "Импортировать" }).click();
  await expect(page.locator(".alert.success")).toBeVisible();

  await page.goto("/algorithm-groups");
  await page.getByRole("link", { name: "Открыть" }).click();
  await expect(page.locator(".panel-header h2")).toHaveText("Graphs");
  await page.getByRole("link", { name: "Открыть" }).click();
  await expect(page.locator(".summary-title")).toContainText("Кратко");
});
