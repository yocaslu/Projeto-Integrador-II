import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import {
  comparacaoCurta,
  comparacaoMvi,
  estados,
  metadados,
  rankingMvi,
  simularApi,
} from "../testes/respostas.js";
import Painel from "./Painel.jsx";

function respostasPadrao() {
  return {
    "/metadados/": metadados,
    "/estados/": estados,
    "/comparacao/": (url) => (url.includes("feminicidio") ? comparacaoCurta : comparacaoMvi),
    "/ranking/": rankingMvi,
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
  expect(await screen.findByText(/dados de 2024 e 2025/)).toBeInTheDocument();
});

test("mostra o erro da API sem quebrar a página", async () => {
  simularApi({ ...respostasPadrao(), "/comparacao/": null });
  render(<Painel />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Não encontrado");
  expect(await screen.findByRole("heading", { name: "São Paulo em 2025" })).toBeInTheDocument();
});
