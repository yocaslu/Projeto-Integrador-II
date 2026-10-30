import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import {
  comparacaoCurta,
  comparacaoMvi,
  estados,
  metadados,
  malha,
  rankingMvi,
  simularApi,
} from "../testes/respostas.js";
import Painel, { aplicarMudanca } from "./Painel.jsx";

function respostasPadrao() {
  return {
    "/metadados/": metadados,
    "/estados/": estados,
    "/comparacao/": (url) => (url.includes("feminicidio") ? comparacaoCurta : comparacaoMvi),
    "/ranking/": rankingMvi,
    "/malhas/ufs.json": malha,
  };
}

test("carrega os filtros, os cartões da UF e os dois gráficos", async () => {
  simularApi(respostasPadrao());
  render(<Painel />);

  expect(await screen.findByRole("heading", { name: "São Paulo em 2025" })).toBeInTheDocument();
  const cartoes = within(screen.getByRole("region", { name: "São Paulo em 2025" }));
  expect(cartoes.getByText("7,84")).toBeInTheDocument();
  expect(cartoes.getByText("−3,85%")).toBeInTheDocument();
  expect(cartoes.getByText("2ª de 3")).toBeInTheDocument();
  expect(cartoes.getByText("3.615")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Evolução ao longo dos anos" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Comparação entre estados" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: /Furto/ })).toBeDisabled();
});

test("o ranking pede o último ano do indicador e espera os metadados", async () => {
  const chamadas = simularApi(respostasPadrao());
  render(<Painel />);
  await screen.findByRole("heading", { name: "São Paulo em 2025" });

  const rankings = chamadas.filter((url) => url.startsWith("/api/v1/ranking/"));
  expect(rankings).toEqual(["/api/v1/ranking/?indicador=mvi&ano=2025"]);
});

test("trocar o indicador refaz as consultas e volta ao último ano", async () => {
  const chamadas = simularApi(respostasPadrao());
  render(<Painel />);
  await screen.findByRole("heading", { name: "São Paulo em 2025" });

  fireEvent.change(screen.getByLabelText("Ano do ranking"), { target: { value: "2023" } });
  await waitFor(() =>
    expect(chamadas).toContain("/api/v1/ranking/?indicador=mvi&ano=2023"),
  );

  fireEvent.change(screen.getByLabelText("Indicador"), { target: { value: "feminicidio" } });
  await waitFor(() => {
    expect(chamadas).toContain("/api/v1/comparacao/?uf=SP&indicador=feminicidio");
    expect(chamadas).toContain("/api/v1/ranking/?indicador=feminicidio&ano=2025");
  });
  expect(await screen.findByText(/taxa da região Sudeste não está disponível/)).toBeInTheDocument();
});

test("a região restringe as UFs e o ranking e leva a uma UF dela", async () => {
  const chamadas = simularApi(respostasPadrao());
  render(<Painel />);
  await screen.findByRole("heading", { name: "São Paulo em 2025" });

  fireEvent.change(screen.getByLabelText("Região"), { target: { value: "NE" } });

  const ufs = within(screen.getByLabelText("Unidade da federação"));
  expect(ufs.getByRole("option", { name: /Bahia/ })).toBeInTheDocument();
  expect(ufs.queryByRole("option", { name: /São Paulo/ })).not.toBeInTheDocument();
  expect(screen.getByLabelText("Unidade da federação")).toHaveValue("BA");
  expect(screen.getByText(/Mostrando as UFs da região Nordeste/)).toBeInTheDocument();
  await waitFor(() => expect(chamadas).toContain("/api/v1/comparacao/?uf=BA&indicador=mvi"));
});

test("escolher uma UF fora da região limpa a região", () => {
  const atuais = { indicador: "mvi", regiao: "NE", uf: "BA", ano: null };
  expect(aplicarMudanca(atuais, { uf: "SP" }, estados)).toMatchObject({ regiao: "", uf: "SP" });
  expect(aplicarMudanca(atuais, { uf: "BA" }, estados)).toMatchObject({ regiao: "NE", uf: "BA" });
  expect(aplicarMudanca(atuais, { regiao: "" }, estados)).toMatchObject({ regiao: "", uf: "BA" });
});

test("sem metadados, o ranking mostra o erro em vez de carregar para sempre", async () => {
  simularApi({ ...respostasPadrao(), "/metadados/": null });
  render(<Painel />);

  expect((await screen.findAllByRole("alert")).length).toBeGreaterThan(0);
  expect(screen.queryByText("Carregando…")).not.toBeInTheDocument();
});

test("mostra o erro da API sem quebrar a página", async () => {
  simularApi({ ...respostasPadrao(), "/comparacao/": null });
  render(<Painel />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Não encontrado");
  expect(await screen.findByRole("heading", { name: "São Paulo em 2025" })).toBeInTheDocument();
});
