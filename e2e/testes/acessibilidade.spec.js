import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

// Espera os filtros, os cartões e os dois gráficos, para que o axe analise a página completa.
async function abrirPainel(page) {
  await page.goto("/");
  await expect(page.getByText("Posição entre as UFs")).toBeVisible();
  await expect(page.locator(".recharts-line").first()).toBeVisible();
  await expect(page.locator(".recharts-bar-rectangle").first()).toBeVisible();
  await expect(page.locator(".mapa path.leaflet-interactive")).toHaveCount(27);
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

// RF04: a região restringe a lista de UFs e o ranking.
test("o filtro de região restringe as UFs e o ranking", async ({ page }) => {
  await abrirPainel(page);
  await page.locator("#filtro-regiao").selectOption("S");
  await expect(page.locator("#filtro-uf option")).toHaveCount(3);
  await expect(page.locator(".recharts-bar-rectangle")).toHaveCount(3);
  await expect(page.locator(".mapa path.leaflet-interactive")).toHaveCount(27);
});

// RF03 e RF04: os filtros mudam o gráfico de evolução e o ranking.
test("os filtros atualizam os cartões e os gráficos", async ({ page }) => {
  await abrirPainel(page);
  await page.locator("#filtro-indicador").selectOption("feminicidio");
  await page.locator("#filtro-uf").selectOption("BA");
  await expect(page.getByRole("heading", { name: "Bahia em 2025" })).toBeVisible();
  await expect(page.locator("#legenda-evolucao")).toContainText(
    "Taxa por 100 mil mulheres, 2022 a 2025: Bahia, Nordeste e Brasil",
  );
  await expect(page.locator("#legenda-ranking")).toContainText("100 mil mulheres");

  await page.locator("#filtro-ano").selectOption("2022");
  await expect(page.getByRole("heading", { name: "Bahia em 2022" })).toBeVisible();
});

// RF06: o mapa usa os dados do ranking e seleciona a UF clicada.
test("clicar em uma UF no mapa troca a UF selecionada", async ({ page }) => {
  await abrirPainel(page);
  await expect(page.locator("#filtro-uf")).toHaveValue("SP");

  // A UF selecionada é a única com borda laranja.
  await expect(page.locator('.mapa path[stroke="#b35c00"]')).toHaveCount(1);
  const outra = page.locator('.mapa path.leaflet-interactive:not([stroke="#b35c00"])').first();
  await outra.click({ force: true });
  await expect(page.locator("#filtro-uf")).not.toHaveValue("SP");
  await expect(page.locator('.mapa path[stroke="#b35c00"]')).toHaveCount(1);
});

test("o rodapé indica as fontes dos dados", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("contentinfo")).toContainText("FBSP");
  await expect(page.getByRole("contentinfo")).toContainText("IBGE");
});
