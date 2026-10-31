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

// RNF01: o contraste também vale no tema escuro.
test("o tema escuro não tem violações WCAG 2.1 AA e fica salvo", async ({ page }) => {
  await abrirPainel(page);
  await page.getByRole("button", { name: "Usar tema escuro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-tema", "escuro");
  for (const resumo of await page.getByText("Ver os dados em tabela").all()) {
    await resumo.click();
  }
  const resultado = await new AxeBuilder({ page }).withTags(ETIQUETAS_WCAG).analyze();
  expect(resultado.violations).toEqual([]);

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-tema", "escuro");
  await expect(page.getByRole("button", { name: "Usar tema claro" })).toBeVisible();
});

test("sem escolha salva, o tema segue o do sistema", async ({ browser }) => {
  const contexto = await browser.newContext({ colorScheme: "dark" });
  const page = await contexto.newPage();
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-tema", "escuro");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-tema", "claro");
  await contexto.close();
});

// O link guarda a seleção: reabrir a URL mostra o mesmo painel.
test("os filtros ficam na URL e podem ser compartilhados", async ({ page }) => {
  await abrirPainel(page);
  await page.locator("#filtro-indicador").selectOption("latrocinio");
  await page.locator("#filtro-uf").selectOption("BA");
  await page.locator("#filtro-unidade").selectOption("ocorrencias");
  await page.locator("#filtro-criterio").selectOption("valor");
  await expect(page).toHaveURL(/indicador=latrocinio/);

  await page.reload();
  await expect(page.locator("#filtro-indicador")).toHaveValue("latrocinio");
  await expect(page.locator("#filtro-uf")).toHaveValue("BA");
  await expect(page.locator("#filtro-unidade")).toHaveValue("ocorrencias");
  await expect(page.locator("#filtro-criterio")).toHaveValue("valor");
  await expect(page.getByText("Número de ocorrências")).toBeVisible();
});

// Link antigo ou digitado à mão não pode levar a erro da API.
test("valores inexistentes na URL voltam ao padrão", async ({ page }) => {
  await page.goto("/?indicador=nada&uf=XX&ano=1900&recorte=99");
  await expect(page.getByRole("heading", { name: "São Paulo em 2025" })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

// RF02: recortes de letalidade; o gráfico fica só com a UF (ADR 0009).
test("o recorte muda o ranking e deixa só a UF na evolução", async ({ page }) => {
  await abrirPainel(page);
  await page.locator("#filtro-indicador").selectOption("morte-intervencao-policial");
  await page.locator("#filtro-recorte").selectOption({ label: "Polícia Militar, em serviço" });
  await expect(page.locator("#legenda-evolucao")).toContainText("Polícia Militar, em serviço");
  await expect(page.locator(".grafico__area--evolucao .recharts-line")).toHaveCount(1);
  await expect(page.locator("#legenda-ranking")).toContainText("Polícia Militar, em serviço");
  await page.locator("#filtro-criterio").selectOption("participacao");
  await expect(page.locator("#legenda-ranking")).toContainText("Participação no total do indicador");
  const resultado = await new AxeBuilder({ page }).withTags(ETIQUETAS_WCAG).analyze();
  expect(resultado.violations).toEqual([]);
});

// RNF01: o mapa funciona pelo teclado, com uma única parada de Tab.
test("o mapa pode ser usado pelo teclado", async ({ page }) => {
  await abrirPainel(page);
  const selecionada = page.locator('.mapa path[tabindex="0"]');
  await expect(selecionada).toHaveCount(1);
  await expect(selecionada).toHaveAttribute("aria-label", /^São Paulo: /);

  await selecionada.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator(".mapa path:focus")).toHaveAttribute("aria-label", /^Sergipe: /);
  await page.keyboard.press("Enter");
  await expect(page.locator("#filtro-uf")).toHaveValue("SE");
  await expect(page.locator(".mapa path:focus")).toHaveAttribute("aria-label", /^Sergipe: /);
  await expect(page.locator('.mapa path[aria-pressed="true"]')).toHaveAttribute(
    "aria-label",
    /^Sergipe: /,
  );
});

// RF06: o mapa usa os dados do ranking e seleciona a UF clicada.
test("clicar em uma UF no mapa troca a UF selecionada", async ({ page }) => {
  await abrirPainel(page);
  await expect(page.locator("#filtro-uf")).toHaveValue("SP");

  // A UF selecionada é a única marcada, com a borda laranja.
  await expect(page.locator('.mapa path[aria-pressed="true"]')).toHaveCount(1);
  const outra = page.locator('.mapa path[aria-pressed="false"]').first();
  await outra.click({ force: true });
  await expect(page.locator("#filtro-uf")).not.toHaveValue("SP");
  await expect(page.locator('.mapa path[aria-pressed="true"]')).toHaveCount(1);
});

test("o rodapé indica as fontes dos dados", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("contentinfo")).toContainText("FBSP");
  await expect(page.getByRole("contentinfo")).toContainText("IBGE");
});
