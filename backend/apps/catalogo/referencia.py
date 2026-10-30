"""Dados de referência do catálogo: fontes e hierarquia de indicadores.

Fixos, revisados em PR e carregados pelo comando importar_anuario antes dos fatos.

- FONTES: criadas primeiro e sempre nesta ordem, para que um banco limpo reproduza os ids 1 a 5
  (ADR 0005; contrato, seção 4.5). Fonte nova entra no fim; nenhuma é reordenada nem removida.
- INDICADORES: em pré-ordem da hierarquia, que é o valor de `ordem` (contrato, seção 4.3.1;
  docs/importacao.md, seção 2). A hierarquia significa "contido em", nunca "soma de".
"""

from dataclasses import dataclass

from apps.catalogo.models import BaseTaxa
from apps.registros.escolhas import Unidade


@dataclass(frozen=True)
class FonteRef:
    slug: str
    nome: str
    descricao: str
    url: str


@dataclass(frozen=True)
class IndicadorRef:
    slug: str
    nome: str
    pai: str | None
    unidade_padrao: Unidade
    base_taxa: BaseTaxa | None
    descricao: str


FONTES: tuple[FonteRef, ...] = (
    FonteRef(
        "secretarias-seguranca",
        "Secretarias Estaduais de Segurança Pública e/ou Defesa Social (compilação FBSP)",
        "Registros policiais das secretarias estaduais de segurança pública e defesa social, do "
        "ISP/RJ e de polícias civis e militares de alguns estados, compilados pelo Fórum "
        "Brasileiro de Segurança Pública no 20º Anuário Brasileiro de Segurança Pública (2026). "
        'A linha "Fonte:" completa de cada tabela está em docs/importacao.md.',
        "https://publicacoes.forumseguranca.org.br/items/bb542342-3cf8-47a5-a51d-a0eb911914b9",
    ),
    FonteRef(
        "ibge-estimativas",
        "IBGE – Estimativas da população residente",
        "Estimativas da população residente no Brasil e nas Unidades da Federação, com data de "
        "referência em 1º de julho de 2024 e de 2025.",
        "https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html",
    ),
    FonteRef(
        "ibge-projecoes",
        "IBGE – Projeções da população",
        "Projeções da população do Brasil e das Unidades da Federação por sexo e idade (revisão "
        "2024), usadas pelo FBSP no denominador das taxas por 100 mil mulheres e das taxas por "
        "100 mil habitantes de 2012 a 2023.",
        "https://www.ibge.gov.br/estatisticas/sociais/populacao/9109-projecao-da-populacao.html",
    ),
    FonteRef(
        "senatran-frota",
        "Senatran – Frota de veículos",
        "Frota de veículos registrada no RENAVAM e informada pela Secretaria Nacional de Trânsito "
        "(Ministério dos Transportes) em dezembro de 2024 e de 2025.",
        "https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/"
        "estatisticas-frota-de-veiculos-senatran",
    ),
    FonteRef(
        "bcb-instituicoes",
        "Banco Central do Brasil – Instituições financeiras",
        "Quantidade de instituições financeiras (bancos, caixas eletrônicos e empresas de "
        "transporte de valores) informada pelo Banco Central do Brasil em dezembro de 2024 e de "
        "2025.",
        "https://www.bcb.gov.br/estabilidadefinanceira/relacao_instituicoes_funcionamento",
    ),
)

FONTE_DOS_REGISTROS = "secretarias-seguranca"
FONTE_DAS_ESTIMATIVAS = "ibge-estimativas"
FONTE_DAS_PROJECOES = "ibge-projecoes"

FONTE_DA_BASE: dict[BaseTaxa, str] = {
    BaseTaxa.HABITANTES: "ibge-estimativas",
    BaseTaxa.MULHERES: "ibge-projecoes",
    BaseTaxa.VEICULOS: "senatran-frota",
    BaseTaxa.INSTITUICOES: "bcb-instituicoes",
}
"""Fonte do denominador de cada base de taxa (INDICADORES.fonte_taxa, ajuste 12)."""

VIT, OCO = Unidade.VITIMAS, Unidade.OCORRENCIAS
HAB, MUL, VEI, INS = (
    BaseTaxa.HABITANTES,
    BaseTaxa.MULHERES,
    BaseTaxa.VEICULOS,
    BaseTaxa.INSTITUICOES,
)

