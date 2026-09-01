from dotenv import load_dotenv
load_dotenv()

import os
import time
from contextlib import contextmanager

import polars as pl

from .origens import extrair_mysql, extrair_postgres_senda
from .destinos import carregar_snowflake, conectar_snowflake, carregar_s3


DESTINOS = {
    "s3": carregar_s3,
    "snowflake": carregar_snowflake,
}

def destinos_configurados() -> list[str]:
    """Lê DW_DESTINOS e FALHA ALTO se estiver errado.

    ⚠ Falhar aqui é de propósito. O erro tem de aparecer ANTES da extração —
      que é a parte cara (13s contra 0,2s da carga). Um destino digitado errado
      passando batido significa extrair tudo e descartar em silêncio.
"""
    nomes = [n.strip().lower() for n in os.getenv("DW_DESTINOS","s3").split(",") if n.strip()]
    if not nomes:
        raise ValueError(
            "DW_DESTINOS está vazio. A extração rodaria e o dado seria descartado"
            "Definono .evn, ex.: DW_DESTINOS=s3"
        )
    return nomes

@contextmanager
def cronometro(nome:str):
    t0 = time.perf_counter()
    yield
    print(f"  {nome}: {time.perf_counter() - t0} segundos")

def conferir_carga(df: pl.DataFrame, tabela: str) -> None:
    """Compara o que saiu da origem com o que chegou no Snowflake.

    ⚠ Só faz sentido para o Snowflake — no S3 não há tabela para contar. Por
      isso o pipeline só chama esta função quando 'snowflake' está nos destinos.
    """
    esperado = df.height
    conn = conectar_snowflake()
    try:
        real = conn.cursor().execute(f"SELECT * FROM {tabela}").fetchone()[0]
    finally:
        conn.close()
    status = "OK" if esperado == real else "Erro"
    print(f"  [{status}] {tabela}: extraído={esperado} | snowflake={real}")

def pipeline(query: str,
             tabela: str,
             *,
             origem=extrair_mysql,
             particao: str | None = None,
             destinos: list[str] | None = None,
             ) -> int:
    nomes = destinos or destinos_configurados()
    with cronometro("Extração"):
        df = origem(query)

    for nome in nomes:
        with cronometro(f"carga {nome}"):
            DESTINOS[nome](df, tabela, particao)
        if nome == "snowflake":
            conferir_carga(df, tabela)

    print(f"{tabela}: {df.height} linhas -> {', '.join(nomes)}")
    return df.height