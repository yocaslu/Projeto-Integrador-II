import "@testing-library/jest-dom";
import { configure } from "@testing-library/react";

// Com a máquina ocupada, o limite padrão de 1 s das buscas assíncronas gera falhas falsas.
configure({ asyncUtilTimeout: 4000 });

// O jsdom não tem ResizeObserver, usado pelo ResponsiveContainer do Recharts. Sem tamanho,
// o SVG não é desenhado; os testes conferem as tabelas, os textos e os links.
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Sem tamanho no jsdom, o Recharts avisa a cada gráfico; o aviso não diz nada sobre o teste.
const avisar = console.warn;
console.warn = (mensagem, ...resto) => {
  if (typeof mensagem === "string" && mensagem.includes("of chart should be greater than 0")) return;
  avisar(mensagem, ...resto);
};
