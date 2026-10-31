import { render, screen, within } from "@testing-library/react";
import { converterRegistro } from "../../api/cliente.js";
import { rankingMvi } from "../../testes/respostas.js";
import GraficoRanking from "./GraficoRanking.jsx";

const ranking = { ...rankingMvi, results: rankingMvi.results.map(converterRegistro) };

test("lista as UFs na ordem do ranking, com as sem dado ao final", () => {
  render(<GraficoRanking ranking={ranking} ufSelecionada="SP" aoSelecionarUf={() => {}} />);

  const linhas = within(screen.getByRole("table", { hidden: true })).getAllByRole("row", {
    hidden: true,
  });
  expect(linhas.map((linha) => linha.textContent)).toEqual([
    "PosiçãoUFTaxa por 100 mil habitantesNúmero absoluto",
    "1ªBahia36,805.200",
    "2ªSão Paulo7,843.615",
    "—AcreNão disponívelNão disponível",
  ]);
  expect(screen.getByText("Sem dado em 2025: Acre.")).toBeInTheDocument();
});

test("usa o critério escolhido na tabela, no título e no CSV", () => {
  const porParticipacao = {
    ...ranking,
    criterio: "participacao",
    results: ranking.results.map((item) => ({
      ...item,
      participacao: { referencia: null, valor_pct: item.posicao ? 12.5 : null },
    })),
  };
  render(<GraficoRanking ranking={porParticipacao} ufSelecionada="SP" aoSelecionarUf={() => {}} />);

  expect(
    screen.getByRole("figure", { name: "Participação no indicador-pai por unidade da federação, 2025" }),
  ).toBeInTheDocument();
  expect(screen.getAllByRole("cell", { name: "12,50%", hidden: true })).toHaveLength(2);
  expect(screen.getByRole("link", { name: /CSV/ })).toHaveAttribute(
    "href",
    "/api/v1/ranking/?indicador=mvi&ano=2025&criterio=participacao&formato=csv",
  );
});

test("aponta o CSV do mesmo ranking", () => {
  render(<GraficoRanking ranking={ranking} ufSelecionada="SP" aoSelecionarUf={() => {}} />);

  expect(
    screen.getByRole("figure", { name: "Taxa por 100 mil habitantes por unidade da federação, 2025" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /CSV/ })).toHaveAttribute(
    "href",
    "/api/v1/ranking/?indicador=mvi&ano=2025&formato=csv",
  );
});
