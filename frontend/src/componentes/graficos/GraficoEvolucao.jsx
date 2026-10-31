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

const ANOS_SEMPRE_VISIVEIS = 6;

const ESTILOS = [
  { chave: "uf", cor: CORES.uf, traco: undefined, marcador: "circle" },
  { chave: "regiao", cor: CORES.regiao, traco: "6 4", marcador: "square" },
  { chave: "brasil", cor: CORES.brasil, traco: "2 3", marcador: "triangle" },
];

const NOTA_DE_REVISAO = /Revisão do FBSP: ([^.]*)\./;

// Anos em que o FBSP revisou o valor da UF, com o que a edição anterior publicou (ADR 0012).
export function revisoesDe(pontos) {
  return pontos.flatMap((ponto) => {
    const nota = ponto.observacao?.match(NOTA_DE_REVISAO);
    return nota ? [{ ano: ponto.ano, texto: nota[1] }] : [];
  });
}

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

function Marcador({ cx, cy, forma, cor, revisado }) {
  if (cx === undefined || cy === undefined) return null;
  if (revisado) {
    return (
      <g>
        <circle cx={cx} cy={cy} r={8} fill="none" stroke={cor} strokeWidth={1.5} />
        <circle cx={cx} cy={cy} r={4} fill={cor} />
      </g>
    );
  }
  if (forma === "square") {
    return <rect x={cx - 4} y={cy - 4} width={8} height={8} fill={cor} />;
  }
  if (forma === "triangle") {
    return <path d={`M${cx},${cy - 5} L${cx + 5},${cy + 4} L${cx - 5},${cy + 4} Z`} fill={cor} />;
  }
  return <circle cx={cx} cy={cy} r={4} fill={cor} />;
}

export default function GraficoEvolucao({ comparacao, unidade }) {
  const { indicador, recorte, series, ano_min: anoMin, ano_max: anoMax } = comparacao;
  const linhas = montarLinhas(series);
  // Com recorte, a evolução é só da UF: o total do Brasil soma as UFs que informaram, e esse
  // conjunto muda de um ano para o outro (ADR 0009).
  const estilos = recorte ? ESTILOS.slice(0, 1) : ESTILOS;
  const revisoes = revisoesDe(series[0].pontos);
  const anosRevisados = new Set(revisoes.map((revisao) => revisao.ano));
  const nomes = {
    uf: series[0].localidade.nome,
    regiao: series[1].localidade.nome,
    brasil: series[2].localidade.nome,
  };
  const regiaoSemTaxa = !recorte && linhas.every((linha) => linha.regiao === null);
  const ufSemTaxa = linhas.every((linha) => linha.uf === null);
  const fontesTaxa = fontesPorPeriodo(series[0].pontos);
  const anosPublicados = series[0].pontos
    .filter((ponto) => ponto.taxa?.origem === "publicada")
    .map((ponto) => ponto.ano);
  const origemMista =
    anosPublicados.length > 0 && series[0].pontos.some((ponto) => ponto.taxa?.origem === "calculada");
  const rotulo = recorte ? `${rotuloTaxa(indicador.base_taxa)} (${recorte.rotulo})` : rotuloTaxa(indicador.base_taxa);
  const titulo = `${rotulo}, ${anoMin} a ${anoMax}`;
  const localidades = estilos.map(({ chave }) => nomes[chave]);

  return (
    <figure className="grafico" aria-labelledby="legenda-evolucao">
      <figcaption id="legenda-evolucao">
        {titulo}: {new Intl.ListFormat("pt-BR").format(localidades)}
      </figcaption>

      <div className="grafico__area grafico__area--evolucao">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={linhas} margin={{ top: 8, right: 24, bottom: 8, left: 0 }}>
            <CartesianGrid stroke={CORES.grade} vertical={false} />
            <XAxis
              dataKey="ano"
              tickMargin={6}
              // Série curta mostra todos os anos; a de 14 anos pula rótulos conforme a largura.
              interval={linhas.length <= ANOS_SEMPRE_VISIVEIS ? 0 : "equidistantPreserveStart"}
            />
            <YAxis width={48} tickFormatter={(valor) => formatarTaxa(valor).replace(",00", "")} />
            <Tooltip
              formatter={(valor, chave) => [formatarTaxa(valor), nomes[chave]]}
              labelFormatter={(ano) => `Ano ${ano}`}
            />
            <Legend formatter={(chave) => nomes[chave]} />
            {estilos.map(({ chave, cor, traco, marcador }) => (
              <Line
                key={chave}
                dataKey={chave}
                name={chave}
                stroke={cor}
                strokeWidth={2.5}
                strokeDasharray={traco}
                dot={(props) => (
                  <Marcador
                    key={`${chave}-${props.index}`}
                    {...props}
                    forma={marcador}
                    cor={cor}
                    revisado={chave === "uf" && anosRevisados.has(props.payload.ano)}
                  />
                )}
                isAnimationActive={false}
                connectNulls={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {recorte && (
        <p className="nota">
          No recorte, o gráfico mostra só a UF: o total do Brasil soma as UFs que informaram, e esse
          conjunto muda de um ano para o outro.
        </p>
      )}
      {recorte && ufSemTaxa && (
        <p className="nota">{nomes.uf} não informou este recorte nos anos da série.</p>
      )}
      {revisoes.length > 0 && (
        <div className="nota">
          <p>O círculo em volta do ponto marca os anos em que o FBSP revisou o valor de {nomes.uf}:</p>
          <ul>
            {revisoes.map((revisao) => (
              <li key={revisao.ano}>
                {revisao.ano}: {revisao.texto}.
              </li>
            ))}
          </ul>
        </div>
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
          ...estilos.map(({ chave }) => ({ chave, titulo: nomes[chave] })),
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
        Fonte: FBSP, Anuário Brasileiro de Segurança Pública, edições de 2024 a 2026
        {fontesTaxa ? `; denominador da taxa: ${fontesTaxa}` : ""}.{" "}
        <a
          href={urlApi("/comparacao/", {
            uf: series[0].localidade.codigo,
            indicador: indicador.slug,
            unidade,
            recorte: recorte?.id,
            formato: "csv",
          })}
        >
          Baixar estes dados (CSV)
        </a>
      </p>
    </figure>
  );
}
