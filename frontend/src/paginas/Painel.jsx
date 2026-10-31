// Tela principal: filtros, cartões de taxa, variação e posição, gráfico de evolução e ranking.
// O mapa (RF06) reaproveita os dados do ranking, sem requisição extra à API.
import { lazy, Suspense, useState } from "react";
import {
  buscarComparacao,
  buscarEstados,
  buscarMetadados,
  buscarRanking,
} from "../api/cliente.js";
import CartoesResumo from "../componentes/cartoes/CartoesResumo.jsx";
import Filtros from "../componentes/filtros/Filtros.jsx";
import useConsulta from "../hooks/useConsulta.js";
import { achatarIndicadores } from "../utils/indicadores.js";

// Recharts e Leaflet são a maior parte do JavaScript: ficam em arquivos separados, para os filtros
// e os cartões aparecerem antes.
const GraficoEvolucao = lazy(() => import("../componentes/graficos/GraficoEvolucao.jsx"));
const GraficoRanking = lazy(() => import("../componentes/ranking/GraficoRanking.jsx"));
const MapaUfs = lazy(() => import("../componentes/mapa/MapaUfs.jsx"));

export const FILTROS_INICIAIS = { indicador: "mvi", regiao: "", uf: "SP", ano: null };

// Região e UF ficam sempre coerentes: escolher uma região fora da UF atual leva à primeira UF
// dela; escolher (no mapa ou no ranking) uma UF fora da região atual limpa a região.
export function aplicarMudanca(atuais, mudanca, estados) {
  const novos = { ...atuais, ...mudanca };
  const daRegiao = (uf, regiao) =>
    estados.some((estado) => estado.sigla === uf && estado.regiao.sigla === regiao);
  if (!novos.regiao || daRegiao(novos.uf, novos.regiao)) return novos;
  if ("regiao" in mudanca) {
    const primeira = estados.find((estado) => estado.regiao.sigla === novos.regiao);
    return { ...novos, uf: primeira?.sigla ?? novos.uf };
  }
  return { ...novos, regiao: "" };
}

// As regiões vêm da própria lista de UFs (cada uma traz a sua), sem outra requisição.
function regioesDe(estados) {
  const porSigla = new Map(estados.map((estado) => [estado.regiao.sigla, estado.regiao]));
  return [...porSigla.values()].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
}

const CARREGANDO = (
  <p className="carregando" role="status">
    Carregando…
  </p>
);

function Estado({ consulta, children }) {
  if (consulta.erro) {
    return (
      <p className="erro" role="alert">
        Não foi possível carregar os dados: {consulta.erro.message}
      </p>
    );
  }
  if (!consulta.dados) return CARREGANDO;
  return <Suspense fallback={CARREGANDO}>{children(consulta.dados)}</Suspense>;
}

export default function Painel() {
  const [filtros, setFiltros] = useState(FILTROS_INICIAIS);
  const metadados = useConsulta((opcoes) => buscarMetadados(opcoes), []);
  const estados = useConsulta((opcoes) => buscarEstados(opcoes), []);

  const indicadores = metadados.dados ? achatarIndicadores(metadados.dados.indicadores) : [];
  const indicador = indicadores.find((item) => item.slug === filtros.indicador);
  const anos = indicador?.anos ?? [];
  // Sem ano escolhido, ou com um ano que o indicador não tem, vale o último ano com dados.
  const ano = anos.includes(filtros.ano) ? filtros.ano : (anos.at(-1) ?? null);

  const comparacao = useConsulta(
    (opcoes) => buscarComparacao({ uf: filtros.uf, indicador: filtros.indicador }, opcoes),
    [filtros.uf, filtros.indicador],
  );
  const ranking = useConsulta(
    (opcoes) => buscarRanking({ indicador: filtros.indicador, ano }, opcoes),
    [filtros.indicador, ano],
    ano !== null,
  );

  const todosEstados = estados.dados ?? [];
  const ufsDaRegiao = filtros.regiao
    ? todosEstados.filter((estado) => estado.regiao.sigla === filtros.regiao)
    : todosEstados;
  const siglasDaRegiao = filtros.regiao ? new Set(ufsDaRegiao.map((uf) => uf.sigla)) : null;
  const nomeDaRegiao = ufsDaRegiao[0]?.regiao.nome;
  // Sem os metadados o ranking não tem ano para consultar: o erro deles vale também para ele.
  const consultaRanking = metadados.erro ? metadados : ranking;

  const mudarFiltros = (mudanca) =>
    setFiltros((atuais) => aplicarMudanca(atuais, mudanca, todosEstados));
  const itemUf = ranking.dados?.results.find((item) => item.localidade.codigo === filtros.uf);

  return (
    <section aria-labelledby="titulo-painel">
      <h2 id="titulo-painel">Indicadores</h2>

      <Estado consulta={metadados.erro || !metadados.dados ? metadados : estados}>
        {(listaEstados) => (
          <Filtros
            indicadores={indicadores}
            regioes={regioesDe(listaEstados)}
            estados={ufsDaRegiao}
            anos={anos}
            valores={{ ...filtros, ano }}
            aoMudar={mudarFiltros}
          />
        )}
      </Estado>

      {ranking.dados && (
        <CartoesResumo
          item={itemUf}
          ano={ranking.dados.ano}
          base={ranking.dados.indicador.base_taxa}
          totalUfs={ranking.dados.results.length}
        />
      )}

      <div className="painel__graficos" aria-busy={comparacao.carregando || ranking.carregando}>
        <div className="painel__coluna">
          <section className="painel__bloco" aria-labelledby="titulo-evolucao">
            <h3 id="titulo-evolucao">Evolução ao longo dos anos</h3>
            <Estado consulta={comparacao}>
              {(dados) => <GraficoEvolucao comparacao={dados} />}
            </Estado>
          </section>

          <section className="painel__bloco" aria-labelledby="titulo-mapa">
            <h3 id="titulo-mapa">Mapa por unidade da federação</h3>
            <Estado consulta={consultaRanking}>
              {(dados) => (
                <MapaUfs
                  ranking={dados}
                  siglasDaRegiao={siglasDaRegiao}
                  regiao={filtros.regiao}
                  ufSelecionada={filtros.uf}
                  aoSelecionarUf={(uf) => mudarFiltros({ uf })}
                />
              )}
            </Estado>
          </section>
        </div>

        <section className="painel__bloco" aria-labelledby="titulo-ranking">
          <h3 id="titulo-ranking">Comparação entre estados</h3>
          {siglasDaRegiao && (
            <p className="nota">
              Mostrando as UFs da região {nomeDaRegiao}. A posição continua sendo entre as 27 UFs.
            </p>
          )}
          <Estado consulta={consultaRanking}>
            {(dados) => (
              <GraficoRanking
                ranking={
                  siglasDaRegiao
                    ? {
                        ...dados,
                        results: dados.results.filter((item) =>
                          siglasDaRegiao.has(item.localidade.codigo),
                        ),
                      }
                    : dados
                }
                ufSelecionada={filtros.uf}
                aoSelecionarUf={(uf) => uf && mudarFiltros({ uf })}
              />
            )}
          </Estado>
        </section>
      </div>
    </section>
  );
}
