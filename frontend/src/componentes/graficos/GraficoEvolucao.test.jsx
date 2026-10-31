import { render, screen, within } from "@testing-library/react";
import { converterRegistro } from "../../api/cliente.js";
import { comparacaoCurta, comparacaoMvi } from "../../testes/respostas.js";
import GraficoEvolucao, { fontesPorPeriodo, montarLinhas, revisoesDe } from "./GraficoEvolucao.jsx";

function converter(comparacao) {
  return {
    ...comparacao,
    series: comparacao.series.map((serie) => ({
      ...serie,
      pontos: serie.pontos.map(converterRegistro),
    })),
  };
}

test("monta uma linha por ano com a taxa das três séries", () => {
  const linhas = montarLinhas(converter(comparacaoMvi).series);
  expect(linhas).toEqual([
    { ano: 2023, uf: 8.1, regiao: 13.4, brasil: 21.9 },
    { ano: 2024, uf: 8.15, regiao: 13.2, brasil: 20.6 },
    { ano: 2025, uf: 7.84, regiao: 12.5, brasil: 19.1 },
  ]);
});

test("mostra legenda, tabela, fonte e link do CSV", () => {
  render(<GraficoEvolucao comparacao={converter(comparacaoMvi)} />);

  expect(
    screen.getByText("Taxa por 100 mil habitantes, 2023 a 2025: São Paulo, Sudeste e Brasil"),
  ).toBeInTheDocument();
  const tabela = screen.getByRole("table", { hidden: true });
  expect(within(tabela).getByRole("columnheader", { name: "Sudeste", hidden: true })).toBeInTheDocument();
  expect(within(tabela).getByRole("cell", { name: "7,84", hidden: true })).toBeInTheDocument();
  expect(screen.getByText(/denominador da taxa: IBGE – Estimativas/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /CSV/ })).toHaveAttribute(
    "href",
    "/api/v1/comparacao/?uf=SP&indicador=mvi&formato=csv",
  );
});

test("avisa quando parte da série usa taxas publicadas pelo FBSP", () => {
  const comparacao = converter(comparacaoMvi);
  comparacao.series[0].pontos[0].taxa.origem = "publicada";
  render(<GraficoEvolucao comparacao={comparacao} />);

  expect(screen.getByText(/Taxas de 2023 a 2023 publicadas pelo FBSP/)).toBeInTheDocument();
});

test("indica a fonte do denominador de cada período da série", () => {
  const ponto = (ano, nome) => ({ ano, taxa: { fonte: nome ? { nome } : null } });
  expect(fontesPorPeriodo([ponto(2023, "A"), ponto(2024, "A")])).toBe("A");
  expect(fontesPorPeriodo([ponto(2022, "A"), ponto(2023, "A"), ponto(2024, "B")])).toBe(
    "A (2022 a 2023); B (2024)",
  );
  expect(fontesPorPeriodo([ponto(2024, null)])).toBe("");
});

test("lista os anos revisados pelo FBSP, a partir da observação", () => {
  const comparacao = converter(comparacaoMvi);
  comparacao.series[0].pontos[1].observacao =
    "Nota da tabela. Revisão do FBSP: a edição de 2025 do Anuário publicou 740.";
  expect(revisoesDe(comparacao.series[0].pontos)).toEqual([
    { ano: 2024, texto: "a edição de 2025 do Anuário publicou 740" },
  ]);

  render(<GraficoEvolucao comparacao={comparacao} />);
  expect(screen.getByText(/2024: a edição de 2025 do Anuário publicou 740/)).toBeInTheDocument();
});

test("com recorte, mostra só a UF e leva o recorte e a unidade ao CSV", () => {
  const comparacao = {
    ...converter(comparacaoMvi),
    recorte: { id: 2, rotulo: "Polícia Militar, em serviço" },
  };
  render(<GraficoEvolucao comparacao={comparacao} unidade="vitimas" />);

  expect(
    screen.getByText(/Polícia Militar, em serviço\), 2023 a 2025: São Paulo$/),
  ).toBeInTheDocument();
  expect(screen.queryByRole("columnheader", { name: "Brasil", hidden: true })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /CSV/ })).toHaveAttribute(
    "href",
    "/api/v1/comparacao/?uf=SP&indicador=mvi&unidade=vitimas&recorte=2&formato=csv",
  );
});

test("avisa quando a região não tem taxa", () => {
  render(<GraficoEvolucao comparacao={converter(comparacaoCurta)} />);

  expect(screen.getByText(/taxa da região Sudeste não está disponível/)).toBeInTheDocument();
  expect(screen.getAllByRole("cell", { name: "Não disponível", hidden: true })).toHaveLength(2);
});
