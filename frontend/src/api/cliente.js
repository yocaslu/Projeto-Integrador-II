// Cliente da API. Valores e taxas chegam como texto ("41.2") para preservar a precisão
// do NUMERIC no backend; a conversão para número acontece aqui, antes dos gráficos.

export const API_URL = "/api/v1";

export function paraNumero(texto) {
  if (texto === null || texto === undefined) return null;
  const numero = Number(texto);
  return Number.isFinite(numero) ? numero : null;
}

export function converterRegistro(registro) {
  return {
    ...registro,
    valor: paraNumero(registro.valor),
    taxa: registro.taxa ? { ...registro.taxa, valor: paraNumero(registro.taxa.valor) } : null,
    taxa_publicada: paraNumero(registro.taxa_publicada),
    variacao: registro.variacao
      ? {
          ...registro.variacao,
          valor_pct: paraNumero(registro.variacao.valor_pct),
          taxa_pct: paraNumero(registro.variacao.taxa_pct),
        }
      : null,
  };
}

export async function buscar(caminho, parametros = {}) {
  const consulta = new URLSearchParams(parametros).toString();
  const resposta = await fetch(`${API_URL}${caminho}${consulta ? `?${consulta}` : ""}`);
  if (!resposta.ok) {
    // Erros chegam no formato Problem Details (RFC 9457)
    const problema = await resposta.json().catch(() => ({}));
    throw new Error(problema.detail ?? `Erro ${resposta.status}`);
  }
  return resposta.json();
}
