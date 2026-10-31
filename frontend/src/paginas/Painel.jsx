// Tela principal: filtros, cartões de taxa, variação e posição, gráfico de evolução e ranking.
// O mapa (RF06) reaproveita os dados do ranking, sem requisição extra à API.
import { lazy, Suspense, useEffect, useState } from "react";
import {
  buscarComparacao,
  buscarEstados,
  buscarMetadados,
  buscarRanking,
} from "../api/cliente.js";
import CartoesResumo from "../componentes/cartoes/CartoesResumo.jsx";
import Filtros from "../componentes/filtros/Filtros.jsx";
import useConsulta from "../hooks/useConsulta.js";
import {
  aplicarMudanca,
  buscaDosFiltros,
  corrigirFiltros,
  lerFiltrosDaUrl,
} from "../utils/filtros.js";
import { achatarIndicadores } from "../utils/indicadores.js";

// Recharts e Leaflet são a maior parte do JavaScript: ficam em arquivos separados, para os filtros
// e os cartões aparecerem antes.
const GraficoEvolucao = lazy(() => import("../componentes/graficos/GraficoEvolucao.jsx"));
const GraficoRanking = lazy(() => import("../componentes/ranking/GraficoRanking.jsx"));
const MapaUfs = lazy(() => import("../componentes/mapa/MapaUfs.jsx"));

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
  const [escolhidos, setEscolhidos] = useState(() => lerFiltrosDaUrl());
  const metadados = useConsulta((opcoes) => buscarMetadados(opcoes), []);
  const estados = useConsulta((opcoes) => buscarEstados(opcoes), []);

  const indicadores = metadados.dados ? achatarIndicadores(metadados.dados.indicadores) : [];
  const todosEstados = estados.dados ?? [];
  // As consultas esperam os metadados e as UFs: um link pode trazer valores que não existem mais.
  const pronto = Boolean(metadados.dados && estados.dados);
  const filtros = pronto ? corrigirFiltros(escolhidos, indicadores, todosEstados) : escolhidos;
  const indicador = indicadores.find((item) => item.slug === filtros.indicador);
  const anos = indicador?.anos ?? [];
  const { ano } = filtros;
  const ultimoAno = anos.at(-1);
  const buscaNaUrl = buscaDosFiltros(filtros, ultimoAno);

  useEffect(() => {
    if (pronto) window.history.replaceState(null, "", `${window.location.pathname}${buscaNaUrl}`);
  }, [pronto, buscaNaUrl]);

  const comparacao = useConsulta(
    (opcoes) =>
      buscarComparacao(
        {
          uf: filtros.uf,
          indicador: filtros.indicador,
          unidade: filtros.unidade,
          recorte: filtros.recorte,
        },
        opcoes,
      ),
    [filtros.uf, filtros.indicador, filtros.unidade, filtros.recorte],
    pronto,
  );
  const ranking = useConsulta(
    (opcoes) =>
      buscarRanking(
        {
          indicador: filtros.indicador,
          ano,
          criterio: filtros.criterio === "taxa" ? null : filtros.criterio,
          unidade: filtros.unidade,
          recorte: filtros.recorte,
        },
        opcoes,
      ),
    [filtros.indicador, ano, filtros.criterio, filtros.unidade, filtros.recorte],
    pronto && ano !== null,
  );

  const ufsDaRegiao = filtros.regiao
    ? todosEstados.filter((estado) => estado.regiao.sigla === filtros.regiao)
    : todosEstados;
  const siglasDaRegiao = filtros.regiao ? new Set(ufsDaRegiao.map((uf) => uf.sigla)) : null;
  const nomeDaRegiao = ufsDaRegiao[0]?.regiao.nome;
  // Sem os metadados e as UFs, as consultas não saem: o erro deles vale também para os blocos.
  const erroDeBase = metadados.erro ? metadados : estados.erro ? estados : null;
  const consultaRanking = erroDeBase ?? ranking;
  const consultaEvolucao = erroDeBase ?? comparacao;

  const mudarFiltros = (mudanca) =>
    setEscolhidos((atuais) =>
      aplicarMudanca(corrigirFiltros(atuais, indicadores, todosEstados), mudanca, todosEstados),
    );
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
            valores={filtros}
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
          criterio={ranking.dados.criterio}
          unidade={ranking.dados.unidade}
        />
      )}

      <div className="painel__graficos" aria-busy={comparacao.carregando || ranking.carregando}>
        <div className="painel__coluna">
          <section className="painel__bloco" aria-labelledby="titulo-evolucao">
            <h3 id="titulo-evolucao">Evolução ao longo dos anos</h3>
            <Estado consulta={consultaEvolucao}>
              {(dados) => <GraficoEvolucao comparacao={dados} unidade={filtros.unidade} />}
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
                unidade={filtros.unidade}
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
