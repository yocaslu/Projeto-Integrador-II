"""Leitura e validação dos parâmetros de consulta (contrato, seção 2).

Funções puras, sem banco: os conjuntos válidos (siglas, slugs, intervalo de anos) vêm de quem
chama. Todos os erros de uma requisição são acumulados e levantados juntos em `validar()`, como
`ValidationError({parametro: [mensagens]})`; erros de combinação usam a chave `""` (contrato,
seção 6). O `apps/api/erros.py` converte isso em Problem Details.

Uso típico numa view:

    leitor = LeitorParametros(request.query_params, PERMITIDOS, paginado=True)
    locais = leitor.localidades(ufs_validas, regioes_validas)
    anos = leitor.anos(intervalo)
    leitor.validar()
"""

import re
from collections import defaultdict
from collections.abc import Collection, Iterable
from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

COMBINACAO = ""
"""Chave dos erros de combinação entre parâmetros (contrato, seção 6)."""

FORMATO = "formato"
PAGINA = "pagina"
TAMANHO = "tamanho"
TAMANHO_PADRAO = 100
TAMANHO_MAXIMO = 1000

NIVEIS = ("pais", "regiao", "uf")
"""Níveis de localidade, na ordem canônica (contrato, seção 1.1)."""

SIGLA_PAIS = "BR"

_ANO = re.compile(r"^\d{4}$")
_INTEIRO = re.compile(r"^\d+$")


@dataclass(frozen=True)
class Anos:
    """Filtro de anos: `ano` (lista) ou o intervalo fechado `ano_min`/`ano_max`.

    Todos `None` quando nenhum dos três foi informado.
    """

    ano: tuple[int, ...] | None = None
    ano_min: int | None = None
    ano_max: int | None = None


@dataclass(frozen=True)
class Localidades:
    """Resultado da regra de `nivel`, `uf` e `regiao` (contrato, seção 4.7.2).

    - `niveis`: níveis efetivos, na ordem canônica.
    - `ufs`: siglas de UF a filtrar (só com `niveis == ("uf",)`), ou `None`.
    - `regioes`: siglas de região a filtrar, ou `None`. Com `niveis == ("uf",)`, significa
      "as UFs dessas regiões"; com `niveis == ("regiao",)`, "os agregados dessas regiões".
    """

    niveis: tuple[str, ...]
    ufs: tuple[str, ...] | None = None
    regioes: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Paginacao:
    pagina: int = 1
    tamanho: int = TAMANHO_PADRAO


