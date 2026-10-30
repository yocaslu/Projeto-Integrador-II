// Mapa do Brasil com o indicador por UF (RF06). Usa os mesmos dados do ranking, ligados à
// malha do IBGE pelo código da UF (localidade.codigo_ibge = codarea). Não há camada de
// fundo (tiles): o mapa só precisa das UFs e não depende de outro serviço externo.
import "leaflet/dist/leaflet.css";
import { GeoJSON, MapContainer } from "react-leaflet";
import useConsulta from "../../hooks/useConsulta.js";
import { formatarTaxa, rotuloTaxa, SEM_DADO } from "../../utils/formatacao.js";
import { classificar, COR_SEM_DADO, corDoValor, limitesDaMalha } from "../../utils/mapa.js";
import { CORES } from "../../utils/cores.js";

export const URL_MALHA = "/malhas/ufs.json";
const OPACIDADE_FORA_DA_REGIAO = 0.2;

async function buscarMalha({ signal } = {}) {
  const resposta = await fetch(URL_MALHA, { signal });
  if (!resposta.ok) throw new Error(`malha das UFs não encontrada (${resposta.status})`);
  // Sem o arquivo, o Vite e o nginx devolvem o index.html com status 200.
  return resposta.json().catch(() => {
    throw new Error("malha das UFs não encontrada");
  });
}

export function Legenda({ classes, temSemDado }) {
  return (
    <ul className="legenda-mapa" aria-label="Legenda do mapa">
      {classes.map((classe) => (
        <li key={classe.cor}>
          <span className="legenda-mapa__cor" style={{ background: classe.cor }} aria-hidden="true" />
          {formatarTaxa(classe.inicio)} a {formatarTaxa(classe.fim)}
        </li>
      ))}
      {temSemDado && (
        <li>
          <span
            className="legenda-mapa__cor legenda-mapa__cor--sem-dado"
            style={{ background: COR_SEM_DADO }}
            aria-hidden="true"
          />
          {SEM_DADO}
        </li>
      )}
    </ul>
  );
}

export default function MapaUfs({ ranking, siglasDaRegiao, regiao, ufSelecionada, aoSelecionarUf }) {
  const malha = useConsulta((opcoes) => buscarMalha(opcoes), []);
  const { indicador, ano, results } = ranking;

  const porCodigo = new Map(results.map((item) => [item.localidade.codigo_ibge, item]));
  const classes = classificar(results.map((item) => item.taxa?.valor ?? null));
  const temSemDado = results.some((item) => item.taxa?.valor === null || item.taxa?.valor === undefined);
  const titulo = `${rotuloTaxa(indicador.base_taxa)} por unidade da federação, ${ano}`;

  function estilo(feicao) {
    const item = porCodigo.get(feicao.properties.codarea);
    const selecionada = item?.localidade.codigo === ufSelecionada;
    const foraDaRegiao = siglasDaRegiao && !siglasDaRegiao.has(item?.localidade.codigo);
    return {
      fillColor: corDoValor(item?.taxa?.valor ?? null, classes),
      fillOpacity: foraDaRegiao ? OPACIDADE_FORA_DA_REGIAO : 1,
      color: selecionada ? CORES.regiao : CORES.brasil,
      weight: selecionada ? 3 : 0.75,
    };
  }

  function aoCriarUf(feicao, camada) {
    const item = porCodigo.get(feicao.properties.codarea);
    if (!item) return;
    camada.bindTooltip(`${item.localidade.nome}: ${formatarTaxa(item.taxa?.valor ?? null)}`, {
      sticky: true,
    });
    camada.on("click", () => aoSelecionarUf(item.localidade.codigo));
    // A borda da UF selecionada fica por cima das vizinhas.
    if (item.localidade.codigo === ufSelecionada) camada.on("add", () => camada.bringToFront());
  }

  return (
    <figure className="grafico" aria-labelledby="legenda-mapa">
      <figcaption id="legenda-mapa">{titulo}</figcaption>
      {malha.erro && (
        <p className="erro" role="alert">
          Não foi possível exibir o mapa: {malha.erro.message}.
        </p>
      )}
      {malha.dados && (
        <MapContainer
          className="mapa"
          bounds={limitesDaMalha(malha.dados)}
          boundsOptions={{ padding: [8, 8] }}
          scrollWheelZoom={false}
          attributionControl
          zoomSnap={0.25}
        >
          <GeoJSON
            // O GeoJSON do react-leaflet não reaplica estilo nem eventos quando os dados
            // mudam; a chave recria a camada a cada indicador, ano ou UF selecionada.
            key={`${indicador.slug}-${ano}-${ufSelecionada}-${regiao}`}
            data={malha.dados}
            style={estilo}
            onEachFeature={aoCriarUf}
            attribution="Malha: IBGE"
          />
        </MapContainer>
      )}
      <Legenda classes={classes} temSemDado={temSemDado} />
      <p className="nota">
        Cores mais escuras indicam taxas mais altas; cada cor reúne cerca de um quinto das UFs.
        A UF selecionada tem borda laranja. Clique em uma UF para selecioná-la. Os mesmos valores
        estão no ranking e na sua tabela.
        {siglasDaRegiao && " As UFs fora da região escolhida ficam esmaecidas."}
      </p>
      <p className="fonte">
        Fonte: FBSP, Anuário Brasileiro de Segurança Pública, edições de 2024 a 2026; malha das UFs: IBGE, API de
        malhas territoriais.
      </p>
    </figure>
  );
}
