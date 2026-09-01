from dimensoes.dim_colaborador import executar as dim_colaborador
from dimensoes.dim_municipio import executar as dim_municipio
from dimensoes.dim_empresa import executar as dim_empresa
from dimensoes.dim_produto import executar as dim_produto
from dimensoes.dim_local_est import executar as dim_local_est
from fatos.fato_cte import executar as fato_cte
from fatos.fato_cte_nota import executar as fato_cte_nota
from fatos.fato_compra import executar as fato_compra
from fatos.fato_estoque import executar as fato_estoque

# ⚠ OS HORÁRIOS SÃO ESCALONADOS DE PROPÓSITO. Todos os ETLs rodavam às 06:00 e
#   disparavam 9 extrações concorrentes contra o MySQL do ERP — que é um banco de
#   PRODUÇÃO, contratado, disputando CPU com quem está faturando nota.
#
#   As dimensões vêm primeiro (são leves e rápidas) e os fatos depois, com folga
#   entre eles. Isso NÃO cria dependência entre as DAGs — cada uma continua
#   independente; é só um espaçamento para não empilhar carga na origem.
#
# ⚠ O teto de concorrência real é a pool `siger_mysql` (ver fabrica_dags.py).
#   O escalonamento aqui é a primeira linha de defesa; a pool é a que segura.
ETLS = {
    # dimensões — 06:00 a 06:40
    "dim_empresa":     (dim_empresa,     "0 6 * * *"),
    "dim_local":       (dim_local_est,   "10 6 * * *"),
    "dim_municipio":   (dim_municipio,   "20 6 * * *"),
    "dim_colaborador": (dim_colaborador, "30 6 * * *"),
    "dim_produto":     (dim_produto,     "40 6 * * *"),
    # fatos — 07:00 em diante, depois das dimensões
    "fato_compra":     (fato_compra,     "0 7 * * *"),
    "fato_cte":        (fato_cte,        "20 7 * * *"),
    "fato_cte_nota":   (fato_cte_nota,   "40 7 * * *"),
    "fato_estoque":    (fato_estoque,    "0 8 * * *"),
}

for _nome, (_funcao, _schedule) in ETLS.items():
    assert callable(_funcao), f"{_nome} não é uma função! Confira o import em catalogo.py"