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
import { aplicarMudanca } from "../utils/filtros.js";
import Painel from "./Painel.jsx";

beforeEach(() => window.history.replaceState(null, "", "/"));

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

test("lê os filtros da URL e corrige os valores que não existem", async () => {
  window.history.replaceState(null, "", "/?indicador=feminicidio&uf=XX&ano=1999&criterio=nada");
  const chamadas = simularApi(respostasPadrao());
  render(<Painel />);

  await waitFor(() => {
    expect(chamadas).toContain("/api/v1/comparacao/?uf=SP&indicador=feminicidio");
    expect(chamadas).toContain("/api/v1/ranking/?indicador=feminicidio&ano=2025");
  });
  expect(chamadas.filter((url) => url.includes("XX"))).toEqual([]);
  expect(window.location.search).toBe("?indicador=feminicidio");
});

test("guarda na URL os filtros escolhidos, sem os padrões", async () => {
  simularApi(respostasPadrao());
  render(<Painel />);
  await screen.findByRole("heading", { name: "São Paulo em 2025" });
  expect(window.location.search).toBe("");

  fireEvent.change(screen.getByLabelText("Unidade da federação"), { target: { value: "BA" } });
  fireEvent.change(screen.getByLabelText("Ano do ranking"), { target: { value: "2023" } });
  await waitFor(() => expect(window.location.search).toBe("?uf=BA&ano=2023"));
});

test("o critério do ranking vai para a consulta, e a participação só aparece quando existe", async () => {
  const chamadas = simularApi(respostasPadrao());
  render(<Painel />);
  await screen.findByRole("heading", { name: "São Paulo em 2025" });

  const criterios = within(screen.getByLabelText("Classificar por"));
  expect(criterios.queryByRole("option", { name: "Participação" })).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Classificar por"), { target: { value: "valor" } });
  await waitFor(() =>
    expect(chamadas).toContain("/api/v1/ranking/?indicador=mvi&ano=2025&criterio=valor"),
  );

  fireEvent.change(screen.getByLabelText("Indicador"), { target: { value: "feminicidio" } });
  expect(criterios.getByRole("option", { name: "Participação" })).toBeInTheDocument();
});

test("unidade e recorte só aparecem nos indicadores que os têm", async () => {
  const comOpcoes = JSON.parse(JSON.stringify(metadados));
  Object.assign(comOpcoes.indicadores[0].subtipos[0], {
    unidade_padrao: "vitimas",
    unidades: ["vitimas", "ocorrencias"],
    recortes: [{ id: 2, rotulo: "Polícia Militar, em serviço" }],
  });
  const chamadas = simularApi({ ...respostasPadrao(), "/metadados/": comOpcoes });
  render(<Painel />);
  await screen.findByRole("heading", { name: "São Paulo em 2025" });
  expect(screen.queryByLabelText("Unidade")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Corporação e situação")).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Indicador"), { target: { value: "feminicidio" } });
  fireEvent.change(await screen.findByLabelText("Corporação e situação"), { target: { value: "2" } });
  fireEvent.change(screen.getByLabelText("Unidade"), { target: { value: "ocorrencias" } });
  await waitFor(() =>
    expect(chamadas).toContain(
      "/api/v1/comparacao/?uf=SP&indicador=feminicidio&unidade=ocorrencias&recorte=2",
    ),
  );
});

test("mostra o erro da API sem quebrar a página", async () => {
  simularApi({ ...respostasPadrao(), "/comparacao/": null });
  render(<Painel />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Não encontrado");
  expect(await screen.findByRole("heading", { name: "São Paulo em 2025" })).toBeInTheDocument();
});
