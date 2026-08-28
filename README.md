# ETL SIGER → Snowflake

Pipeline de extração e carga: MySQL/MariaDB (SIGER, ERP da Grupo Sugar/Neorubber) → Snowflake, orquestrado via Apache Airflow.

## Stack

- **Extração**: Polars + connectorx (leitura paralela via Arrow, sem passar por Pandas)
- **Carga**: ADBC (`write_database`) — escreve direto do Polars pro Snowflake, sem conversão intermediária
- **Orquestração**: Apache Airflow 2.10.4, rodando em Docker Compose (LocalExecutor + Postgres)
- **Origem hoje**: MySQL/MariaDB (SIGER, schema `02794s000`)
- **Destino hoje**: Snowflake (`SUGARSHOES.DW`)

## Pré-requisitos

- Docker Desktop instalado e rodando (WSL2 habilitado, no Windows)
- Python 3.12+ com um venv local (pra rodar/testar fora do Docker)
- Acesso de rede ao MySQL do SIGER
- Credenciais de um usuário Snowflake com permissão de escrita no schema de destino

## Setup

1. Clona o repositório e cria o `.env` a partir do exemplo:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Preenche o `.env` com suas credenciais (peça pro time se não tiver):

   ```
   MYSQL_HOST=
   MYSQL_PORT=3306
   MYSQL_USER=
   MYSQL_PASSWORD=
   MYSQL_DB=

   SNOWFLAKE_ACCOUNT=
   SNOWFLAKE_USER=
   SNOWFLAKE_PASSWORD=
   SNOWFLAKE_WAREHOUSE=
   SNOWFLAKE_DATABASE=
   SNOWFLAKE_SCHEMA=
   ```

   **Nunca commita o `.env`** — ele já está no `.gitignore`. Se tiver dúvida, confirma com:

   ```powershell
   git check-ignore -v .env
   ```

3. Cria as pastas que o Airflow precisa (se ainda não existirem):

   ```powershell
   mkdir logs, plugins
   ```

4. Sobe o ambiente:

   ```powershell
   docker compose up airflow-init
   docker compose up -d
   ```

5. Acessa `http://localhost:8080` — login `admin` / `admin`.

## Rodando um ETL sem o Airflow (teste local rápido)

```powershell
python .\dags\main.py fato_compra    # roda um ETL específico
python .\dags\main.py                # roda todos, em sequência
```

**Não roda um arquivo aninhado direto** (`python .\dags\fatos\fato_compra.py`) — quebra com `ModuleNotFoundError: No module named 'conexoes'`. O Python usa a pasta do próprio arquivo como raiz de import, e `conexoes/` só é visível a partir de `dags/`. Use sempre `main.py`.

## Estrutura

```
dags/
├── main.py                    ← entrypoint pra rodar local (CLI)
├── catalogo.py                ← registro central: {nome: (função, schedule)}
├── etl_siger_snowflake.py     ← gera 1 DAG por ETL no Airflow, a partir do catálogo
├── conexoes/
│   ├── __init__.py            ← pipeline(), cronometro(), conferir_carga()
│   ├── util.py                ← montar_uri() — monta URI a partir de prefixo no .env
│   ├── origens.py             ← extrair_mysql, extrair_postgres_senda...
│   └── destinos.py            ← carregar_snowflake, conectar_snowflake
├── dimensoes/                 ← um arquivo por dimensão
└── fatos/                     ← um arquivo por fato
```

## Como adicionar um ETL novo

Cria o arquivo em `dimensoes/` ou `fatos/`, seguindo este molde:

```python
from conexoes import pipeline

query = """
    SELECT ...
"""

def executar() -> int:
    return pipeline(query, "NOME_DA_TABELA")

if __name__ == "__main__":
    executar()
```

Registra em `catalogo.py`:

```python
from fatos.novo_arquivo import executar as novo_etl

ETLS = {
    ...
    "novo_etl": (novo_etl, "0 6 * * *"),  # cron: min hora dia mês dia-semana
}
```

**Atenção ao import** — sempre `from pasta.arquivo import executar as nome`, nunca `from pasta import arquivo`. O segundo pega o **módulo**, não a função, e quebra silenciosamente só na hora de rodar (`TypeError: 'module' object is not callable` local, ou `python_callable param must be callable` no Airflow).

## Como adicionar uma origem/destino novo

Em `conexoes/origens.py` (ou `destinos.py`):

```python
def extrair_novo_sistema(query: str) -> pl.DataFrame:
    df = pl.read_database_uri(query, uri=montar_uri("PREFIXO", "protocolo"))
    df.columns = [c.upper() for c in df.columns]
    return df
```

E no `.env`, cinco variáveis com o mesmo prefixo: `PREFIXO_USER`, `PREFIXO_PASSWORD`, `PREFIXO_HOST`, `PREFIXO_PORT`, `PREFIXO_DB`.

## Erros conhecidos (poupa tempo de debug)

- **`ModuleNotFoundError` no Docker mas funciona local** → geralmente `websockets`/`idlelib`/`multiprocessing` sobrando de autocomplete errado do PyCharm. Confere imports não usados antes de rodar no container.
- **Mudou o `.env` mas o Airflow continua com valor antigo** → `docker compose restart` **não recarrega** variáveis de ambiente. Precisa `docker compose down && docker compose up -d`.
- **`Access denied` no MySQL do nada** → normalmente é rotação de senha feita pelo DBA, não bug no código. Confirma com TI antes de investigar o script.
- **Aviso de `pyarrow` incompatível** → cosmético até agora, mas fixa a versão se quiser silenciar: `pip install "pyarrow<24,>=14.0.1"`.