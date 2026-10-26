"""Cache HTTP das respostas (RNF11).

Como os dados só mudam em uma nova importação, as respostas levam
Cache-Control: public, max-age=86400 e um ETag derivado da versão da carga gravada pelo
comando importar_anuario. A mudança de versão altera o ETag e invalida o cache do Traefik e
do navegador.
"""

MAX_AGE = 86_400
