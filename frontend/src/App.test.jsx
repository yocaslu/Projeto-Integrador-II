import { fireEvent, render, screen } from "@testing-library/react";
import App from "./App.jsx";
import {
  comparacaoMvi,
  estados,
  malha,
  metadados,
  rankingMvi,
  simularApi,
} from "./testes/respostas.js";

function respostas() {
  simularApi({
    "/metadados/": metadados,
    "/estados/": estados,
    "/comparacao/": comparacaoMvi,
    "/ranking/": rankingMvi,
    "/malhas/ufs.json": malha,
  });
}

beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.tema;
});

test("alterna o tema e guarda a escolha", async () => {
  respostas();
  render(<App />);
  await screen.findByRole("heading", { name: "São Paulo em 2025" });

  fireEvent.click(screen.getByRole("button", { name: "Usar tema escuro" }));
  expect(document.documentElement.dataset.tema).toBe("escuro");
  expect(localStorage.getItem("tema")).toBe("escuro");

  fireEvent.click(screen.getByRole("button", { name: "Usar tema claro" }));
  expect(document.documentElement.dataset.tema).toBe("claro");
  expect(localStorage.getItem("tema")).toBe("claro");
});

test("exibe o título, as fontes e o link do repositório", async () => {
  simularApi({
    "/metadados/": metadados,
    "/estados/": estados,
    "/comparacao/": comparacaoMvi,
    "/ranking/": rankingMvi,
    "/malhas/ufs.json": malha,
  });
  render(<App />);

  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "Painel do Anuário Brasileiro de Segurança Pública",
  );
  expect(screen.getByText(/Fórum Brasileiro de Segurança Pública/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /código-fonte/i })).toBeInTheDocument();
  // Espera a carga terminar, para não deixar atualizações de estado fora do teste.
  expect(await screen.findByRole("heading", { name: "São Paulo em 2025" })).toBeInTheDocument();
});
