# ETL SIGER → Snowflake

Pipeline de extração e carga que leva dados do **SIGER** (ERP MySQL/MariaDB do Grupo
Sugar/Neorubber, schema `02794s000`) para o **Snowflake** (`SUGARSHOES.DW`), orquestrado
por **Apache Airflow**.

O projeto é deliberadamente pequeno: cada ETL é um arquivo com uma query SQL e uma
função `executar()`. Toda a mecânica de conexão, extração, carga e conferência vive em
um único lugar — o pacote [`conexoes`](referencia/conexoes.md).

---

## Em uma olhada

| | |
|---|---|
| **Origem** | MySQL/MariaDB — SIGER, schema `02794s000` |
| **Destino** | Snowflake — `SUGARSHOES.DW` |
| **Estratégia de carga** | *Full refresh* (`if_table_exists="replace"`) |
| **Extração** | Polars + connectorx (Arrow, sem passar por Pandas) |
| **Carga** | ADBC (`DataFrame.write_database`) |
| **Orquestração** | Airflow 2.10.4 (LocalExecutor + Postgres) via Docker Compose |
| **Agendamento** | `0 6 * * *` — todo dia às 06:00 UTC, para os 9 ETLs |
| **Janela de dados** | Fatos transacionais a partir de `2024-09-01` |

## Os 9 ETLs

**Dimensões** — `dim_produto`, `dim_local`, `dim_colaborador`, `dim_municipio`,
`dim_empresa`

**Fatos** — `fato_compra`, `fato_estoque`, `fato_cte`, `fato_cte_nota`

Grão, colunas e origem de cada tabela estão em [Modelo de dados](modelo-dados.md).

## Por onde começar

<div class="grid cards" markdown>

- **[Arquitetura](arquitetura.md)** — como as peças se encaixam, o fluxo de uma
  execução e as decisões de projeto por trás delas.

- **[Modelo de dados](modelo-dados.md)** — o que cada tabela do DW contém, seu grão
  e as tabelas do SIGER que a alimentam.

- **[Runbook](runbook.md)** — subir o ambiente, rodar um ETL na mão, ler os logs e
  resolver os erros que já apareceram em produção.

- **[Referência](referencia/conexoes.md)** — a API dos módulos, gerada a partir do
  código-fonte.

</div>

## Setup em 5 comandos

```powershell
Copy-Item .env.example .env     # 1. preencha as credenciais
mkdir logs, plugins             # 2. pastas que o Airflow monta
docker compose up airflow-init  # 3. cria o metastore e o usuário admin
docker compose up -d            # 4. sobe webserver + scheduler
start http://localhost:8080     # 5. login: admin / admin
```

Detalhes, pré-requisitos e o passo a passo comentado estão no [Runbook](runbook.md).

## Convenções do projeto

- **Nomes em português.** Módulos, funções e variáveis seguem o vocabulário do
  negócio (`origens`, `destinos`, `executar`, `conferir_carga`). Aliases SQL e nomes
  de tabela no Snowflake ficam em `MAIÚSCULO`.
- **A query mora no arquivo do ETL.** Não há camada de templates nem arquivos `.sql`
  soltos — abrir `fatos/fato_cte.py` mostra tudo o que aquele ETL faz.
- **O catálogo é a fonte da verdade.** Um ETL só existe de fato depois de registrado
  em `catalogo.py`; é de lá que o Airflow e a CLI leem.
