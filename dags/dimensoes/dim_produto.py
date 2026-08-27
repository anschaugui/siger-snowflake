from conexoes import pipeline


query = (
    """
SELECT
  p.npro_emp                                          AS EMPRESA,
  p.npro_cod                                          AS PRODUTO,
  UPPER(SUBSTRING_INDEX(p.npro_ca1, '.', -1))         AS REFERENCIA,
  p.npro_des                                          AS DESCRICAO,
  m.etbe_abr028                                       AS MARCA_SIGLA,
  m.etbe_des028                                       AS MARCA_NOME,
  g.etbe_abr003                                       AS GRUPO_SIGLA,
  g.etbe_des003                                       AS GRUPO_NOME
FROM nprodu p
LEFT JOIN etbemp_mar m ON m.etbe_emp = p.npro_emp AND m.etbe_cmar = p.npro_cma
LEFT JOIN etbemp_tpf g ON g.etbe_emp = p.npro_emp AND g.etbe_ctpf = p.npro_grp
WHERE p.npro_emp IN ('S01','S02','N03','N35');
    """
)

def executar() -> int:
    return pipeline(query, "DIM_PRODUTO")

if __name__ == "__main__":
    executar()
