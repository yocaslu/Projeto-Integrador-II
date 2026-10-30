// Evolução temporal da taxa (RF03) da UF, da sua região e do Brasil (RF13), a partir de
// /comparacao/, que já devolve as três séries com os mesmos anos.
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { urlApi } from "../../api/cliente.js";
import { CORES } from "../../utils/cores.js";
import { formatarTaxa, rotuloTaxa } from "../../utils/formatacao.js";
import TabelaDados from "./TabelaDados.jsx";

const ESTILOS = [
  { chave: "uf", cor: CORES.uf, traco: undefined, marcador: "circle" },
  { chave: "regiao", cor: CORES.regiao, traco: "6 4", marcador: "square" },
  { chave: "brasil", cor: CORES.brasil, traco: "2 3", marcador: "triangle" },
];

// Linhas do gráfico: uma por ano, com a taxa de cada série.
export function montarLinhas(series) {
  const [uf, regiao, brasil] = series;
  return uf.pontos.map((ponto, indice) => ({
    ano: ponto.ano,
    uf: ponto.taxa?.valor ?? null,
    regiao: regiao.pontos[indice]?.taxa?.valor ?? null,
    brasil: brasil.pontos[indice]?.taxa?.valor ?? null,
  }));
}

// A fonte do denominador pode mudar ao longo da série: "A (2012 a 2023); B (2024 a 2025)".
export function fontesPorPeriodo(pontos) {
  const periodos = [];
  for (const ponto of pontos) {
    const nome = ponto.taxa?.fonte?.nome;
    if (!nome) continue;
    const ultimo = periodos.at(-1);
    if (ultimo?.nome === nome) ultimo.fim = ponto.ano;
    else periodos.push({ nome, inicio: ponto.ano, fim: ponto.ano });
  }
  if (periodos.length < 2) return periodos[0]?.nome ?? "";
  return periodos
    .map(({ nome, inicio, fim }) =>
      inicio === fim ? `${nome} (${inicio})` : `${nome} (${inicio} a ${fim})`,
    )
    .join("; ");
}

function Marcador({ cx, cy, forma, cor }) {
  if (cx === undefined || cy === undefined) return null;
  if (forma === "square") {
    return <rect x={cx - 4} y={cy - 4} width={8} height={8} fill={cor} />;
  }
  if (forma === "triangle") {
    return <path d={`M${cx},${cy - 5} L${cx + 5},${cy + 4} L${cx - 5},${cy + 4} Z`} fill={cor} />;
  }
  return <circle cx={cx} cy={cy} r={4} fill={cor} />;
}

export default function GraficoEvolucao({ comparacao }) {
  const { indicador, series, ano_min: anoMin, ano_max: anoMax } = comparacao;
  const linhas = montarLinhas(series);
  const nomes = {
    uf: series[0].localidade.nome,
    regiao: series[1].localidade.nome,
    brasil: series[2].localidade.nome,
  };
  const regiaoSemTaxa = linhas.every((linha) => linha.regiao === null);
  const fontesTaxa = fontesPorPeriodo(series[0].pontos);
  const anosPublicados = series[0].pontos
    .filter((ponto) => ponto.taxa?.origem === "publicada")
    .map((ponto) => ponto.ano);
  const origemMista =
    anosPublicados.length > 0 && series[0].pontos.some((ponto) => ponto.taxa?.origem === "calculada");
  const titulo = `${rotuloTaxa(indicador.base_taxa)}, ${anoMin} a ${anoMax}`;

  return (
    <figure className="grafico" aria-labelledby="legenda-evolucao">
      <figcaption id="legenda-evolucao">
        {titulo}: {nomes.uf}, {nomes.regiao} e {nomes.brasil}
      </figcaption>

      <div className="grafico__area grafico__area--evolucao">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={linhas} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid stroke={CORES.grade} vertical={false} />
            <XAxis dataKey="ano" tickMargin={6} interval="equidistantPreserveStart" />
            <YAxis width={48} tickFormatter={(valor) => formatarTaxa(valor).replace(",00", "")} />
            <Tooltip
              formatter={(valor, chave) => [formatarTaxa(valor), nomes[chave]]}
              labelFormatter={(ano) => `Ano ${ano}`}
            />
            <Legend formatter={(chave) => nomes[chave]} />
            {ESTILOS.map(({ chave, cor, traco, marcador }) => (
              <Line
                key={chave}
                dataKey={chave}
                name={chave}
                stroke={cor}
                strokeWidth={2.5}
                strokeDasharray={traco}
                dot={(props) => (
                  <Marcador key={`${chave}-${props.index}`} {...props} forma={marcador} cor={cor} />
                )}
                isAnimationActive={false}
                connectNulls={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {linhas.length < 3 && (
        <p className="nota">
          Este indicador tem dados de {anoMin} e {anoMax} no Anuário 2026. A série longa, de 2012
          a 2025, existe para as Mortes Violentas Intencionais.
        </p>
      )}
      {origemMista && (
        <p className="nota">
          Taxas de {anosPublicados[0]} a {anosPublicados.at(-1)} publicadas pelo FBSP; nos demais
          anos, calculadas com a população do IBGE.
        </p>
      )}
      {regiaoSemTaxa && (
        <p className="nota">
          A taxa da região {nomes.regiao} não está disponível para este indicador, porque não há
          denominador regional publicado.
        </p>
      )}

      <TabelaDados
        legenda={titulo}
        colunas={[
          { chave: "ano", titulo: "Ano" },
          { chave: "uf", titulo: nomes.uf },
          { chave: "regiao", titulo: nomes.regiao },
          { chave: "brasil", titulo: nomes.brasil },
        ]}
        linhas={linhas.map((linha) => ({
          chave: linha.ano,
          ano: linha.ano,
          uf: formatarTaxa(linha.uf),
          regiao: formatarTaxa(linha.regiao),
          brasil: formatarTaxa(linha.brasil),
        }))}
      />

      <p className="fonte">
        Fonte: FBSP, Anuário Brasileiro de Segurança Pública 2026
        {fontesTaxa ? `; denominador da taxa: ${fontesTaxa}` : ""}.{" "}
        <a
          href={urlApi("/comparacao/", {
            uf: series[0].localidade.codigo,
            indicador: indicador.slug,
            formato: "csv",
          })}
        >
          Baixar estes dados (CSV)
        </a>
      </p>
    </figure>
  );
}
