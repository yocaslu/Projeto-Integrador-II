// Paleta dos gráficos (RNF01): azul, laranja e neutro se distinguem nos três tipos comuns de
// daltonismo, e todos passam de 3:1 de contraste sobre o fundo de cada tema (WCAG 1.4.11). As
// séries também diferem pelo traço e pelo marcador, para não depender só da cor. Os valores ficam
// em src/estilos/global.css, um para cada tema; trocar de tema não redesenha os gráficos.
export const CORES = {
  uf: "var(--grafico-uf)",
  regiao: "var(--grafico-regiao)",
  brasil: "var(--grafico-brasil)",
  barra: "var(--grafico-barra)",
  barraDestaque: "var(--grafico-uf)",
  grade: "var(--cor-borda)",
};
