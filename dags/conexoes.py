import os
import polars as pl
import snowflake.connector
from dotenv import load_dotenv
from contextlib import contextmanager
import time
load_dotenv()

@contextmanager
def cronometro(nome: str):
    t0 = time.perf_counter()
    yield
    print(f"{nome}: {time.perf_counter() - t0:.1f}s")


def uri_mysql() -> str:
    return (
        f"mysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
        f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
    )

def extrair(query: str, partition_on: str | None = None,
            partition_num: int = 4) -> pl.DataFrame:
    df = pl.read_database_uri(
        query,
        uri=uri_mysql(),
        partition_on=partition_on,
        partition_num=partition_num,
    )
    df.columns = [c.upper() for c in df.columns]
    return df

def conectar_snowflake():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )

def carregar_snowflake(df: pl.DataFrame, tabela: str) -> int:
    conn_str = (
        f"snowflake://{os.environ['SNOWFLAKE_USER']}:{os.environ['SNOWFLAKE_PASSWORD']}"
        f"@{os.environ['SNOWFLAKE_ACCOUNT']}/{os.environ['SNOWFLAKE_DATABASE']}"
        f"/{os.environ['SNOWFLAKE_SCHEMA']}?warehouse={os.environ['SNOWFLAKE_WAREHOUSE']}"
    )
    return df.write_database(
        tabela, connection=conn_str, engine="adbc", if_table_exists="replace"
    )


def conferir_carga(df: pl.DataFrame, tabela: str) -> None:
    esperado = df.height
    conn = conectar_snowflake()
    try:
        real = conn.cursor().execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
    finally:
        conn.close()
    status = "OK" if esperado == real else "ERROR"
    print(f"[{status}] {tabela}: extraído={esperado} | snowflake={real}")

def pipeline(query: str, tabela: str, origem=extrair, destino=carregar_snowflake) -> int:
    with cronometro("extração"):
        df = origem(query)
    with cronometro("carga"):
        nrows = destino(df, tabela)
    conferir_carga(df, tabela)
    print(f"{tabela}: {nrows} linhas")
    return nrows
