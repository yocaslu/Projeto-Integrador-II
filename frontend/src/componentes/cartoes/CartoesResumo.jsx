// Cartões da UF selecionada no ano do ranking: taxa, variação e posição (esboço do roteiro).
// Os números vêm do mesmo item de /ranking/, então não há requisição extra.
import {
  formatarInteiro,
  formatarTaxa,
  formatarVariacao,
  rotuloTaxa,
} from "../../utils/formatacao.js";

const CRITERIOS = { valor: ", por número absoluto", participacao: ", por participação" };
const UNIDADES = { vitimas: "Número de vítimas", ocorrencias: "Número de ocorrências" };

const SITUACOES = {
  inexistente: "Fenômeno inexistente",
  nao_disponivel: "Informação não disponível",
};

export default function CartoesResumo({ item, ano, base, totalUfs, criterio = "taxa", unidade }) {
  if (!item) return null;
  const { localidade, valor, taxa, variacao, posicao, situacao, observacao } = item;

  return (
    <section className="cartoes" aria-labelledby="titulo-cartoes">
      <h3 id="titulo-cartoes">
        {localidade.nome} em {ano}
      </h3>
      <dl className="cartoes__lista">
        <div className="cartao">
          <dt>{rotuloTaxa(base)}</dt>
          <dd>{formatarTaxa(taxa?.valor)}</dd>
        </div>
        <div className="cartao">
          <dt>Variação da taxa em relação a {variacao?.ano_referencia ?? ano - 1}</dt>
          <dd>{formatarVariacao(variacao?.taxa_pct)}</dd>
        </div>
        <div className="cartao">
          <dt>Posição entre as UFs{CRITERIOS[criterio]}</dt>
          <dd>{posicao ? `${posicao}ª de ${totalUfs}` : "Sem posição"}</dd>
        </div>
        <div className="cartao">
          <dt>{UNIDADES[unidade] ?? "Número absoluto"}</dt>
          <dd>{formatarInteiro(valor)}</dd>
        </div>
      </dl>
      {SITUACOES[situacao] && <p className="nota">Situação do dado: {SITUACOES[situacao]}.</p>}
      {observacao && <p className="nota">Nota: {observacao}</p>}
    </section>
  );
}
