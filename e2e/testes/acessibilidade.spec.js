import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// RNF01: a interface deve atender à WCAG 2.1 nível AA.
test("a página inicial não tem violações WCAG 2.1 AA", async ({ page }) => {
  await page.goto("/");

  const resultado = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  expect(resultado.violations).toEqual([]);
});

test("o rodapé indica as fontes dos dados", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("contentinfo")).toContainText("FBSP");
  await expect(page.getByRole("contentinfo")).toContainText("IBGE");
});
