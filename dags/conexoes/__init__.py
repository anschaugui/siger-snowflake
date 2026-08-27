import time
from contextlib import contextmanager
from dotenv import load_dotenv
import polars as pl

load_dotenv()

from .origens import extrair_mysql, extrair_postgres_senda
from .destinos import carregar_snowflake, conectar_snowflake


@contextmanager
def cronometro(nome: str):
    t0 = time.perf_counter()
    yield
    print(f"{nome}: {time.perf_counter() - t0:.1f}s")


def conferir_carga(df: pl.DataFrame, tabela: str) -> None:
    esperado = df.height
    conn = conectar_snowflake()
    try:
        real = conn.cursor().execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
    finally:
        conn.close()
    status = "OK" if esperado == real else "ERROR"
    print(f"[{status}] {tabela}: extraído={esperado} | snowflake={real}")


def pipeline(query: str, tabela: str, origem=extrair_mysql, destino=carregar_snowflake) -> int:
    origem = origem or extrair_mysql
    destino = destino or carregar_snowflake
    with cronometro("extração"):
        df = origem(query)
    with cronometro("carga"):
        nrows = destino(df, tabela)
    conferir_carga(df, tabela)
    print(f"{tabela}: {nrows} linhas")
    return nrows