class LeitorParametros:
    """Lê os parâmetros de um recurso e acumula os erros de validação.

    Na construção, confere as regras gerais (contrato, seção 2): parâmetro desconhecido,
    repetido ou vazio, e `pagina`/`tamanho` fora de recurso paginado ou junto com CSV. Os métodos
    leem cada parâmetro já convertido e devolvem `None` quando ele não veio ou é inválido; o erro
    fica guardado até `validar()`.

    `permitidos` são os parâmetros do recurso; `formato` é sempre aceito (o valor, json ou csv, é
    validado pela negociação de conteúdo, com 406). `csv` indica que a negociação escolheu CSV
    (por `formato=csv` ou pelo cabeçalho `Accept`).
    """

    def __init__(
        self,
        query_params,
        permitidos: Iterable[str],
        *,
        paginado: bool = False,
        csv: bool = False,
    ):
        self._params = query_params
        self._erros: dict[str, list[str]] = defaultdict(list)
        self._invalidos: set[str] = set()
        aceitos = set(permitidos) | {FORMATO}
        if paginado:
            aceitos |= {PAGINA, TAMANHO}

        for nome in query_params:
            valores = query_params.getlist(nome)
            if nome in (PAGINA, TAMANHO) and not paginado:
                self._erro(nome, "Este recurso não é paginado.")
            elif nome not in aceitos:
                self._erro(nome, "Parâmetro desconhecido.")
            elif len(valores) > 1:
                self._erro(
                    nome, "Parâmetro repetido; informe vários valores separados por vírgula."
                )
            elif not valores[0].strip():
                self._erro(nome, "Valor vazio.")

        formato = self._bruto(FORMATO)
        self._csv = csv or (formato is not None and formato.lower() == "csv")
        if paginado and self._csv:
            for nome in (PAGINA, TAMANHO):
                if nome in query_params and nome not in self._invalidos:
                    self._erro(nome, "A exportação em CSV é sempre completa; não use paginação.")

    # Erros

    def _erro(self, nome: str, mensagem: str) -> None:
        self._erros[nome].append(mensagem)
        self._invalidos.add(nome)

    def erro(self, nome: str, mensagem: str) -> None:
        """Acrescenta um erro de uma regra que depende de dados (ex.: unidade sem registros)."""
        self._erro(nome, mensagem)

    def valido(self, nome: str) -> bool:
        """Indica se o parâmetro não acumulou erro (informado ou não)."""
        return nome not in self._invalidos

    @property
    def erros(self) -> dict[str, list[str]]:
        return dict(self._erros)

    def validar(self) -> None:
        """Levanta `ValidationError` com todos os erros acumulados, se houver."""
        if self._erros:
            raise ValidationError(dict(self._erros))

    # Leitura

    def informado(self, nome: str) -> bool:
        """Indica se o parâmetro veio na requisição (válido ou não)."""
        return nome in self._params

    def _bruto(self, nome: str) -> str | None:
        if nome not in self._params or nome in self._invalidos:
            return None
        return self._params[nome].strip()

    def lista(
        self,
        nome: str,
        validos: Collection[str] | None = None,
        *,
        maiusculas: bool = False,
    ) -> tuple[str, ...] | None:
        """Lista separada por vírgula (contrato, seção 2, regra 3).

        Espaços em volta de cada item são removidos e itens repetidos são ignorados, mantendo a
        ordem; item vazio → erro. Com `validos`, item fora do conjunto → erro (regra 6). Com
        `maiusculas`, a comparação ignora a caixa e os itens voltam em maiúsculas (siglas).
        """
        bruto = self._bruto(nome)
        if bruto is None:
            return None
        itens: list[str] = []
        for item in (parte.strip() for parte in bruto.split(",")):
            if not item:
                self._erro(nome, "Item vazio na lista.")
                return None
            if maiusculas:
                item = item.upper()
            if validos is not None and item not in validos:
                self._erro(nome, f"Valor não reconhecido: {item}.")
                continue
            if item not in itens:
                itens.append(item)
        return None if nome in self._invalidos else tuple(itens)

    def unico(
        self,
        nome: str,
        validos: Collection[str] | None = None,
        *,
        maiusculas: bool = False,
        obrigatorio: bool = False,
    ) -> str | None:
        """Um único valor (ex.: `indicador` em `/ranking/`); vírgula → erro."""
        if obrigatorio and nome not in self._params:
            self._erro(nome, "Parâmetro obrigatório.")
            return None
        bruto = self._bruto(nome)
        if bruto is None:
            return None
        if "," in bruto:
            self._erro(nome, "Informe um único valor.")
            return None
        valor = bruto.upper() if maiusculas else bruto
        if validos is not None and valor not in validos:
            self._erro(nome, f"Valor não reconhecido: {valor}.")
            return None
        return valor

    def booleano(self, nome: str, padrao: bool = False) -> bool:
        """Só `true` e `false`, em minúsculas (contrato, seção 2, regra 7)."""
        bruto = self._bruto(nome)
        if bruto is None:
            return padrao
        if bruto == "true":
            return True
        if bruto == "false":
            return False
        self._erro(nome, "Use true ou false.")
        return padrao

    def _converter_ano(self, nome: str, texto: str, intervalo: tuple[int, int]) -> int | None:
        if not _ANO.match(texto):
            self._erro(nome, f"Ano inválido: {texto}.")
            return None
        ano = int(texto)
        minimo, maximo = intervalo
        if not minimo <= ano <= maximo:
            self._erro(nome, f"Ano fora do intervalo disponível ({minimo} a {maximo}).")
            return None
        return ano

    def ano(
        self, nome: str, intervalo: tuple[int, int], *, obrigatorio: bool = False
    ) -> int | None:
        """Um único ano dentro de `intervalo` (contrato, seção 2, regra 8)."""
        bruto = self.unico(nome, obrigatorio=obrigatorio)
        if bruto is None:
            return None
        return self._converter_ano(nome, bruto, intervalo)

    def anos(self, intervalo: tuple[int, int]) -> Anos:
        """`ano` (lista) ou `ano_min`/`ano_max` (contrato, seção 2, regras 8 e 9).

        `intervalo` é o (primeiro, último) ano com registros, lido do banco pelo chamador.
        """
        lista: list[int] = []
        for texto in self.lista("ano") or ():
            ano = self._converter_ano("ano", texto, intervalo)
            if ano is not None and ano not in lista:
                lista.append(ano)
        ano_min = self.ano("ano_min", intervalo)
        ano_max = self.ano("ano_max", intervalo)

        if self.informado("ano") and (self.informado("ano_min") or self.informado("ano_max")):
            self._erro(COMBINACAO, "ano não pode ser usado junto com ano_min ou ano_max.")
            return Anos()
        if ano_min is not None and ano_max is not None and ano_min > ano_max:
            self._erro(COMBINACAO, "ano_min não pode ser maior que ano_max.")
            return Anos()
        if "ano" in self._invalidos:
            return Anos(ano_min=ano_min, ano_max=ano_max)
        return Anos(ano=tuple(lista) if lista else None, ano_min=ano_min, ano_max=ano_max)

    def localidades(
        self, ufs_validas: Collection[str], regioes_validas: Collection[str]
    ) -> Localidades:
        """Regra de `nivel`, `uf` e `regiao` (contrato, seção 4.7.2).

        Sem `nivel` explícito a resposta tem um único nível; misturar níveis só por lista em
        `nivel`, e então sem `uf` nem `regiao`. `regioes_validas` são as siglas das cinco regiões
        (sem `BR`). Siglas sem diferença de caixa.
        """
        niveis = self.lista("nivel", NIVEIS)
        ufs = self.lista("uf", ufs_validas, maiusculas=True)
        regioes = self._regioes(regioes_validas)
        nivel_informado = self.informado("nivel")
        tem_uf = self.informado("uf")
        tem_regiao = self.informado("regiao")

        if niveis is not None:
            niveis = tuple(nivel for nivel in NIVEIS if nivel in niveis)

        if tem_uf and tem_regiao:
            self._erro(COMBINACAO, "uf e regiao são mutuamente exclusivos; use só um deles.")
        elif tem_uf and nivel_informado and niveis is not None and niveis != ("uf",):
            if len(niveis) > 1:
                self._erro(COMBINACAO, _MENSAGEM_MISTURA)
            else:
                self._erro(COMBINACAO, "uf só pode ser usado com nivel=uf.")
        elif tem_regiao and not nivel_informado:
            self._erro(
                "regiao",
                "Ambíguo sem nivel: use nivel=uf para as UFs da região ou nivel=regiao para o "
                "agregado regional.",
            )
        elif tem_regiao and niveis is not None and len(niveis) > 1:
            self._erro(COMBINACAO, _MENSAGEM_MISTURA)
        elif tem_regiao and niveis == ("pais",):
            self._erro(COMBINACAO, "regiao não pode ser usado com nivel=pais.")

        if niveis is None:
            niveis = ("uf",)
        return Localidades(niveis=niveis, ufs=ufs, regioes=regioes)

    def _regioes(self, regioes_validas: Collection[str]) -> tuple[str, ...] | None:
        bruto = self._bruto("regiao")
        if bruto is not None and SIGLA_PAIS in (
            parte.strip().upper() for parte in bruto.split(",")
        ):
            self._erro("regiao", "BR não é uma região; use nivel=pais para o Brasil.")
            return None
        return self.lista("regiao", regioes_validas, maiusculas=True)

    def ordenacao(self, permitidos: Collection[str]) -> tuple[str, ...]:
        """Campos de `ordenar`, com `-` para ordem decrescente (contrato, seção 4.7.3).

        Devolve só os campos pedidos; a ordem padrão do recurso e o `id` que completam o
        desempate ficam com quem chama. Campo fora de `permitidos` ou repetido → erro.
        """
        campos = self.lista("ordenar")
        if campos is None:
            return ()
        vistos: set[str] = set()
        for campo in campos:
            nome = campo.removeprefix("-")
            if nome not in permitidos:
                self._erro("ordenar", f"Campo de ordenação não reconhecido: {campo}.")
            elif nome in vistos:
                self._erro("ordenar", f"Campo de ordenação repetido: {nome}.")
            vistos.add(nome)
        return () if "ordenar" in self._invalidos else campos

    def paginacao(self) -> Paginacao:
        """`pagina` (≥ 1, padrão 1) e `tamanho` (1 a 1000, padrão 100)."""
        pagina = self._inteiro(PAGINA, minimo=1)
        tamanho = self._inteiro(TAMANHO, minimo=1, maximo=TAMANHO_MAXIMO)
        return Paginacao(
            pagina=1 if pagina is None else pagina,
            tamanho=TAMANHO_PADRAO if tamanho is None else tamanho,
        )

    def _inteiro(self, nome: str, *, minimo: int, maximo: int | None = None) -> int | None:
        bruto = self._bruto(nome)
        if bruto is None:
            return None
        if not _INTEIRO.match(bruto):
            self._erro(nome, "Informe um número inteiro.")
            return None
        valor = int(bruto)
        if valor < minimo or (maximo is not None and valor > maximo):
            limite = (
                f"entre {minimo} e {maximo}" if maximo is not None else f"maior ou igual a {minimo}"
            )
            self._erro(nome, f"O valor deve estar {limite}.")
            return None
        return valor


_MENSAGEM_MISTURA = (
    "uf e regiao filtram um nível só; com mais de um nível em nivel, não os use. "
    "Para UF, região e Brasil lado a lado, use /comparacao/."
)
