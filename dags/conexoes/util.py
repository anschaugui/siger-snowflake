import os
from datetime import date

from conexoes import destinos


def montar_uri(prefixo: str, esquema: str) -> str:
    """
    Monta uma URI de conexão a partir de variáveis de ambiente prefixadas.

    Busca no .env as variáveis {prefixo}_USER, {prefixo}_PASSWORD,
    {prefixo}_HOST, {prefixo}_PORT e {prefixo}_DB, e monta a URI no
    formato `esquema://user:senha@host:porta/banco`.

    Exemplo:
        montar_uri("MYSQL", "mysql")
        # busca MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DB
        # -> "mysql://user:senha@192.168.0.6:3306/02794s000"

    :param prefixo: prefixo das variáveis no .env (ex: "MYSQL", "SENDA")
    :param esquema: protocolo da URI de conexão (ex: "mysql", "postgresql") —
        NÃO é o schema do banco de dados, é o driver/protocolo
    :return: URI de conexão completa, pronta pra usar em pl.read_database_uri
    :raises KeyError: se alguma das 5 variáveis esperadas não existir no .env
    """
    return (
        f"{esquema}://{os.environ[f'{prefixo}_USER']}:{os.environ[f'{prefixo}_PASSWORD']}"
        f"@{os.environ[f'{prefixo}_HOST']}:{os.environ[f'{prefixo}_PORT']}/{os.environ[f'{prefixo}_DB']}"
    )

def lista_sql(valores) -> str:
    """Monta 'a','b','c' a partir de qualquer lista, pronta pra colar num IN (...)."""
    return ",".join(f"'{v}'" for v in valores)

def periodo_janela(n_meses: int = 2) -> list[int]:
    hoje = date.today()
    periodos = []
    ano, mes = hoje.year, hoje.month
    for _ in range(n_meses):
        periodos.append(ano * 100 + mes)
        mes -=1
        if mes == 0:
            mes, ano = 12, ano - 1
    return periodos

def por_periodo(df,tabela):
    return destinos.carregar_s3_particionado(df, tabela, "PERIODO")