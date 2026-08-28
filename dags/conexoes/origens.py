import os
import polars as pl
from .util import montar_uri


def extrair_mysql(query: str) -> pl.DataFrame:
    df = pl.read_database_uri(query, uri=montar_uri("MYSQL", "mysql"))
    df.columns = [c.upper() for c in df.columns]
    return df

def extrair_postgres_senda(query: str) -> pl.DataFrame:
    df = pl.read_database_uri(query, uri=montar_uri("POSTGRESQL", "DW"))
    df.columns = [c.upper() for c in df.columns]
    return df