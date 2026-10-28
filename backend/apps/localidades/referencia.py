"""Dados de referência das localidades: Brasil, 5 regiões e 27 UFs.

Fixos, revisados em PR e carregados pelo comando importar_anuario antes dos fatos. Os códigos são
os do IBGE, em texto (ajuste 2 do modelo; contrato, seção 1.1). Os aliases cobrem os rótulos das
duas planilhas: "Região Norte" no FBSP e "Norte" no IBGE; os nomes das UFs são iguais nas duas.
Um rótulo novo entra aqui, nunca por correspondência aproximada (docs/importacao.md, seção 4.5).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegiaoRef:
    sigla: str
    nome: str
    tipo: str  # "pais" ou "regiao"
    codigo_ibge: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class EstadoRef:
    sigla: str
    nome: str
    codigo_ibge: str
    regiao: str  # sigla da região


REGIOES: tuple[RegiaoRef, ...] = (
    RegiaoRef("BR", "Brasil", "pais", "1"),
    RegiaoRef("N", "Norte", "regiao", "1", ("Região Norte",)),
    RegiaoRef("NE", "Nordeste", "regiao", "2", ("Região Nordeste",)),
    RegiaoRef("SE", "Sudeste", "regiao", "3", ("Região Sudeste",)),
    RegiaoRef("S", "Sul", "regiao", "4", ("Região Sul",)),
    RegiaoRef(
        "CO",
        "Centro-Oeste",
        "regiao",
        "5",
        ("Região Centro-Oeste", "Centro Oeste", "Região Centro Oeste"),
    ),
)
"""Em ordem canônica: Brasil, depois as regiões por código do IBGE."""

ESTADOS: tuple[EstadoRef, ...] = (
    EstadoRef("AC", "Acre", "12", "N"),
    EstadoRef("AL", "Alagoas", "27", "NE"),
    EstadoRef("AM", "Amazonas", "13", "N"),
    EstadoRef("AP", "Amapá", "16", "N"),
    EstadoRef("BA", "Bahia", "29", "NE"),
    EstadoRef("CE", "Ceará", "23", "NE"),
    EstadoRef("DF", "Distrito Federal", "53", "CO"),
    EstadoRef("ES", "Espírito Santo", "32", "SE"),
    EstadoRef("GO", "Goiás", "52", "CO"),
    EstadoRef("MA", "Maranhão", "21", "NE"),
    EstadoRef("MG", "Minas Gerais", "31", "SE"),
    EstadoRef("MS", "Mato Grosso do Sul", "50", "CO"),
    EstadoRef("MT", "Mato Grosso", "51", "CO"),
    EstadoRef("PA", "Pará", "15", "N"),
    EstadoRef("PB", "Paraíba", "25", "NE"),
    EstadoRef("PE", "Pernambuco", "26", "NE"),
    EstadoRef("PI", "Piauí", "22", "NE"),
    EstadoRef("PR", "Paraná", "41", "S"),
    EstadoRef("RJ", "Rio de Janeiro", "33", "SE"),
    EstadoRef("RN", "Rio Grande do Norte", "24", "NE"),
    EstadoRef("RO", "Rondônia", "11", "N"),
    EstadoRef("RR", "Roraima", "14", "N"),
    EstadoRef("RS", "Rio Grande do Sul", "43", "S"),
    EstadoRef("SC", "Santa Catarina", "42", "S"),
    EstadoRef("SE", "Sergipe", "28", "NE"),
    EstadoRef("SP", "São Paulo", "35", "SE"),
    EstadoRef("TO", "Tocantins", "17", "N"),
)
"""Em ordem canônica: por sigla."""

REGIAO_DA_UF: dict[str, str] = {estado.sigla: estado.regiao for estado in ESTADOS}
