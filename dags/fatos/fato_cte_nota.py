from conexoes import pipeline
query = (
    """
SELECT
  n.LOBL_EMP                                          AS EMPRESA,
  n.LOBL_NOT008                                       AS NUMERO,
  n.LOBL_SER008                                       AS SERIE,
  n.LOBL_CCF008                                       AS TRANSPORTADORA,
  n.LOBL_NOI008                                       AS CFOP,
  n.LOBL_NOC                                          AS NOTA,
  n.LOBL_SEC                                          AS NOTA_SERIE,
  n.LOBL_CDF                                          AS CLIENTE,
  MAX(n.LOBL_NOP)                                     AS CFOP_NOTA,
  CASE WHEN MAX(n.LOBL_NOP) >= 5000 THEN 'SAIDA' ELSE 'ENTRADA' END AS SENTIDO,
  -- devolução: últimos 3 dígitos do CFOP (compra/venda/ST)
  MAX(CASE WHEN MOD(n.LOBL_NOP,1000) IN (201,202,203,204,410,411) THEN 1 ELSE 0 END) AS EH_DEVOLUCAO,
  MIN(n.LOBL_DTC)                                     AS DT_NOTA,
  ROUND(SUM(n.LOBL_VAC), 2)                           AS VALOR_NOTA
FROM `02794s000`.lobliv_nfc n
WHERE n.LOBL_NOI008 IN (1352,2352)
  AND n.LOBL_DTC >= '2024-09-01'
GROUP BY 1,2,3,4,5,6,7,8;
    """
)

def executar() -> int:
    return pipeline(query, "FATO_CTE_NOTA")

if __name__ == "__main__":
    executar()
