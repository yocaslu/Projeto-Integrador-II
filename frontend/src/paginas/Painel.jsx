// Tela principal: filtros, cartões de taxa, variação e posição, gráfico de evolução e ranking.
// O mapa (RF06) entra depois, reaproveitando os dados do ranking.
import { useState } from "react";
import {
  buscarComparacao,
  buscarEstados,
  buscarMetadados,
  buscarRanking,
} from "../api/cliente.js";
import CartoesResumo from "../componentes/cartoes/CartoesResumo.jsx";
import Filtros from "../componentes/filtros/Filtros.jsx";
import GraficoEvolucao from "../componentes/graficos/GraficoEvolucao.jsx";
import GraficoRanking from "../componentes/ranking/GraficoRanking.jsx";
import useConsulta from "../hooks/useConsulta.js";
import { achatarIndicadores } from "../utils/indicadores.js";

export const FILTROS_INICIAIS = { indicador: "mvi", uf: "SP", ano: null };

function Estado({ consulta, children }) {
  if (consulta.erro) {
    return (
      <p className="erro" role="alert">
        Não foi possível carregar os dados: {consulta.erro.message}
      </p>
    );
  }
  if (!consulta.dados) {
    return (
      <p className="carregando" role="status">
        Carregando…
      </p>
    );
  }
  return children(consulta.dados);
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

  const mudarFiltros = (mudanca) => setFiltros((atuais) => ({ ...atuais, ...mudanca }));
  const itemUf = ranking.dados?.results.find((item) => item.localidade.codigo === filtros.uf);

  return (
    <section aria-labelledby="titulo-painel">
      <h2 id="titulo-painel">Indicadores</h2>

      <Estado consulta={metadados.erro || !metadados.dados ? metadados : estados}>
        {(listaEstados) => (
          <Filtros
            indicadores={indicadores}
            estados={listaEstados}
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
        <section className="painel__bloco" aria-labelledby="titulo-evolucao">
          <h3 id="titulo-evolucao">Evolução ao longo dos anos</h3>
          <Estado consulta={comparacao}>
            {(dados) => <GraficoEvolucao comparacao={dados} />}
          </Estado>
        </section>

        <section className="painel__bloco" aria-labelledby="titulo-ranking">
          <h3 id="titulo-ranking">Comparação entre estados</h3>
          <Estado consulta={ranking}>
            {(dados) => (
              <GraficoRanking
                ranking={dados}
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
