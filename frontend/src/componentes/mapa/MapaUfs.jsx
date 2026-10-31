// Mapa do Brasil com o indicador por UF (RF06). Usa os mesmos dados do ranking, ligados à
// malha do IBGE pelo código da UF (localidade.codigo_ibge = codarea). Não há camada de
// fundo (tiles): o mapa só precisa das UFs e não depende de outro serviço externo.
import "leaflet/dist/leaflet.css";
import { useRef } from "react";
import { GeoJSON, MapContainer } from "react-leaflet";
import useConsulta from "../../hooks/useConsulta.js";
import { SEM_DADO } from "../../utils/formatacao.js";
import { formatarMetrica, metrica, tituloDoRanking } from "../../utils/metricas.js";
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

export function Legenda({ classes, temSemDado, criterio = "taxa" }) {
  return (
    <ul className="legenda-mapa" aria-label="Legenda do mapa">
      {classes.map((classe) => (
        <li key={classe.cor}>
          <span className="legenda-mapa__cor" style={{ background: classe.cor }} aria-hidden="true" />
          {formatarMetrica(classe.inicio, criterio)} a {formatarMetrica(classe.fim, criterio)}
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
  const { indicador, ano, recorte, results, criterio = "taxa" } = ranking;
  const ufParaFocar = useRef(null);

  const porCodigo = new Map(results.map((item) => [item.localidade.codigo_ibge, item]));
  const classes = classificar(results.map((item) => metrica(item, criterio)));
  const temSemDado = results.some((item) => metrica(item, criterio) === null);
  const titulo = tituloDoRanking({ ...ranking, criterio });
  const textoDaUf = (item) =>
    `${item.localidade.nome}: ${formatarMetrica(metrica(item, criterio), criterio)}`;

  function estilo(feicao) {
    const item = porCodigo.get(feicao.properties.codarea);
    const selecionada = item?.localidade.codigo === ufSelecionada;
    const foraDaRegiao = siglasDaRegiao && !siglasDaRegiao.has(item?.localidade.codigo);
    return {
      fillColor: corDoValor(item ? metrica(item, criterio) : null, classes),
      fillOpacity: foraDaRegiao ? OPACIDADE_FORA_DA_REGIAO : 1,
      color: selecionada ? CORES.regiao : CORES.brasil,
      weight: selecionada ? 3 : 0.75,
    };
  }

  function aoCriarUf(feicao, camada) {
    const item = porCodigo.get(feicao.properties.codarea);
    if (!item) return;
    camada.bindTooltip(textoDaUf(item), { sticky: true });
    camada.on("click", () => aoSelecionarUf(item.localidade.codigo));
  }

  // Com todas as UFs já desenhadas: borda da selecionada por cima das vizinhas e teclado. Só a
  // selecionada entra na ordem do Tab; as setas percorrem as demais em ordem alfabética, e Enter
  // ou espaço seleciona. O mapa é recriado a cada seleção, então o foco é devolvido à UF.
  function aoAdicionarMalha(evento) {
    const ufs = evento.target
      .getLayers()
      .map((camada) => ({ camada, item: porCodigo.get(camada.feature.properties.codarea) }))
      .filter(({ item }) => item)
      .sort((a, b) => a.item.localidade.nome.localeCompare(b.item.localidade.nome, "pt-BR"));
    ufs.forEach(({ camada, item }, indice) => {
      const elemento = camada.getElement();
      const sigla = item.localidade.codigo;
      const selecionada = sigla === ufSelecionada;
      elemento.setAttribute("role", "button");
      elemento.setAttribute("aria-label", textoDaUf(item));
      elemento.setAttribute("aria-pressed", String(selecionada));
      elemento.setAttribute("tabindex", selecionada ? "0" : "-1");
      elemento.addEventListener("keydown", (tecla) => {
        const passo = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[tecla.key];
        if (passo) {
          const proxima = ufs[(indice + passo + ufs.length) % ufs.length].camada.getElement();
          elemento.setAttribute("tabindex", "-1");
          proxima.setAttribute("tabindex", "0");
          proxima.focus();
        } else if (tecla.key === "Enter" || tecla.key === " ") {
          ufParaFocar.current = sigla;
          aoSelecionarUf(sigla);
        } else {
          return;
        }
        tecla.preventDefault();
        tecla.stopPropagation();
      });
      if (selecionada) camada.bringToFront();
      if (ufParaFocar.current === sigla) {
        elemento.focus();
        // Só depois da montagem: no desenvolvimento, o StrictMode monta a camada duas vezes.
        setTimeout(() => {
          ufParaFocar.current = null;
        });
      }
    });
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
            key={`${indicador.slug}-${ano}-${criterio}-${ranking.unidade}-${recorte?.id}-${ufSelecionada}-${regiao}-${results.length}`}
            data={malha.dados}
            style={estilo}
            onEachFeature={aoCriarUf}
            eventHandlers={{ add: aoAdicionarMalha }}
            attribution="Malha: IBGE"
          />
        </MapContainer>
      )}
      <Legenda classes={classes} temSemDado={temSemDado} criterio={criterio} />
      <p className="nota">
        A legenda vai do menor para o maior valor; cada cor reúne cerca de um quinto das UFs.
        A UF selecionada tem borda laranja. Clique em uma UF para selecioná-la ou, pelo teclado, use
        as setas e Enter. Os mesmos valores estão no ranking e na sua tabela.
        {siglasDaRegiao && " As UFs fora da região escolhida ficam esmaecidas."}
      </p>
      <p className="fonte">
        Fonte: FBSP, Anuário Brasileiro de Segurança Pública, edições de 2024 a 2026; malha das UFs: IBGE, API de
        malhas territoriais.
      </p>
    </figure>
  );
}
