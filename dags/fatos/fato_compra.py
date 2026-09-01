from conexoes import pipeline
query = (
    """
SELECT
  n.nped_emp                                          AS EMPRESA,
  DATE_FORMAT(n.nped_dte, '%Y%m') + 0                 AS PERIODO,
  ni.nipf_pro                                         AS PRODUTO,
  ni.nipf_cmb                                         AS COMBINACAO,
  ROUND(SUM(ni.nipf_qtd), 3)                          AS QTD,
  ROUND(SUM(ni.nipf_qtd * ni.nipf_vun), 2)            AS VALOR,
  COUNT(DISTINCT n.nped_cod)                          AS NOTAS,
  COUNT(DISTINCT n.nped_cli)                          AS CLIENTES
FROM 02794s000.npedid n
JOIN 02794s000.nipfat ni
  ON ni.nipf_emp = n.nped_emp AND ni.nipf_npo = n.nped_cod
WHERE n.nped_emp IN ({lista_sql(CONST_EMPRESAS)})
  AND n.nped_pos <> 9
  AND n.nped_ees IN (20,22,23,37,88)
  AND ni.nipf_pos <> 9
  AND ni.nipf_cfo IN (5101,5401,6101,6107,6109,6118,6151,7101,7127)
  AND n.nped_dte >= '2024-09-01'
GROUP BY 1, 2, 3, 4;
    """
)

def executar() -> int:
    return pipeline(query, "FATO_COMPRA")

if __name__ == "__main__":
    executar()
