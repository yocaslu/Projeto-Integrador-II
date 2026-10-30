// Comparação entre estados (RF03) e ranking das UFs (RF10), a partir de /ranking/, que já
// devolve as 27 UFs em ordem decrescente de taxa, com empates e sem dado ao final.
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { urlApi } from "../../api/cliente.js";
import { CORES } from "../../utils/cores.js";
import { formatarInteiro, formatarTaxa, rotuloTaxa } from "../../utils/formatacao.js";
import TabelaDados from "../graficos/TabelaDados.jsx";

const ALTURA_BARRA = 22;

export default function GraficoRanking({ ranking, ufSelecionada, aoSelecionarUf }) {
  const { indicador, ano, results } = ranking;
  const comTaxa = results
    .filter((item) => item.taxa?.valor !== null && item.taxa?.valor !== undefined)
    .map((item) => ({
      sigla: item.localidade.codigo,
      nome: item.localidade.nome,
      taxa: item.taxa.valor,
    }));
  const semDado = results.filter((item) => item.posicao === null);
  const titulo = `${rotuloTaxa(indicador.base_taxa)} por unidade da federação, ${ano}`;
  const fonteTaxa = results.find((item) => item.taxa?.fonte)?.taxa.fonte.nome;

  return (
    <figure className="grafico" aria-labelledby="legenda-ranking">
      <figcaption id="legenda-ranking">{titulo}</figcaption>

      <div className="grafico__area" style={{ height: comTaxa.length * ALTURA_BARRA + 40 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={comTaxa}
            layout="vertical"
            margin={{ top: 4, right: 56, bottom: 4, left: 0 }}
            barCategoryGap={3}
          >
            <CartesianGrid stroke={CORES.grade} horizontal={false} />
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="sigla"
              width={36}
              interval={0}
              tick={({ x, y, payload }) => (
                <text
                  x={x}
                  y={y}
                  dy={4}
                  textAnchor="end"
                  fontSize={12}
                  fontWeight={payload.value === ufSelecionada ? 700 : 400}
                  fill={CORES.brasil}
                >
                  {payload.value}
                </text>
              )}
            />
            <Tooltip
              formatter={(valor) => [formatarTaxa(valor), rotuloTaxa(indicador.base_taxa)]}
              labelFormatter={(sigla) => comTaxa.find((item) => item.sigla === sigla)?.nome}
            />
            <Bar
              dataKey="taxa"
              isAnimationActive={false}
              cursor="pointer"
              onClick={(dados) => aoSelecionarUf(dados.sigla ?? dados.payload?.sigla)}
            >
              {comTaxa.map((item) => (
                <Cell
                  key={item.sigla}
                  fill={item.sigla === ufSelecionada ? CORES.barraDestaque : CORES.barra}
                />
              ))}
              <LabelList
                dataKey="taxa"
                position="right"
                formatter={formatarTaxa}
                fontSize={12}
                fill={CORES.brasil}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="nota">
        A barra destacada é a UF selecionada. Clique em uma barra para selecionar outra UF.
      </p>
      {semDado.length > 0 && (
        <p className="nota">
          Sem dado em {ano}: {semDado.map((item) => item.localidade.nome).join(", ")}.
        </p>
      )}

      <TabelaDados
        legenda={titulo}
        colunas={[
          { chave: "posicao", titulo: "Posição" },
          { chave: "uf", titulo: "UF" },
          { chave: "taxa", titulo: rotuloTaxa(indicador.base_taxa) },
          { chave: "valor", titulo: "Número absoluto" },
        ]}
        linhas={results.map((item) => ({
          chave: item.localidade.codigo,
          posicao: item.posicao ? `${item.posicao}ª` : "—",
          uf: item.localidade.nome,
          taxa: formatarTaxa(item.taxa?.valor),
          valor: formatarInteiro(item.valor),
        }))}
      />

      <p className="fonte">
        Fonte: FBSP, Anuário Brasileiro de Segurança Pública 2026
        {fonteTaxa ? `; denominador da taxa: ${fonteTaxa}` : ""}.{" "}
        <a href={urlApi("/ranking/", { indicador: indicador.slug, ano, formato: "csv" })}>
          Baixar estes dados (CSV)
        </a>
      </p>
    </figure>
  );
}
