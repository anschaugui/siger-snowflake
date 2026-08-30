# Conexões

O pacote `conexoes` concentra toda a mecânica de I/O do projeto. É a única camada que
conhece credenciais, drivers e protocolos — os ETLs apenas o consomem.

```text
conexoes/
├── __init__.py   → pipeline(), cronometro(), conferir_carga()
├── util.py       → montar_uri()
├── origens.py    → extrair_mysql(), extrair_postgres_senda()
└── destinos.py   → conectar_snowflake(), carregar_snowflake()
```

O `__init__.py` executa `load_dotenv()` no import, de modo que qualquer módulo que faça
`from conexoes import pipeline` já encontra as variáveis do `.env` carregadas. Ele
também reexporta as funções de origem e destino, então `from conexoes import
extrair_mysql` funciona.

---

## Orquestração — `conexoes`

::: conexoes
    options:
      members:
        - pipeline
        - conferir_carga
        - cronometro
      show_root_heading: false
      show_root_toc_entry: false

### `pipeline()` em detalhe

É a função que todo ETL chama. Recebe a query e o nome da tabela, e executa as quatro
etapas em ordem:

```python
def pipeline(query, tabela, origem=extrair_mysql, destino=carregar_snowflake) -> int:
    with cronometro("extração"):
        df = origem(query)
    with cronometro("carga"):
        nrows = destino(df, tabela)
    conferir_carga(df, tabela)
    print(f"{tabela}: {nrows} linhas")
    return nrows
```

| Parâmetro | Padrão | Papel |
|---|---|---|
| `query` | — | SQL a executar na origem |
| `tabela` | — | Nome da tabela de destino no Snowflake (em maiúsculo) |
| `origem` | `extrair_mysql` | Função `(query) -> pl.DataFrame` |
| `destino` | `carregar_snowflake` | Função `(df, tabela) -> int` |

`origem` e `destino` são injetáveis: trocar a fonte de um ETL não exige mexer em nada
além da chamada.

```python
from conexoes import pipeline
from conexoes.origens import extrair_postgres_senda

pipeline(query, "FATO_X", origem=extrair_postgres_senda)
```

As linhas `origem = origem or extrair_mysql` no corpo tornam `pipeline(query, tab,
origem=None)` equivalente ao padrão, útil quando o valor vem de configuração.

### Saída no log

```text
extração: 12.4s
carga: 8.1s
[OK] FATO_CTE: extraído=42130 | snowflake=42130
FATO_CTE: 42130 linhas
```

`conferir_carga()` compara `df.height` com um `SELECT COUNT(*)` no destino e imprime
`[OK]` ou `[ERROR]`. **A divergência não levanta exceção** — a task do Airflow termina
como sucesso mesmo assim. Veja
[Runbook → Conferência de carga](../runbook.md#conferencia-de-carga).

---

## Utilidades — `conexoes.util`

::: conexoes.util
    options:
      show_root_heading: false
      show_root_toc_entry: false

---

## Origens — `conexoes.origens`

::: conexoes.origens
    options:
      show_root_heading: false
      show_root_toc_entry: false

Ambas as funções seguem o mesmo contrato — recebem uma query, devolvem um
`pl.DataFrame` com os nomes de coluna em **maiúsculo**. A normalização evita
identificadores citados no Snowflake, que exigiriam aspas em toda consulta de BI.

`extrair_mysql()` é a origem padrão de `pipeline()` e alimenta os 9 ETLs em produção.

!!! warning "`extrair_postgres_senda()` não está em uso"
    A função existe, mas nenhum ETL do catálogo a utiliza, e sua chamada
    `montar_uri("POSTGRESQL", "DW")` passa `"DW"` na posição do **protocolo** da URI —
    onde deveria vir `postgresql`. Veja [Pendências](../pendencias.md).

---

## Destinos — `conexoes.destinos`

::: conexoes.destinos
    options:
      show_root_heading: false
      show_root_toc_entry: false

As duas funções abrem conexões por caminhos diferentes, de propósito:

| Função | Driver | Usada para |
|---|---|---|
| `conectar_snowflake()` | `snowflake-connector-python` | Consultas de controle — hoje só o `COUNT(*)` de `conferir_carga()` |
| `carregar_snowflake()` | **ADBC**, via `df.write_database()` | Escrita em massa, direto de Arrow |

O caminho ADBC é o que evita converter o DataFrame para Pandas ou para objetos Python
antes de gravar — decisivo em `FATO_ESTOQUE`, com mais de 2 milhões de linhas.

!!! danger "`if_table_exists=\"replace\"`"
    `carregar_snowflake()` **substitui a tabela inteira** a cada execução. É o que torna
    o pipeline idempotente, mas também significa que:

    - A estrutura da tabela é recriada conforme o DataFrame — *grants*, comentários e
      *clustering keys* aplicados manualmente no Snowflake se perdem.
    - Há uma janela curta, durante a carga, em que consultas de BI podem ler a tabela
      vazia ou parcial.
