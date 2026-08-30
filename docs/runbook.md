# Runbook

Guia operacional: subir o ambiente, rodar ETLs, ler os logs e resolver os erros que
já apareceram na prática.

## Pré-requisitos

- **Docker Desktop** rodando (com WSL2 habilitado, no Windows)
- **Python 3.12+** com venv local, para testar fora do Docker
- Acesso de rede ao **MySQL do SIGER**
- Usuário **Snowflake** com permissão de escrita no schema de destino

---

## Subir o ambiente

```powershell
# 1. Credenciais
Copy-Item .env.example .env
# preencha o .env — peça as credenciais ao time se não tiver

# 2. Pastas montadas pelos contêineres
mkdir logs, plugins

# 3. Metastore + usuário admin (roda uma vez e sai)
docker compose up airflow-init

# 4. Webserver + scheduler
docker compose up -d
```

Acesse `http://localhost:8080` — usuário `admin`, senha `admin`.

!!! danger "O `.env` nunca vai para o Git"
    Ele já está no `.gitignore`. Para confirmar:
    ```powershell
    git check-ignore -v .env
    ```
    Se o comando não devolver nada, **pare** e corrija o `.gitignore` antes de commitar.

### Variáveis de ambiente

| Variável | Para quê |
|---|---|
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB` | Origem SIGER — consumidas por `montar_uri("MYSQL", "mysql")` |
| `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD` | Autenticação no destino |
| `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA` | Onde gravar |

O `.env.example` lista todas. Ele **não** cobre ainda o prefixo `POSTGRESQL_*` exigido
por `extrair_postgres_senda()` — veja [Pendências](pendencias.md).

---

## Rodar um ETL

### Pelo Airflow (produção)

Todas as DAGs seguem o padrão `etl_<nome>` e rodam às **06:00 UTC** (03:00 BRT). Para
disparar fora do horário, use o botão *Trigger DAG* na interface, ou:

```powershell
docker compose exec airflow-scheduler airflow dags trigger etl_fato_cte
```

Comandos úteis:

```powershell
docker compose exec airflow-scheduler airflow dags list
docker compose exec airflow-scheduler airflow dags list-import-errors   # erro de sintaxe/import nas DAGs
docker compose exec airflow-scheduler airflow tasks test etl_fato_cte fato_cte 2026-08-30
```

`tasks test` executa a task **de verdade** (extrai e carrega no Snowflake), mas sem
registrar nada no metastore — é a forma mais rápida de validar uma query nova dentro do
contêiner.

### Localmente (teste rápido)

```powershell
python .\dags\main.py fato_compra    # um ETL específico
python .\dags\main.py                # todos, em sequência
python .\dags\main.py --help         # lista os nomes válidos
```

!!! failure "Não rode um arquivo aninhado direto"
    ```powershell
    python .\dags\fatos\fato_compra.py   # ModuleNotFoundError: No module named 'conexoes'
    ```
    O Python usa a pasta do próprio arquivo como raiz de import, e `conexoes/` só é
    visível a partir de `dags/`. Use sempre `main.py`.

---

## Ler os logs

Os logs ficam em `./logs/`, montados do contêiner, na estrutura do Airflow:

```text
logs/dag_id=etl_fato_cte/run_id=scheduled__2026-08-29T06:00:00+00:00/task_id=fato_cte/attempt=1.log
```

Para varrer todos de uma vez, o resumo de cada execução está em duas linhas:

```powershell
Select-String -Path logs\*\*\*\*.log -Pattern "\[OK\]|\[ERROR\]" | Select-Object -Last 20
```

```bash
grep -rh "\[OK\]\|\[ERROR\]" logs --include="*.log" | tail -20
```

### Conferência de carga

Toda execução bem-sucedida imprime:

```text
extração: 12.4s
carga: 8.1s
[OK] FATO_CTE_NOTA: extraído=111507 | snowflake=111507
FATO_CTE_NOTA: 111507 linhas
```

- **`extraído`** — linhas que saíram do SIGER (`df.height`)
- **`snowflake`** — `SELECT COUNT(*)` na tabela de destino após a carga
- **`[OK]`** se batem, **`[ERROR]`** se divergem

!!! warning "`[ERROR]` não faz a task falhar"
    `conferir_carga()` apenas imprime — a task termina como *success* mesmo com
    divergência. Um `[ERROR]` precisa ser encontrado ativamente nos logs.

    Divergência real observada neste projeto:
    ```text
    [ERROR] DIM_PRODUTO: extraído=257 | snowflake=135668
    ```
    Dois ETLs gravando na mesma tabela — o segundo conferiu contra o resultado do
    primeiro. Veja [Pendências](pendencias.md).

Volumes típicos, para comparação:

| Tabela | Linhas esperadas |
|---|---|
| `FATO_ESTOQUE` | 1.590.000 – 2.020.000 |
| `DIM_PRODUTO` | ~135.600 |
| `FATO_CTE_NOTA` | ~111.500 |
| `FATO_COMPRA` | ~48.900 |

Uma queda brusca em relação a esses números é sinal de filtro alterado, dado faltante
na origem ou carga interrompida.

---

## Problemas conhecidos

Todos os itens abaixo foram observados nos logs deste projeto.

### `Your user account has been temporarily locked` (Snowflake 390102)

O usuário do Snowflake foi bloqueado por tentativas de login malsucedidas repetidas —
tipicamente uma senha errada no `.env` somada a várias DAGs disparando juntas.

1. Corrija a senha no `.env`.
2. Espere ~15 minutos, ou peça ao administrador do Snowflake para desbloquear.
3. Reinicie os serviços para reler o `.env`:
   ```powershell
   docker compose restart airflow-scheduler airflow-webserver
   ```

Como os 9 ETLs rodam no mesmo horário, uma credencial errada gera 9 tentativas
simultâneas e o bloqueio chega rápido. Ao trocar a senha, valide com **um** ETL antes
de deixar o agendamento rodar.

### `The requested database does not exist or not authorized` (Snowflake 390201)

`SNOWFLAKE_DATABASE` ou `SNOWFLAKE_SCHEMA` está errado, ou o *role* padrão do usuário
não enxerga o objeto. Confirme conectando manualmente e rodando:

```sql
SHOW DATABASES;
SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE();
```

### `python_callable param must be callable`

Import errado em `catalogo.py`. Deve ser:

```python
from fatos.fato_cte import executar as fato_cte    # ✅ a função
from fatos import fato_cte                         # ❌ o módulo
```

O `assert` no fim de `catalogo.py` pega isso já no import da DAG, com o nome do ETL
culpado na mensagem.

### `ModuleNotFoundError: No module named 'conexoes'`

Você rodou um arquivo aninhado direto. Use `python .\dags\main.py <etl>`.

### `ModuleNotFoundError: No module named 'dags'`

Import escrito como `from dags.conexoes import ...`. Dentro do contêiner, `dags/` **é**
a raiz (`/opt/airflow/dags`), então o prefixo não existe. Use `from conexoes import ...`.

### `Error: query must be either str or a list of str`

A variável `query` do ETL não é uma string. A causa quase sempre é uma **vírgula sobrando**
depois do fechamento das aspas triplas, que transforma a string numa tupla de um
elemento:

```python
query = """
    SELECT ...
""",     # ← esta vírgula
```

### `NameError: name 'dim_municipio' is not defined`

Registrado em `catalogo.py` sem o `import` correspondente no topo do arquivo.

### `ModuleNotFoundError: No module named 'airflow.providers.standard'`

Import do estilo Airflow 3 num ambiente Airflow 2.10. O correto aqui é:

```python
from airflow.operators.python import PythonOperator
```

### `ModuleNotFoundError: No module named 'websockets'`

Dependência transitiva ausente na imagem. Acrescente ao `requirements.txt` e
reconstrua:

```powershell
docker compose build --no-cache
docker compose up -d
```

---

## Tarefas de manutenção

### Adicionar um ETL

1. Crie o arquivo em `dimensoes/` ou `fatos/`:

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

2. Registre em `catalogo.py`:

    ```python
    from fatos.novo_arquivo import executar as novo_etl

    ETLS = {
        # ...
        "novo_etl": (novo_etl, "0 6 * * *"),   # min hora dia mês dia-semana
    }
    ```

3. Teste local: `python .\dags\main.py novo_etl`
4. A DAG `etl_novo_etl` aparece sozinha no Airflow — a fábrica de DAGs a gera a partir
   do catálogo.

**Confira antes de commitar:** a `query` é uma string (sem vírgula sobrando)? O nome da
tabela é único entre todos os ETLs? O import traz a *função*, não o módulo?

### Adicionar uma origem

Em `conexoes/origens.py`:

```python
def extrair_novo_sistema(query: str) -> pl.DataFrame:
    df = pl.read_database_uri(query, uri=montar_uri("PREFIXO", "protocolo"))
    df.columns = [c.upper() for c in df.columns]
    return df
```

E no `.env`, cinco variáveis com o mesmo prefixo: `PREFIXO_USER`, `PREFIXO_PASSWORD`,
`PREFIXO_HOST`, `PREFIXO_PORT`, `PREFIXO_DB`.

Para usar a origem nova num ETL, passe-a a `pipeline()`:

```python
from conexoes import pipeline
from conexoes.origens import extrair_novo_sistema

def executar() -> int:
    return pipeline(query, "MINHA_TABELA", origem=extrair_novo_sistema)
```

### Mudar o horário de execução

Edite o cron do ETL em `catalogo.py`. O scheduler recarrega os arquivos sozinho em
poucos minutos; não precisa reiniciar nada.

### Alterar a data de corte ou a lista de empresas

Os filtros estão dentro de cada query SQL, não centralizados. Mudá-los exige editar
**cada arquivo** de ETL afetado:

```bash
grep -rl "2024-09-01" dags/
grep -rl "S01" dags/
```

---

## Servir esta documentação

```powershell
docker compose --profile docs up docs
```

Acesse `http://localhost:8001`. O `mkdocs serve` recarrega ao salvar qualquer arquivo
em `docs/`.

Sem Docker:

```powershell
pip install -r requirements-docs.txt
mkdocs serve
```
