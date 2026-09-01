# DW Sugar & Neo

Data warehouse dimensional do Grupo Sugar/Neorubber. Extrai do **SIGER** (ERP
MySQL/MariaDB, schema `02794s000`) e grava em **S3** (consultável por Athena) e/ou
**Snowflake**, orquestrado por **Apache Airflow**.

O projeto é deliberadamente pequeno: cada ETL é um arquivo com uma query SQL e uma
função `executar()`. Toda a mecânica de conexão, extração, carga e conferência vive em
um único lugar — o pacote [`conexoes`](referencia/conexoes.md).

!!! tip "Novo por aqui? Comece pelos [Conceitos](conceitos.md)"
    Ele explica *por que* o modelo tem esta forma — grão, dimensão conformada, chave
    natural, partição — e lista os defeitos que este projeto já viu quebrar **sem
    levantar exceção**. É a leitura que evita repetir um erro caro.

---

## Em uma olhada

| | |
|---|---|
| **Origem** | MySQL/MariaDB — SIGER, schema `02794s000` |
| **Destinos** | S3 (`dw-sugarshoes-2026`, Parquet) e Snowflake (`SUGARSHOES.DW`) |
| **Quem escolhe o destino** | a variável `DW_DESTINOS` — **um lugar só** |
| **Extração** | Polars + connectorx (Arrow, sem passar por Pandas) |
| **Carga S3** | Parquet, partição Hive `coluna=valor/` |
| **Carga Snowflake** | ADBC (`DataFrame.write_database`), *full refresh* |
| **Catálogo/consulta** | AWS Glue Crawler → Athena (`dw_sugarshoes`, `sa-east-1`) |
| **Orquestração** | Airflow 2.10.4 (LocalExecutor + Postgres) via Docker Compose |
| **Agendamento** | `0 6 * * *` — todo dia às 06:00 UTC |

## Trocar o destino de tudo

Um ETL declara **o que** extrai; **onde** grava é configuração. Uma linha no `.env`
muda os ETLs todos:

```bash
DW_DESTINOS=s3                # só o data lake
DW_DESTINOS=snowflake         # só o Snowflake
DW_DESTINOS=s3,snowflake      # os dois (extrai uma vez, grava nos dois)
```

O porquê está em [Conceitos → destino é configuração](conceitos.md#destino-e-configuracao-nao-codigo).

## Os ETLs

**Dimensões** — `dim_produto`, `dim_local_est`, `dim_colaborador`, `dim_municipio`,
`dim_empresa`, `dim_cliente`, `dim_fornecedor`, `dim_formulacao`

**Fatos** — `fato_compra`, `fato_estoque`, `fato_cte`, `fato_cte_nota`

!!! note "Nem todos estão no catálogo"
    `dim_cliente`, `dim_fornecedor` e `dim_formulacao` existem e estão no formato
    novo, mas ainda **não foram registradas em `catalogo.py`** — então não rodam pelo
    Airflow nem pelo `main.py all`. Ver [Pendências](pendencias.md).

Grão, colunas e origem de cada tabela estão em [Modelo de dados](modelo-dados.md).

## Por onde começar

<div class="grid cards" markdown>

- **[Conceitos](conceitos.md)** — por que um DW, modelagem dimensional, grão,
  dimensão conformada, camadas do lake e as armadilhas que não dão erro.

- **[Arquitetura](arquitetura.md)** — como as peças se encaixam, o fluxo de uma
  execução e as decisões de projeto por trás delas.

- **[Modelo de dados](modelo-dados.md)** — o que cada tabela do DW contém, seu grão
  e as tabelas do SIGER que a alimentam.

- **[Data warehouse na AWS](aws.md)** — bucket, IAM, crawler, Athena e custo.

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
  de tabela no DW ficam em `MAIÚSCULO`.
- **A query mora no arquivo do ETL.** Não há camada de templates nem arquivos `.sql`
  soltos — abrir `fatos/fato_cte.py` mostra tudo o que aquele ETL faz.
- **O módulo não conhece o destino.** `pipeline(query, "DIM_CLIENTE")` e pronto. O
  único argumento extra aceito é `particao`, porque partição é propriedade do dado.
- **A coluna-chave tem o mesmo nome na dimensão e no fato.** `CLIENTE`, `PRODUTO`,
  `COD_IBGE` — assim o JOIN vira `USING (...)` e o SQL cobra a convenção.
- **O catálogo é a fonte da verdade.** Um ETL só existe de fato depois de registrado
  em `catalogo.py`; é de lá que o Airflow e a CLI leem.
