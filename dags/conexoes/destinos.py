import os
import polars as pl
import snowflake.connector

def conectar_snowflake():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )

def carregar_snowflake(df: pl.DataFrame, table: str) -> int:
    conn_str = (
        f"snowflake://{os.environ['SNOWFLAKE_USER']}:{os.environ['SNOWFLAKE_PASSWORD']}"
        f"@{os.environ['SNOWFLAKE_ACCOUNT']}/{os.environ['SNOWFLAKE_DATABASE']}"
        f"/{os.environ['SNOWFLAKE_SCHEMA']}?warehouse={os.environ['SNOWFLAKE_WAREHOUSE']}"
    )
    return df.write_database(
        table, connection=conn_str, engine="adbc", if_table_exists="replace"
    )
