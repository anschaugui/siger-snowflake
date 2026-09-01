from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from catalogo import ETLS

DEFAULT_ARGS = {
    "owner": "dados",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
    "depends_on_past": False,
}

for nome, (funcao, schedule) in ETLS.items():
    eh_fato = nome.startswith("fato")
    with DAG(
            dag_id=f"etl_{nome}",
            schedule=schedule,
            start_date=datetime(2026, 8, 1),
            catchup=False,
            # ⚠ uma execução por vez: um backfill longo não pode encavalar com o
            #   ciclo do dia seguinte e escrever a mesma tabela em paralelo
            max_active_runs=1,
            default_args=DEFAULT_ARGS,
            tags=["siger", "fato" if eh_fato else "dimensao"],
            doc_md=f"Carrega **{nome.upper()}** do SIGER para os destinos em `DW_DESTINOS`.",
    ) as dag:
        PythonOperator(task_id=nome, python_callable=funcao, pool="siger_mysql")

    globals()[f"etl_{nome}"] = dag