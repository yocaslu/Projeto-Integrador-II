// Baixa a malha das 27 UFs da API de malhas territoriais do IBGE (v3), em GeoJSON e na
// qualidade mínima, e grava em public/malhas/ufs.json. Rode uma vez (npm run malha) e
// versione o arquivo: o mapa não depende da disponibilidade do IBGE a cada visita.
//
// Cada feição mantém só a propriedade codarea (código IBGE da UF, "35"), que liga a malha
// ao campo localidade.codigo_ibge da API. As coordenadas são arredondadas a 4 casas
// (cerca de 11 m), suficiente para um mapa do país inteiro.
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const URL_MALHA =
  "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR" +
  "?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao=UF";

const CASAS = 4;
const DESTINO = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "malhas", "ufs.json");

function arredondar(coordenadas) {
  if (typeof coordenadas[0] === "number") {
    return coordenadas.map((valor) => Number(valor.toFixed(CASAS)));
  }
  return coordenadas.map(arredondar);
}

export function reduzirMalha(geojson) {
  const feicoes = geojson.features.map((feicao) => ({
    type: "Feature",
    properties: { codarea: String(feicao.properties.codarea) },
    geometry: {
      type: feicao.geometry.type,
      coordinates: arredondar(feicao.geometry.coordinates),
    },
  }));
  if (feicoes.length !== 27) {
    throw new Error(`Esperadas 27 UFs na malha, recebidas ${feicoes.length}.`);
  }
  feicoes.sort((a, b) => a.properties.codarea.localeCompare(b.properties.codarea));
  return { type: "FeatureCollection", features: feicoes };
}

async function principal() {
  const resposta = await fetch(URL_MALHA);
  if (!resposta.ok) throw new Error(`IBGE respondeu ${resposta.status}.`);
  const malha = reduzirMalha(await resposta.json());
  await mkdir(dirname(DESTINO), { recursive: true });
  await writeFile(DESTINO, `${JSON.stringify(malha)}\n`);
  console.log(`Malha gravada em ${DESTINO} (${malha.features.length} UFs).`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  principal().catch((erro) => {
    console.error(erro.message);
    process.exit(1);
  });
}
