import io
import os
import polars as pl
import snowflake.connector
import boto3

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


def conectar_s3():
    return boto3.client(
        "s3",
        region_name=os.environ["AWS_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )

def carregar_s3(caminho_local: str, chave:str) -> None:
    conectar_s3().upload_file(caminho_local, os.environ["AWS_S3_BUCKET"], chave)

def carregar_s3_parquet(df: pl.DataFrame, tabela:str) -> int:
    buffer = io.BytesIO()
    df.write_parquet(buffer)
    conectar_s3().put_object(
        Bucket=os.environ["AWS_S3_BUCKET"],
        Key=f'silver/{tabela}/{tabela}.parquet',
        Body=buffer.getvalue(),
    )
    return df.height

def carregar_s3_particionado(df: pl.DataFrame, tabela:str, coluna_particao:str) -> int:
    for valor in df[coluna_particao].unique():
        parte = df.filter(pl.col(coluna_particao) == valor)
        buffer = io.BytesIO()
        parte.write_parquet(buffer)
        conectar_s3().put_object(
            Bucket=os.environ["AWS_S3_BUCKET"],
            Key=f'silver/{tabela}/{tabela}_{valor}.parquet',
            Body=buffer.getvalue(),
        )
    return df.height