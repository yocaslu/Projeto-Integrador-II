import { render, screen } from "@testing-library/react";
import App from "./App.jsx";

test("exibe o título, as fontes e o link do repositório", () => {
  render(<App />);

  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "Painel do Anuário Brasileiro de Segurança Pública",
  );
  expect(screen.getByText(/Fórum Brasileiro de Segurança Pública/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /código-fonte/i })).toBeInTheDocument();
});
