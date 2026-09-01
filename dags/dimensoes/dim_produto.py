from conexoes import pipeline

query = (
    """
SELECT
  CAST(p.npro_cod AS SIGNED)                                  AS PRODUTO,
  NULLIF(UPPER(TRIM(SUBSTRING_INDEX(p.npro_ca1, '.', -1))), '') AS REFERENCIA,
  NULLIF(TRIM(p.npro_des), '')                                AS DESCRICAO,
  NULLIF(TRIM(p.npro_del), '')                                AS DESCRICAO_LONGA,
  NULLIF(TRIM(p.npro_uni), '')                                AS UNIDADE,
  NULLIF(CAST(p.npro_cma AS SIGNED), 0)                       AS MARCA_COD,
  NULLIF(TRIM(m.etbe_abr028), '')                             AS MARCA_SIGLA,
  NULLIF(TRIM(m.etbe_des028), '')                             AS MARCA_NOME,
  NULLIF(CAST(p.npro_grp AS SIGNED), 0)                       AS GRUPO_COD,
  NULLIF(TRIM(g.etbe_abr003), '')                             AS GRUPO_SIGLA,
  NULLIF(TRIM(g.etbe_des003), '')                             AS GRUPO_NOME,
  NULLIF(CAST(p.npro_sgr AS SIGNED), 0)                       AS SUBGRUPO_COD,
  NULLIF(CAST(p.npro_cop AS SIGNED), 0)                       AS COLECAO_COD,
  NULLIF(TRIM(c.etbe_abr025), '')                             AS COLECAO_SIGLA,
  NULLIF(TRIM(c.etbe_des025), '')                             AS COLECAO_NOME
FROM `02794s000`.nprodu p
LEFT JOIN `02794s000`.etbemp_mar m ON m.etbe_emp = p.npro_emp AND m.etbe_cmar = p.npro_cma
LEFT JOIN `02794s000`.etbemp_tpf g ON g.etbe_emp = p.npro_emp AND g.etbe_ctpf = p.npro_grp
LEFT JOIN `02794s000`.etbemp_cop c ON c.etbe_emp = p.npro_emp AND c.etbe_ccop = p.npro_cop
WHERE p.npro_emp = 'N03';
    """
)


def executar() -> int:
    return pipeline(query, "DIM_PRODUTO")


if __name__ == "__main__":
    executar()
