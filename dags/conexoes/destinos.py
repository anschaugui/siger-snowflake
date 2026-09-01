import io
import os
import polars as pl
import snowflake.connector
import boto3


# ── SNOWFLAKE ────────────────────────────────────────────────────────────────
def conectar_snowflake():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )


def carregar_snowflake(df: pl.DataFrame, tabela: str, particao: str | None = None) -> int:
    """
    ⚠ `particao` é IGNORADA de propósito. O Snowflake não tem pasta, e a carga é
      replace da tabela inteira. O argumento existe só para a assinatura bater
      com a dos outros destinos — é isso que deixa o pipeline chamar qualquer
      destino sem precisar saber qual é.

    ⚠ engine="adbc". O Polars aceita só 'sqlalchemy' ou 'adbc'; não existe
      engine 'snowflake'.
    """
    conn_str = (
        f"snowflake://{os.environ['SNOWFLAKE_USER']}:{os.environ['SNOWFLAKE_PASSWORD']}"
        f"@{os.environ['SNOWFLAKE_ACCOUNT']}/{os.environ['SNOWFLAKE_DATABASE']}"
        f"/{os.environ['SNOWFLAKE_SCHEMA']}?warehouse={os.environ['SNOWFLAKE_WAREHOUSE']}"
    )
    df.write_database(tabela, connection=conn_str, engine="adbc", if_table_exists="replace")
    return df.height


# ── S3 ───────────────────────────────────────────────────────────────────────
def conectar_s3():
    """⚠ client, NÃO resource. `boto3.resource` não expõe put_object."""
    return boto3.client(
        "s3",
        region_name=os.environ["AWS_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )


def carregar_s3(df: pl.DataFrame, tabela: str, particao: str | None = None) -> int:
    """
    Grava Parquet no S3. Com `particao`, usa o formato Hive `coluna=valor/`.

    ⚠ A COLUNA DE PARTIÇÃO SAI DO ARQUIVO (`.drop`). O valor já está no caminho;
      mantê-lo dentro do Parquet faz o Glue montar a tabela com a coluna
      DUPLICADA e o Athena recusa com HIVE_INVALID_METADATA.

    ⚠ A CHAVE PRECISA DO `{coluna}={valor}/`. Sem isso os 46 arquivos vão todos
      para o mesmo caminho e sobrescrevem uns aos outros — sem erro nenhum.

    ⚠ O `return` fica FORA do laço. Dentro dele, só a primeira partição sobe.

    ⚠ O cliente boto3 nasce FORA do laço: criar um custa ~34ms, e com 46
      partições isso eram 1,6s jogados fora por execução.
    """
    s3 = conectar_s3()
    bucket = os.environ["AWS_S3_BUCKET"]

    if not particao:
        buffer = io.BytesIO()
        df.write_parquet(buffer)
        s3.put_object(
            Bucket=bucket,
            Key=f"silver/{tabela}/{tabela}.parquet",
            Body=buffer.getvalue(),
        )
        return df.height

    coluna = particao.lower()
    for valor in df[particao].unique():
        parte = df.filter(pl.col(particao) == valor).drop(particao)
        buffer = io.BytesIO()
        parte.write_parquet(buffer)
        s3.put_object(
            Bucket=bucket,
            Key=f"silver/{tabela}/{coluna}={valor}/{tabela}.parquet",
            Body=buffer.getvalue(),
        )
    return df.height


def enviar_arquivo(caminho_local: str, chave: str) -> None:
    """
    Sobe um arquivo pronto do disco.

    ⚠ NÃO é destino de pipeline — a assinatura é outra. Antes esta função se
      chamava `carregar_s3`, o mesmo nome do destino acima; renomeada para os
      dois não colidirem.
    """
    conectar_s3().upload_file(caminho_local, os.environ["AWS_S3_BUCKET"], chave)