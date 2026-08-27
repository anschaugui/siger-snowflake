from dimensoes.dim_produto import executar as dim_produto
from dimensoes.dim_local_est import executar as dim_local_est
from fatos.fato_compra import executar as fato_compra
from fatos.fato_estoque import executar as fato_estoque

ETLS = {
    "dim_produto": (dim_produto, "0 6 * * *"),
    "dim_local": (dim_local_est, "0 6 * * *"),
    "fato_compra": (fato_compra, "0 6 * * *"),
    "fato_estoque": (fato_estoque, "0 6 * * *"),
}