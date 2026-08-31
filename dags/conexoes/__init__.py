import time
from contextlib import contextmanager
from dotenv import load_dotenv
import polars as pl
from .destinos import carregar_snowflake, conectar_snowflake, carregar_s3_parquet


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


def pipeline(query: str,
             tabela: str,
             origem=extrair_mysql,
             destino=None,
             arquivo_s3=None,
             params=None
             ) -> int:
    origem = origem or extrair_mysql
    with cronometro('extração'):
        df = origem(query, params) if params else origem(query)

    # error se destino e arquivos3 vazios
    if not destino and not arquivo_s3:
        raise ValueError(
            f'{tabela}: nenhum destino informado (destino= e arquivo_s3= vazios).'
            'A extração rodou, mas o dado seria descartado sem isso'
        )

    nrows = df.height
    if destino:
        with cronometro('carga'):
            nrows = destino(df, tabela)
        conferir_carga(df, tabela)
    if arquivo_s3:
        with cronometro('arquivo_s3'):
            arquivo_s3(df, tabela)
    print(f"{tabela}: {nrows}")
    return nrows

def pipeline_completo(query:str, tabela:str, **kwargs) -> int:
    """
    O caso comum: Snowflake + s3, sem partição. atalho para pipeline().
    :param query:
    :param tabela:
    :param kwargs:
    :return:
    """
    return pipeline(query, tabela, destinos=carregar_snowflake, arquivo_s3=carregar_s3_parquet, **kwargs)