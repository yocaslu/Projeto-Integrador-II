// Filtros do painel (RF04): indicador, região, UF e ano. A UF define a série do gráfico de
// evolução e o destaque no ranking; a região restringe as UFs da lista, do ranking e o destaque
// do mapa; o ano e o critério valem para o ranking e para os cartões. Unidade e recorte só
// aparecem nos indicadores que os têm.
import { criteriosDe } from "../../utils/filtros.js";

const UNIDADES = { vitimas: "Vítimas", ocorrencias: "Ocorrências" };

const RECUO = "   ";

export default function Filtros({ indicadores, regioes, estados, anos, valores, aoMudar }) {
  const indicador = indicadores.find((item) => item.slug === valores.indicador);
  const unidades = indicador?.unidades ?? [];
  const recortes = indicador?.recortes ?? [];

  return (
    <form className="filtros" aria-label="Filtros" onSubmit={(evento) => evento.preventDefault()}>
      <div className="campo">
        <label htmlFor="filtro-indicador">Indicador</label>
        <select
          id="filtro-indicador"
          value={valores.indicador}
          onChange={(evento) => aoMudar({ indicador: evento.target.value })}
        >
          {indicadores.map((indicador) => (
            <option
              key={indicador.slug}
              value={indicador.slug}
              disabled={!indicador.possui_registros}
            >
              {RECUO.repeat(indicador.nivel)}
              {indicador.nome}
            </option>
          ))}
        </select>
      </div>

      <div className="campo">
        <label htmlFor="filtro-regiao">Região</label>
        <select
          id="filtro-regiao"
          value={valores.regiao}
          onChange={(evento) => aoMudar({ regiao: evento.target.value })}
        >
          <option value="">Todas as regiões</option>
          {regioes.map((regiao) => (
            <option key={regiao.sigla} value={regiao.sigla}>
              {regiao.nome}
            </option>
          ))}
        </select>
      </div>

      <div className="campo">
        <label htmlFor="filtro-uf">Unidade da federação</label>
        <select
          id="filtro-uf"
          value={valores.uf}
          onChange={(evento) => aoMudar({ uf: evento.target.value })}
        >
          {estados.map((estado) => (
            <option key={estado.sigla} value={estado.sigla}>
              {estado.nome} ({estado.sigla})
            </option>
          ))}
        </select>
      </div>

      <div className="campo">
        <label htmlFor="filtro-ano">Ano do ranking</label>
        <select
          id="filtro-ano"
          value={valores.ano ?? ""}
          onChange={(evento) => aoMudar({ ano: Number(evento.target.value) })}
          disabled={anos.length === 0}
        >
          {[...anos].reverse().map((ano) => (
            <option key={ano} value={ano}>
              {ano}
            </option>
          ))}
        </select>
      </div>

      <div className="campo">
        <label htmlFor="filtro-criterio">Classificar por</label>
        <select
          id="filtro-criterio"
          value={valores.criterio}
          onChange={(evento) => aoMudar({ criterio: evento.target.value })}
        >
          {criteriosDe(indicador, valores.recorte).map((criterio) => (
            <option key={criterio.valor} value={criterio.valor}>
              {criterio.rotulo}
            </option>
          ))}
        </select>
      </div>

      {unidades.length > 1 && (
        <div className="campo">
          <label htmlFor="filtro-unidade">Unidade</label>
          <select
            id="filtro-unidade"
            value={valores.unidade || indicador.unidade_padrao}
            onChange={(evento) => aoMudar({ unidade: evento.target.value })}
          >
            {unidades.map((unidade) => (
              <option key={unidade} value={unidade}>
                {UNIDADES[unidade] ?? unidade}
              </option>
            ))}
          </select>
        </div>
      )}

      {recortes.length > 0 && (
        <div className="campo">
          <label htmlFor="filtro-recorte">Corporação e situação</label>
          <select
            id="filtro-recorte"
            value={valores.recorte}
            onChange={(evento) => aoMudar({ recorte: evento.target.value })}
          >
            <option value="">Total</option>
            {recortes.map((recorte) => (
              <option key={recorte.id} value={recorte.id}>
                {recorte.rotulo}
              </option>
            ))}
          </select>
        </div>
      )}
    </form>
  );
}
