import { render, screen } from "@testing-library/react";
import App from "./App.jsx";
import { comparacaoMvi, estados, metadados, rankingMvi, simularApi } from "./testes/respostas.js";

test("exibe o título, as fontes e o link do repositório", async () => {
  simularApi({
    "/metadados/": metadados,
    "/estados/": estados,
    "/comparacao/": comparacaoMvi,
    "/ranking/": rankingMvi,
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
