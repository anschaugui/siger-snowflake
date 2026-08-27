from dimensoes.dim_colaborador import executar as dim_colaborador
from dimensoes.dim_municipio import executar as dim_municipio
from dimensoes.dim_empresa import executar as dim_empresa
from dimensoes.dim_produto import executar as dim_produto
from dimensoes.dim_local_est import executar as dim_local_est
from fatos.fato_cte import executar as fato_cte
from fatos.fato_cte_nota import executar as fato_cte_nota
from fatos.fato_compra import executar as fato_compra
from fatos.fato_estoque import executar as fato_estoque

ETLS = {
    "dim_produto": (dim_produto, "0 6 * * *"),
    "dim_local": (dim_local_est, "0 6 * * *"),
    "dim_colaborador": (dim_colaborador, "0 6 * * *"),
    "dim_municipio": (dim_municipio, "0 6 * * *"),
    "dim_empresa": (dim_empresa, "0 6 * * *"),
    "fato_compra": (fato_compra, "0 6 * * *"),
    "fato_estoque": (fato_estoque, "0 6 * * *"),
    "fato_cte": (fato_cte, "0 6 * * *"),
    "fato_cte_nota": (fato_cte_nota, "0 6 * * *"),
}