import { fireEvent, render, screen } from "@testing-library/react";
import { converterRegistro } from "../../api/cliente.js";
import { malha, rankingMvi, simularApi } from "../../testes/respostas.js";
import { CORES } from "../../utils/cores.js";
import { COR_SEM_DADO, ESCALA } from "../../utils/mapa.js";
import MapaUfs from "./MapaUfs.jsx";

const ranking = { ...rankingMvi, results: rankingMvi.results.map(converterRegistro) };

function uf(codarea) {
  return screen.getByTestId("malha").querySelector(`[data-codarea="${codarea}"]`);
}

test("pinta cada UF pela taxa do ranking e destaca a selecionada", async () => {
  simularApi({ "/malhas/ufs.json": malha });
  render(<MapaUfs ranking={ranking} ufSelecionada="SP" aoSelecionarUf={() => {}} />);
  await screen.findByTestId("malha");

  expect(uf("29")).toHaveAttribute("data-cor", ESCALA[4]);
  expect(uf("35")).toHaveAttribute("data-cor", ESCALA[0]);
  expect(uf("12")).toHaveAttribute("data-cor", COR_SEM_DADO);
  expect(uf("35")).toHaveAttribute("data-borda", CORES.regiao);
  expect(uf("29")).toHaveAttribute("data-borda", CORES.brasil);
  expect(uf("29")).toHaveTextContent("Bahia: 36,80");
  expect(uf("12")).toHaveTextContent("Acre: Não disponível");
});

test("mostra a legenda com as faixas e a fonte da malha", async () => {
  simularApi({ "/malhas/ufs.json": malha });
  render(<MapaUfs ranking={ranking} ufSelecionada="SP" aoSelecionarUf={() => {}} />);
  await screen.findByTestId("malha");

  const legenda = screen.getByRole("list", { name: "Legenda do mapa" });
  expect(legenda).toHaveTextContent("7,84 a 7,84");
  expect(legenda).toHaveTextContent("36,80 a 36,80");
  expect(legenda).toHaveTextContent("Não disponível");
  expect(screen.getByText(/malha das UFs: IBGE/)).toBeInTheDocument();
});

test("clicar em uma UF a seleciona", async () => {
  simularApi({ "/malhas/ufs.json": malha });
  const aoSelecionarUf = jest.fn();
  render(<MapaUfs ranking={ranking} ufSelecionada="SP" aoSelecionarUf={aoSelecionarUf} />);
  await screen.findByTestId("malha");

  fireEvent.click(uf("29"));
  expect(aoSelecionarUf).toHaveBeenCalledWith("BA");
});

test("avisa quando a malha não foi baixada, sem esconder a legenda", async () => {
  simularApi({});
  render(<MapaUfs ranking={ranking} ufSelecionada="SP" aoSelecionarUf={() => {}} />);

  expect(await screen.findByRole("alert")).toHaveTextContent("malha das UFs não encontrada");
  expect(screen.getByRole("list", { name: "Legenda do mapa" })).toBeInTheDocument();
});