INDICADORES: tuple[IndicadorRef, ...] = (
    IndicadorRef(
        "mvi",
        "Mortes Violentas Intencionais",
        None,
        VIT,
        HAB,
        "Soma das vítimas de homicídio doloso (inclusive feminicídios), latrocínio, lesão "
        "corporal seguida de morte e morte decorrente de intervenção policial. Indicador-síntese "
        "da violência letal.",
    ),
    IndicadorRef(
        "homicidio-doloso",
        "Homicídio doloso",
        "mvi",
        VIT,
        HAB,
        "Homicídio com intenção de matar, incluindo os feminicídios.",
    ),
    IndicadorRef(
        "homicidio-mulheres",
        "Homicídio de mulheres (incluindo feminicídios)",
        "homicidio-doloso",
        VIT,
        MUL,
        "Homicídios dolosos cujas vítimas são mulheres, incluindo os feminicídios.",
    ),
    IndicadorRef(
        "feminicidio",
        "Feminicídio",
        "homicidio-mulheres",
        VIT,
        MUL,
        "Homicídio de mulher por razões da condição de sexo feminino (Lei nº 13.104/2015).",
    ),
    IndicadorRef(
        "latrocinio",
        "Latrocínio",
        "mvi",
        VIT,
        HAB,
        "Roubo seguido de morte.",
    ),
    IndicadorRef(
        "lesao-corporal-seguida-de-morte",
        "Lesão corporal seguida de morte",
        "mvi",
        VIT,
        HAB,
        "Agressão sem intenção de matar que resulta em morte.",
    ),
    IndicadorRef(
        "morte-intervencao-policial",
        "Morte decorrente de intervenção policial",
        "mvi",
        VIT,
        HAB,
        "Mortes decorrentes de intervenções de policiais civis e militares, em serviço e fora "
        "de serviço (letalidade policial).",
    ),
    IndicadorRef(
        "roubo",
        "Roubo (total)",
        None,
        OCO,
        HAB,
        "Subtração de bens mediante violência ou grave ameaça. O total pode ser menor que a soma "
        "dos subtipos, porque uma ocorrência pode entrar em mais de um deles.",
    ),
    IndicadorRef("roubo-veiculo", "Roubo de veículo", "roubo", OCO, VEI, "Roubo de veículos."),
    IndicadorRef("roubo-celular", "Roubo de celular", "roubo", OCO, HAB, "Roubo de celulares."),
    IndicadorRef(
        "roubo-transeunte",
        "Roubo a transeunte",
        "roubo",
        OCO,
        HAB,
        "Roubo a pessoas na via pública.",
    ),
    IndicadorRef(
        "roubo-residencia", "Roubo a residência", "roubo", OCO, HAB, "Roubo a residências."
    ),
    IndicadorRef(
        "roubo-estabelecimento-comercial",
        "Roubo a estabelecimento comercial",
        "roubo",
        OCO,
        HAB,
        "Roubo a estabelecimentos comerciais.",
    ),
    IndicadorRef(
        "roubo-instituicao-financeira",
        "Roubo a instituição financeira",
        "roubo",
        OCO,
        INS,
        "Roubo a bancos, caixas eletrônicos e empresas de transporte de valores.",
    ),
    IndicadorRef("roubo-carga", "Roubo de carga", "roubo", OCO, HAB, "Roubo de cargas."),
    IndicadorRef(
        "furto",
        "Furto",
        None,
        OCO,
        None,
        "Subtração de bens sem violência ou grave ameaça. Agrupador sem registros próprios: o "
        "Anuário não publica total de furtos, só os de veículos e de celulares.",
    ),
    IndicadorRef("furto-veiculo", "Furto de veículo", "furto", OCO, VEI, "Furto de veículos."),
    IndicadorRef("furto-celular", "Furto de celular", "furto", OCO, HAB, "Furto de celulares."),
)
"""Em pré-ordem da hierarquia: a posição (a partir de 1) é o `ordem` do indicador."""

AGRUPADORES = frozenset({"furto"})
"""Indicadores sem registros próprios."""
