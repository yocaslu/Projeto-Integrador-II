// Cliente da API. Valores e taxas chegam como texto ("41.2") para preservar a precisão
// do NUMERIC no backend; a conversão para número acontece aqui, antes dos gráficos.

export const API_URL = "/api/v1";

export function paraNumero(texto) {
  if (texto === null || texto === undefined) return null;
  const numero = Number(texto);
  return Number.isFinite(numero) ? numero : null;
}

// Serve para registros de /registros/, pontos de /comparacao/ e itens de /ranking/,
// que têm os mesmos campos numéricos.
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
    participacao: registro.participacao
      ? { ...registro.participacao, valor_pct: paraNumero(registro.participacao.valor_pct) }
      : null,
  };
}

// Monta a URL de um recurso, sem parâmetros vazios: a API responde 400 a parâmetro vazio.
export function urlApi(caminho, parametros = {}) {
  const definidos = Object.entries(parametros).filter(
    ([, valor]) => valor !== null && valor !== undefined && valor !== "",
  );
  const consulta = new URLSearchParams(definidos).toString();
  return `${API_URL}${caminho}${consulta ? `?${consulta}` : ""}`;
}

export async function buscar(caminho, parametros = {}, { signal } = {}) {
  const resposta = await fetch(urlApi(caminho, parametros), { signal });
  if (!resposta.ok) {
    // Erros chegam no formato Problem Details (RFC 9457)
    const problema = await resposta.json().catch(() => ({}));
    throw new Error(problema.detail ?? `Erro ${resposta.status}`);
  }
  return resposta.json();
}

export function buscarMetadados(opcoes) {
  return buscar("/metadados/", {}, opcoes);
}

export function buscarEstados(opcoes) {
  return buscar("/estados/", {}, opcoes);
}

export async function buscarComparacao(parametros, opcoes) {
  const dados = await buscar("/comparacao/", parametros, opcoes);
  return {
    ...dados,
    series: dados.series.map((serie) => ({
      ...serie,
      pontos: serie.pontos.map(converterRegistro),
    })),
  };
}

export async function buscarRanking(parametros, opcoes) {
  const dados = await buscar("/ranking/", parametros, opcoes);
  return { ...dados, results: dados.results.map(converterRegistro) };
}
