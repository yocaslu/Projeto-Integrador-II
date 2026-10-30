// Formatação dos números para exibição, no padrão brasileiro.

const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const duasCasas = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const SEM_DADO = "Não disponível";

export function formatarInteiro(numero) {
  return numero === null || numero === undefined ? SEM_DADO : inteiro.format(numero);
}

export function formatarTaxa(numero) {
  return numero === null || numero === undefined ? SEM_DADO : duasCasas.format(numero);
}

// Variação com sinal explícito: "+3,10%" e "−3,10%".
export function formatarVariacao(numero) {
  if (numero === null || numero === undefined) return SEM_DADO;
  if (numero === 0) return "0,00%";
  const sinal = numero > 0 ? "+" : "−";
  return `${sinal}${duasCasas.format(Math.abs(numero))}%`;
}

// "100 mil habitantes" → "por 100 mil habitantes"
export function rotuloTaxa(base) {
  return base ? `Taxa por ${base}` : "Taxa";
}
