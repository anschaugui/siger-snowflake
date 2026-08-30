# Orquestração

Três arquivos na raiz de `dags/` decidem *quais* ETLs existem e *como* são disparados.

---

## `catalogo.py` — o registro central

Um dicionário mapeando nome do ETL para `(função, expressão cron)`:

```python
ETLS = {
    "dim_produto":     (dim_produto,     "0 6 * * *"),
    "dim_local":       (dim_local_est,   "0 6 * * *"),
    "dim_colaborador": (dim_colaborador, "0 6 * * *"),
    "dim_municipio":   (dim_municipio,   "0 6 * * *"),
    "dim_empresa":     (dim_empresa,     "0 6 * * *"),
    "fato_compra":     (fato_compra,     "0 6 * * *"),
    "fato_estoque":    (fato_estoque,    "0 6 * * *"),
    "fato_cte":        (fato_cte,        "0 6 * * *"),
    "fato_cte_nota":   (fato_cte_nota,   "0 6 * * *"),
}
```

É a **única** fonte da verdade do projeto: o Airflow e a CLI leem daqui, e um ETL só
passa a existir de fato depois de registrado.

A chave do dicionário vira o `dag_id` (prefixado com `etl_`) e o `task_id`. Repare que
`dim_local_est` é registrado como `"dim_local"` — a DAG resultante é `etl_dim_local`.

### A verificação no import

```python
for _nome, (_funcao, _schedule) in ETLS.items():
    assert callable(_funcao), f"{_nome} não é uma função! Confira o import em catalogo.py"
```

Existe para pegar cedo o erro mais comum ao registrar um ETL:

```python
from fatos.fato_cte import executar as fato_cte    # ✅ importa a função
from fatos import fato_cte                         # ❌ importa o módulo
```

Sem o `assert`, a segunda forma só falharia dentro do Airflow, como
`python_callable param must be callable` — erro que aparece 20 vezes nos logs deste
projeto. Com ele, a falha acontece no *parse* da DAG e a mensagem já diz qual ETL está
errado.

---

## `etl_siger_snowflake.py` — a fábrica de DAGs

```python
for nome, (funcao, schedule) in ETLS.items():
    with DAG(
        dag_id=f"etl_{nome}",
        schedule=schedule,
        start_date=datetime(2026, 8, 1),
        catchup=False,
    ) as dag:
        PythonOperator(task_id=nome, python_callable=funcao)
    globals()[f"etl_{nome}"] = dag
```

Um único arquivo gera as 9 DAGs — cada uma com uma task só. Adicionar um ETL ao
catálogo faz a DAG correspondente aparecer sozinha, sem escrever nada aqui.

**`globals()[f"etl_{nome}"] = dag`** não é opcional. O Airflow descobre DAGs varrendo
as variáveis de nível de módulo do arquivo; uma DAG construída dentro de um `for` e
nunca atribuída a um nome global fica invisível para o scheduler.

**`catchup=False`** impede que o Airflow dispare uma execução retroativa por dia desde
`start_date`. Como a carga é *full refresh*, reprocessar o passado produziria
exatamente o mesmo resultado de hoje.

**Sem dependências entre DAGs** — as dimensões não bloqueiam os fatos. Cada tabela é
substituída inteira e o join acontece na camada de BI, então a ordem não importa para a
consistência do carregamento.

---

## `main.py` — a CLI local

::: main
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [main]

Uso pretendido:

```powershell
python .\dags\main.py fato_compra    # um ETL
python .\dags\main.py                # todos, em sequência (padrão "all")
python .\dags\main.py --help         # nomes válidos, vindos do catálogo
```

O `argparse` deriva os `choices` de `list(ETLS) + ["all"]`, então a lista de nomes
aceitos acompanha o catálogo automaticamente.

!!! bug "A CLI está quebrada hoje"
    `main.py` chama `funcao()` sobre o **valor** do dicionário, que é a tupla
    `(função, cron)` — resultando em `TypeError: 'tuple' object is not callable`.
    Detalhes em [Pendências → item 1](../pendencias.md). O caminho pelo Airflow, que
    desempacota a tupla, não é afetado.

!!! failure "Rode sempre por `main.py`, nunca o arquivo aninhado"
    ```powershell
    python .\dags\fatos\fato_compra.py   # ModuleNotFoundError: No module named 'conexoes'
    ```
    O Python usa a pasta do próprio arquivo como raiz de import, e `conexoes/` só é
    visível a partir de `dags/`.
