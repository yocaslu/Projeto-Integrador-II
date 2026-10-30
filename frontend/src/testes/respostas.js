// Respostas reduzidas da API, no formato do contrato, para os testes dos componentes.

const fonte = { id: 1, nome: "Secretarias Estaduais (compilação FBSP)" };
const fonteTaxa = { id: 2, nome: "IBGE – Estimativas da população residente" };

function ponto(ano, valor, taxa, extras = {}) {
  return {
    ano,
    valor: valor === null ? null : String(valor),
    situacao: valor === null ? "nao_disponivel" : "informado",
    metodo: "publicado",
    taxa: {
      valor: taxa === null ? null : String(taxa),
      base: "100 mil habitantes",
      origem: taxa === null ? null : "calculada",
      fonte: taxa === null ? null : fonteTaxa,
    },
    variacao: { ano_referencia: ano - 1, valor_pct: null, taxa_pct: null },
    participacao: { referencia: null, valor_pct: null },
    fonte,
    observacao: null,
    ...extras,
  };
}

export const metadados = {
  anos: { min: 2012, max: 2025 },
  indicadores: [
    {
      slug: "mvi",
      nome: "Mortes Violentas Intencionais",
      base_taxa: "100 mil habitantes",
      possui_registros: true,
      anos: [2023, 2024, 2025],
      subtipos: [
        {
          slug: "feminicidio",
          nome: "Feminicídio",
          base_taxa: "100 mil mulheres",
          possui_registros: true,
          anos: [2024, 2025],
          subtipos: [],
        },
      ],
    },
    {
      slug: "furto",
      nome: "Furto",
      base_taxa: null,
      possui_registros: false,
      anos: [],
      subtipos: [],
    },
  ],
};

export const estados = [
  { sigla: "BA", nome: "Bahia", codigo_ibge: "29", regiao: { sigla: "NE", nome: "Nordeste" } },
  { sigla: "SP", nome: "São Paulo", codigo_ibge: "35", regiao: { sigla: "SE", nome: "Sudeste" } },
];

const localidades = {
  SP: { nivel: "uf", codigo: "SP", codigo_ibge: "35", nome: "São Paulo" },
  BA: { nivel: "uf", codigo: "BA", codigo_ibge: "29", nome: "Bahia" },
  SE: { nivel: "regiao", codigo: "SE", codigo_ibge: "3", nome: "Sudeste" },
  BR: { nivel: "pais", codigo: "BR", codigo_ibge: "1", nome: "Brasil" },
};

export const comparacaoMvi = {
  indicador: { slug: "mvi", nome: "Mortes Violentas Intencionais", base_taxa: "100 mil habitantes" },
  unidade: "vitimas",
  recorte: null,
  ano_min: 2023,
  ano_max: 2025,
  series: [
    { localidade: localidades.SP, pontos: [ponto(2023, 3700, 8.1), ponto(2024, 3800, 8.15), ponto(2025, 3615, 7.84)] },
    { localidade: localidades.SE, pontos: [ponto(2023, 12000, 13.4), ponto(2024, 11800, 13.2), ponto(2025, 11000, 12.5)] },
    { localidade: localidades.BR, pontos: [ponto(2023, 46000, 21.9), ponto(2024, 44000, 20.6), ponto(2025, 41000, 19.1)] },
  ],
};

// Dois anos e região sem taxa, como no feminicídio.
export const comparacaoCurta = {
  ...comparacaoMvi,
  indicador: { slug: "feminicidio", nome: "Feminicídio", base_taxa: "100 mil mulheres" },
  ano_min: 2024,
  ano_max: 2025,
  series: [
    { localidade: localidades.SP, pontos: [ponto(2024, 50, 1.1), ponto(2025, 52, 1.14)] },
    { localidade: localidades.SE, pontos: [ponto(2024, 300, null), ponto(2025, 310, null)] },
    { localidade: localidades.BR, pontos: [ponto(2024, 1400, 1.37), ponto(2025, 1450, 1.43)] },
  ],
};

export const rankingMvi = {
  indicador: { slug: "mvi", nome: "Mortes Violentas Intencionais", base_taxa: "100 mil habitantes" },
  ano: 2025,
  criterio: "taxa",
  unidade: "vitimas",
  recorte: null,
  results: [
    {
      posicao: 1,
      localidade: localidades.BA,
      ...ponto(2025, 5200, 36.8, {
        variacao: { ano_referencia: 2024, valor_pct: "-4.00", taxa_pct: "-4.20" },
      }),
    },
    {
      posicao: 2,
      localidade: localidades.SP,
      ...ponto(2025, 3615, 7.84, {
        variacao: { ano_referencia: 2024, valor_pct: "-3.50", taxa_pct: "-3.85" },
      }),
    },
    {
      posicao: null,
      localidade: { nivel: "uf", codigo: "AC", codigo_ibge: "12", nome: "Acre" },
      ...ponto(2025, null, null),
    },
  ].map(({ ano: _ano, ...item }) => item),
};

// Simula o fetch da API a partir do caminho pedido; guarda as URLs para os testes.
export function simularApi(respostas) {
  const chamadas = [];
  global.fetch = jest.fn(async (url) => {
    chamadas.push(url);
    const caminho = url.replace("/api/v1", "").split("?")[0];
    const corpo = typeof respostas[caminho] === "function" ? respostas[caminho](url) : respostas[caminho];
    if (!corpo) return { ok: false, status: 404, json: async () => ({ detail: "Não encontrado" }) };
    return { ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(corpo)) };
  });
  return chamadas;
}

function quadrado(lng, lat) {
  return [[[lng, lat], [lng + 1, lat], [lng + 1, lat + 1], [lng, lat + 1], [lng, lat]]];
}

// Malha reduzida no formato da API do IBGE: uma feição por UF, com o código em codarea.
export const malha = {
  type: "FeatureCollection",
  features: [
    { type: "Feature", properties: { codarea: "12" }, geometry: { type: "Polygon", coordinates: quadrado(-70, -10) } },
    { type: "Feature", properties: { codarea: "29" }, geometry: { type: "Polygon", coordinates: quadrado(-42, -13) } },
    { type: "Feature", properties: { codarea: "35" }, geometry: { type: "Polygon", coordinates: quadrado(-48, -23) } },
  ],
};
