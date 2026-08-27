import os
import polars as pl
from websockets import uri


def extrair_mysql(query: str) -> pl.DataFrame:
    uri = f"mysql://{os.environ['MYSQL_USER']}:{os.environ['MYSQL_PASSWORD']}@{os.environ['MYSQL_HOST']}:{os.environ['MYSQL_PORT']}/{os.environ['MYSQL_DB']}"
    df = pl.read_database_uri(query, uri=uri)
    df.columns = [c.upper() for c in df.columns]
    return df

def extrair_postgres_senda(query: str) -> pl.DataFrame:
    uri = f"postgresql://{os.environ['SENDA_USER']}:{os.environ['SENDA_PASSWORD']}@{os.environ['SENDA_HOST']}:{os.environ['SENDA_PORT']}/{os.environ['SENDA_DB']}"
    df = pl.read_database_uri(query, uri=uri)
    df.columns = [c.upper() for c in df.columns]
    return df