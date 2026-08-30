# Arquitetura

## Visão geral

O pipeline tem três camadas bem separadas, e a fronteira entre elas é o que mantém o
projeto simples:

```mermaid
flowchart LR
    subgraph origem["Origem"]
        MY[("MySQL / MariaDB<br/>SIGER · 02794s000")]
    end

    subgraph app["Aplicação (dags/)"]
        direction TB
        CAT["catalogo.py<br/><i>registro dos ETLs</i>"]
        ETL["dimensoes/ · fatos/<br/><i>query + executar()</i>"]
        PIPE["conexoes.pipeline()<br/><i>extrair · carregar · conferir</i>"]
        ETL --> PIPE
        CAT -.->|referencia| ETL
    end

    subgraph orq["Orquestração"]
        AF["Airflow<br/>1 DAG por ETL"]
        CLI["main.py<br/><i>CLI local</i>"]
    end

    subgraph destino["Destino"]
        SF[("Snowflake<br/>SUGARSHOES.DW")]
    end

    AF --> CAT
    CLI --> CAT
    MY -->|connectorx / Arrow| PIPE
    PIPE -->|ADBC| SF
```

**O que cada camada sabe:**

- Um **ETL** (`fatos/fato_cte.py`) sabe apenas *qual SQL rodar* e *em que tabela
  gravar*. Não conhece credenciais, driver nem orquestrador.
- O **pacote `conexoes`** sabe *como* falar com cada banco. Não conhece nenhuma regra
  de negócio.
- O **catálogo** e o **orquestrador** sabem *quais* ETLs existem e *quando* rodam. Não
  conhecem SQL.

Trocar o Airflow por outro scheduler, ou o Snowflake por outro destino, mexe em uma
camada só.

---

## Estrutura de arquivos

```text
dags/
├── main.py                    # entrypoint CLI para execução local
├── catalogo.py                # registro central: {nome: (função, cron)}
├── etl_siger_snowflake.py     # fábrica de DAGs — gera 1 DAG por item do catálogo
│
├── conexoes/                  # toda a mecânica de I/O
│   ├── __init__.py            #   pipeline(), cronometro(), conferir_carga()
│   ├── util.py                #   montar_uri()
│   ├── origens.py             #   extrair_mysql(), extrair_postgres_senda()
│   └── destinos.py            #   conectar_snowflake(), carregar_snowflake()
│
├── dimensoes/                 # 1 arquivo por dimensão
│   ├── dim_colaborador.py
│   ├── dim_empresa.py
│   ├── dim_local_est.py
│   ├── dim_municipio.py
│   └── dim_produto.py
│
└── fatos/                     # 1 arquivo por fato
    ├── fato_compra.py
    ├── fato_cte.py
    ├── fato_cte_nota.py
    └── fato_estoque.py
```

---

## O fluxo de uma execução

Toda execução — pelo Airflow ou pela CLI — converge para a mesma função,
`conexoes.pipeline()`:

```mermaid
sequenceDiagram
    autonumber
    participant O as Airflow / CLI
    participant E as ETL (ex.: fato_cte)
    participant P as pipeline()
    participant S as SIGER (MySQL)
    participant W as Snowflake

    O->>E: executar()
    E->>P: pipeline(query, "FATO_CTE")
    activate P
    P->>S: extrair_mysql(query)
    S-->>P: DataFrame Polars (colunas em MAIÚSCULO)
    Note over P: cronômetro: "extração: 12.4s"
    P->>W: carregar_snowflake(df, tabela)
    W-->>P: nº de linhas escritas
    Note over P: cronômetro: "carga: 8.1s"
    P->>W: conferir_carga() — SELECT COUNT(*)
    W-->>P: contagem real
    Note over P: [OK] ou [ERROR]
    P-->>E: nrows
    deactivate P
```

As quatro etapas, no código (`dags/conexoes/__init__.py`):

