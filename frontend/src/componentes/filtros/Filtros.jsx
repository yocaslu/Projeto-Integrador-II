// Filtros do painel (RF04): indicador, UF e ano. A UF define a série do gráfico de evolução
// e o destaque no ranking; o ano vale para o ranking e para os cartões.

const RECUO = "   ";

export default function Filtros({ indicadores, estados, anos, valores, aoMudar }) {
  return (
    <form className="filtros" aria-label="Filtros" onSubmit={(evento) => evento.preventDefault()}>
      <div className="campo">
        <label htmlFor="filtro-indicador">Indicador</label>
        <select
          id="filtro-indicador"
          value={valores.indicador}
          onChange={(evento) => aoMudar({ indicador: evento.target.value, ano: null })}
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
    </form>
  );
}
