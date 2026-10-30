import { render, screen, within } from "@testing-library/react";
import { converterRegistro } from "../../api/cliente.js";
import { comparacaoCurta, comparacaoMvi } from "../../testes/respostas.js";
import GraficoEvolucao, { montarLinhas } from "./GraficoEvolucao.jsx";

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
  expect(screen.getByText(/denominador da taxa em 2025: IBGE – Estimativas/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /CSV/ })).toHaveAttribute(
    "href",
    "/api/v1/comparacao/?uf=SP&indicador=mvi&formato=csv",
  );
  expect(screen.queryByText(/série longa/)).not.toBeInTheDocument();
});

test("avisa quando parte da série usa taxas publicadas pelo FBSP", () => {
  const comparacao = converter(comparacaoMvi);
  comparacao.series[0].pontos[0].taxa.origem = "publicada";
  render(<GraficoEvolucao comparacao={comparacao} />);

  expect(screen.getByText(/Taxas de 2023 a 2023 publicadas pelo FBSP/)).toBeInTheDocument();
});

test("avisa quando a série tem só dois anos e a região não tem taxa", () => {
  render(<GraficoEvolucao comparacao={converter(comparacaoCurta)} />);

  expect(screen.getByText(/dados de 2024 e 2025 no Anuário 2026/)).toBeInTheDocument();
  expect(screen.getByText(/taxa da região Sudeste não está disponível/)).toBeInTheDocument();
  expect(screen.getAllByRole("cell", { name: "Não disponível", hidden: true })).toHaveLength(2);
});