| Etapa | Função | O que faz |
|---|---|---|
| **Extrair** | `extrair_mysql()` | `pl.read_database_uri()` via connectorx; normaliza os nomes de coluna para maiúsculo |
| **Carregar** | `carregar_snowflake()` | `df.write_database(..., engine="adbc", if_table_exists="replace")` |
| **Conferir** | `conferir_carga()` | `SELECT COUNT(*)` no destino e compara com `df.height` |
| **Cronometrar** | `cronometro()` | context manager que imprime o tempo de cada fase |

O passo de conferência é o que dá observabilidade barata ao pipeline: cada execução
deixa nos logs uma linha auditável.

```text
[OK] FATO_CTE_NOTA: extraído=111507 | snowflake=111507
FATO_CTE_NOTA: 111507 linhas
```

Um `[ERROR]` nessa linha significa divergência de contagem entre origem e destino — a
task **não** falha por isso, então vale procurar por ele ativamente (veja
[Runbook → Conferência de carga](runbook.md#conferencia-de-carga)).

---

## Do catálogo às DAGs

`catalogo.py` é um dicionário que mapeia o nome do ETL para a tupla
`(função, expressão cron)`:

```python
ETLS = {
    "dim_produto":   (dim_produto,   "0 6 * * *"),
    "fato_cte":      (fato_cte,      "0 6 * * *"),
    # ...
}
```

Ele termina com uma verificação que roda no *import*:

```python
for _nome, (_funcao, _schedule) in ETLS.items():
    assert callable(_funcao), f"{_nome} não é uma função! Confira o import em catalogo.py"
```

Isso existe porque o erro mais comum ao registrar um ETL novo é escrever
`from fatos import fato_cte` (importa o **módulo**) em vez de
`from fatos.fato_cte import executar as fato_cte` (importa a **função**). Sem o
`assert`, a falha só apareceria muito depois, como
`python_callable param must be callable` dentro do Airflow — e os logs deste projeto
mostram que isso já aconteceu dezenas de vezes.

`etl_siger_snowflake.py` percorre o catálogo e gera as DAGs dinamicamente:

```python
for nome, (funcao, schedule) in ETLS.items():
    with DAG(dag_id=f"etl_{nome}", schedule=schedule,
             start_date=datetime(2026, 8, 1), catchup=False) as dag:
        PythonOperator(task_id=nome, python_callable=funcao)
    globals()[f"etl_{nome}"] = dag
```

Duas sutilezas importantes:

- **`globals()[...] = dag`** é obrigatório. O Airflow descobre DAGs varrendo as
  variáveis de nível de módulo do arquivo; uma DAG criada dentro de um `for` e nunca
  atribuída a um nome global fica invisível para o scheduler.
- **`catchup=False`** evita que o Airflow dispare uma execução retroativa para cada dia
  desde `start_date`. Como a carga é *full refresh*, reprocessar o passado não teria
  sentido: o resultado seria idêntico ao de hoje.

O resultado são 9 DAGs independentes — `etl_dim_produto`, `etl_fato_cte`, … — cada uma
com uma única task. **Não há dependências entre elas**: as dimensões não bloqueiam os
fatos. Isso é viável aqui porque cada tabela é substituída inteira e o join entre fatos
e dimensões acontece na camada de consumo (BI), não na carga.

---

## Configuração por variáveis de ambiente

Nenhuma credencial aparece no código. `montar_uri()` monta uma URI a partir de um
**prefixo** e busca cinco variáveis com esse prefixo no ambiente:

```python
montar_uri("MYSQL", "mysql")
# lê MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DB
# → "mysql://user:senha@192.168.0.6:3306/02794s000"
```

Adicionar uma origem nova é, portanto, escrever uma função de três linhas em
`origens.py` e cinco variáveis no `.env` — sem tocar em mais nada.

O segundo parâmetro (`esquema`) é o **protocolo/driver** da URI (`mysql`,
`postgresql`), não o schema do banco. A docstring de `montar_uri()` chama atenção para
isso justamente porque a confusão é fácil.

As variáveis chegam ao processo por dois caminhos, dependendo de onde ele roda:

| Contexto | Como o `.env` é carregado |
|---|---|
| **Docker / Airflow** | `env_file: .env` no `docker-compose.yaml`, injetado no contêiner |
| **Local (`python main.py`)** | `load_dotenv()` no topo de `conexoes/__init__.py` |

O Snowflake é a exceção ao padrão de prefixo: `destinos.py` lê
`SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_WAREHOUSE`,
`SNOWFLAKE_DATABASE` e `SNOWFLAKE_SCHEMA` diretamente, porque a URI do Snowflake tem
formato próprio (`account` no lugar de `host:port`, `warehouse` como query string).

---

## Decisões de projeto

### Polars + connectorx + ADBC, sem Pandas no caminho

A extração usa `pl.read_database_uri()`, que delega ao **connectorx**: ele lê o
resultado da query e devolve buffers **Arrow** direto. A carga usa
`write_database(engine="adbc")`, que também fala Arrow com o Snowflake. O dado nunca é
materializado como objeto Python nem convertido para Pandas — o que importa quando
`FATO_ESTOQUE` traz mais de 2 milhões de linhas por execução.

`pandas` continua no `requirements.txt` porque
`snowflake-connector-python[pandas]` o exige como dependência transitiva, não porque o
pipeline o utilize.

### Full refresh, não incremental

Toda tabela é reescrita por inteiro (`if_table_exists="replace"`). É a escolha certa
para o volume atual: elimina a necessidade de chaves de merge, de controle de
*watermark* e de lógica de deduplicação, e torna cada execução idempotente — rodar duas
vezes seguidas dá o mesmo resultado.

O corte de `2024-09-01` nos fatos transacionais é o que mantém esse custo aceitável.

**Onde isso dói:** existe uma janela de alguns segundos, durante a carga, em que a
tabela está sendo substituída e uma consulta de BI pode pegá-la vazia ou parcial. Com
o agendamento às 06:00 UTC (03:00 no horário de Brasília), a janela cai fora do
horário de uso.

### Agregação empurrada para a origem

As queries de fato já chegam agregadas — `GROUP BY` e `SUM()` rodam no MySQL, não em
Python. `FATO_COMPRA`, por exemplo, agrega por empresa/período/produto/combinação na
própria origem. Isso reduz o volume trafegado e aproveita os índices do SIGER; o preço
é que o grão da tabela do DW fica fixado na query, e mudá-lo exige reprocessar tudo.

### Colunas normalizadas para maiúsculo na extração

Tanto `extrair_mysql()` quanto `extrair_postgres_senda()` fazem
`df.columns = [c.upper() for c in df.columns]`. O Snowflake trata identificadores não
citados como maiúsculos; normalizar na entrada evita colunas criadas com aspas e nomes
mistos que exigiriam *quoting* em toda consulta de BI.

---

## Infraestrutura

`docker-compose.yaml` define cinco serviços:

| Serviço | Papel | Porta |
|---|---|---|
| `postgres` | Metastore do Airflow (estado das DAGs, histórico) | — |
| `airflow-init` | Executa `db migrate` e cria o usuário `admin`; roda uma vez e sai | — |
| `airflow-webserver` | Interface web | **8080** |
| `airflow-scheduler` | Dispara as tasks conforme o cron | — |
| `docs` | Serve esta documentação (`mkdocs serve`); perfil `docs` | **8001** |

Os três serviços do Airflow compartilham a âncora YAML `x-airflow-common`, que define a
imagem construída pelo `Dockerfile` (`apache/airflow:2.10.4-python3.12` +
`requirements.txt`), o `env_file` e os volumes `./dags`, `./logs` e `./plugins`.

O serviço `docs` está atrás do *profile* `docs`, então não sobe com um
`docker compose up` comum — só com `docker compose --profile docs up docs`. Isso mantém
o ambiente de execução enxuto.

!!! note "Por que a porta 8001"
    O contêiner de docs expõe 8000 internamente, mas é mapeado para **8001** no host
    para não conflitar com outros serviços de desenvolvimento.
