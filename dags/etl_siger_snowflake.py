from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from catalogo import ETLS

for nome, (funcao, schedule) in ETLS.items():
    with DAG(
        dag_id=f"etl_{nome}",
        schedule=schedule,
        start_date=datetime(2026, 8, 1),
        catchup=False,
    ) as dag:
        PythonOperator(task_id=nome, python_callable=funcao)
    globals()[f"etl_{nome}"] = dag