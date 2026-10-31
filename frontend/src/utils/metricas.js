// O número que classifica o ranking e colore o mapa, conforme o critério escolhido.
import { formatarInteiro, formatarTaxa, rotuloTaxa, SEM_DADO } from "./formatacao.js";

export function metrica(item, criterio) {
  if (criterio === "valor") return item.valor ?? null;
  if (criterio === "participacao") return item.participacao?.valor_pct ?? null;
  return item.taxa?.valor ?? null;
}

export function formatarMetrica(numero, criterio) {
  if (criterio === "valor") return formatarInteiro(numero);
  if (criterio === "participacao") {
    return numero === null || numero === undefined ? SEM_DADO : `${formatarTaxa(numero)}%`;
  }
  return formatarTaxa(numero);
}

export function rotuloMetrica({ criterio, indicador, recorte }) {
  if (criterio === "valor") return "Número absoluto";
  if (criterio === "participacao") {
    return recorte ? "Participação no total do indicador" : "Participação no indicador-pai";
  }
  return rotuloTaxa(indicador.base_taxa);
}

// "Taxa por 100 mil habitantes por unidade da federação, 2025", com o recorte, se houver.
export function tituloDoRanking(ranking) {
  const recorte = ranking.recorte ? ` (${ranking.recorte.rotulo})` : "";
  return `${rotuloMetrica(ranking)}${recorte} por unidade da federação, ${ranking.ano}`;
}
