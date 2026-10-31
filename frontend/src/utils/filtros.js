// Filtros do painel: valores iniciais, leitura e escrita na URL (para compartilhar a seleção) e
// correção de valores que não existem, como os de um link antigo ou digitado à mão.

export const FILTROS_INICIAIS = {
  indicador: "mvi",
  regiao: "",
  uf: "SP",
  ano: null,
  unidade: "",
  recorte: "",
  criterio: "taxa",
};

export function lerFiltrosDaUrl(busca = window.location.search) {
  const parametros = new URLSearchParams(busca);
  const filtros = { ...FILTROS_INICIAIS };
  for (const nome of Object.keys(filtros)) {
    const valor = parametros.get(nome);
    if (valor) filtros[nome] = nome === "ano" ? Number(valor) : valor;
  }
  return filtros;
}

// Só o que difere do padrão entra na URL. O ano mais recente também fica de fora, para o link
// continuar mostrando o último ano quando sair uma nova edição.
export function buscaDosFiltros(filtros, ultimoAno) {
  const parametros = new URLSearchParams();
  for (const [nome, valor] of Object.entries(filtros)) {
    if (nome === "ano" && valor === ultimoAno) continue;
    if (valor !== FILTROS_INICIAIS[nome] && valor !== null) parametros.set(nome, valor);
  }
  const busca = parametros.toString();
  return busca ? `?${busca}` : "";
}

// Região e UF ficam sempre coerentes: escolher uma região fora da UF atual leva à primeira UF
// dela; escolher (no mapa ou no ranking) uma UF fora da região atual limpa a região. Trocar de
// indicador volta o ano, a unidade e o recorte aos padrões.
export function aplicarMudanca(atuais, mudanca, estados) {
  const novos = { ...atuais, ...mudanca };
  if ("indicador" in mudanca) Object.assign(novos, { ano: null, unidade: "", recorte: "" });
  const daRegiao = (uf, regiao) =>
    estados.some((estado) => estado.sigla === uf && estado.regiao.sigla === regiao);
  if (!novos.regiao || daRegiao(novos.uf, novos.regiao)) return novos;
  if ("regiao" in mudanca) {
    const primeira = estados.find((estado) => estado.regiao.sigla === novos.regiao);
    return { ...novos, uf: primeira?.sigla ?? novos.uf };
  }
  return { ...novos, regiao: "" };
}

// Os critérios que a API aceita: participação só existe com recorte ou com indicador-pai.
export function criteriosDe(indicador, recorte) {
  const criterios = [
    { valor: "taxa", rotulo: "Taxa" },
    { valor: "valor", rotulo: "Número absoluto" },
  ];
  if (recorte || indicador?.tem_participacao) {
    criterios.push({ valor: "participacao", rotulo: "Participação" });
  }
  return criterios;
}

// Filtros com valores válidos para os metadados e as UFs recebidos; a API responderia 400 aos demais.
export function corrigirFiltros(filtros, indicadores, estados) {
  const comRegistros = indicadores.filter((item) => item.possui_registros);
  const indicador =
    comRegistros.find((item) => item.slug === filtros.indicador) ??
    comRegistros.find((item) => item.slug === FILTROS_INICIAIS.indicador) ??
    comRegistros[0];
  const estado = estados.find((item) => item.sigla === filtros.uf);
  const uf = estado ? filtros.uf : FILTROS_INICIAIS.uf;
  const regioes = estados.filter((item) => item.sigla === uf).map((item) => item.regiao.sigla);
  const anos = indicador?.anos ?? [];
  const recorte = indicador?.recortes?.some((item) => String(item.id) === filtros.recorte)
    ? filtros.recorte
    : "";
  const criterio = criteriosDe(indicador, recorte).some((item) => item.valor === filtros.criterio)
    ? filtros.criterio
    : "taxa";
  return {
    indicador: indicador?.slug ?? FILTROS_INICIAIS.indicador,
    regiao: regioes.includes(filtros.regiao) ? filtros.regiao : "",
    uf,
    ano: anos.includes(filtros.ano) ? filtros.ano : (anos.at(-1) ?? null),
    unidade: indicador?.unidades?.includes(filtros.unidade) ? filtros.unidade : "",
    recorte,
    criterio,
  };
}
