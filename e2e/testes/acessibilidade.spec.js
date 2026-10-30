import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

// Espera os filtros, os cartões e os dois gráficos, para que o axe analise a página completa.
async function abrirPainel(page) {
  await page.goto("/");
  await expect(page.getByText("Posição entre as UFs")).toBeVisible();
  await expect(page.locator(".recharts-line").first()).toBeVisible();
  await expect(page.locator(".recharts-bar-rectangle").first()).toBeVisible();
}

// RNF01: a interface deve atender à WCAG 2.1 nível AA.
test("o painel carregado não tem violações WCAG 2.1 AA", async ({ page }) => {
  await abrirPainel(page);
  const resultado = await new AxeBuilder({ page }).withTags(ETIQUETAS_WCAG).analyze();
  expect(resultado.violations).toEqual([]);
});

test("as tabelas de dados abertas não têm violações WCAG 2.1 AA", async ({ page }) => {
  await abrirPainel(page);
  for (const resumo of await page.getByText("Ver os dados em tabela").all()) {
    await resumo.click();
  }
  await expect(page.getByRole("table")).toHaveCount(2);
  const resultado = await new AxeBuilder({ page }).withTags(ETIQUETAS_WCAG).analyze();
  expect(resultado.violations).toEqual([]);
});

// RF03 e RF04: os filtros mudam o gráfico de evolução e o ranking.
test("os filtros atualizam os cartões e os gráficos", async ({ page }) => {
  await abrirPainel(page);
  await page.locator("#filtro-indicador").selectOption("feminicidio");
  await page.locator("#filtro-uf").selectOption("BA");
  await expect(page.getByRole("heading", { name: "Bahia em 2025" })).toBeVisible();
  await expect(page.locator("#legenda-evolucao")).toContainText(
    "Taxa por 100 mil mulheres, 2024 a 2025: Bahia, Nordeste e Brasil",
  );
  await expect(page.locator("#legenda-ranking")).toContainText("100 mil mulheres");

  await page.locator("#filtro-ano").selectOption("2024");
  await expect(page.getByRole("heading", { name: "Bahia em 2024" })).toBeVisible();
});

test("o rodapé indica as fontes dos dados", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("contentinfo")).toContainText("FBSP");
  await expect(page.getByRole("contentinfo")).toContainText("IBGE");
});
