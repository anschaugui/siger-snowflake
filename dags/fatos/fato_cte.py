from conexoes import pipeline
query = (
    """
SELECT
  c.LMVL_EMP                                          AS EMPRESA,
  c.LMVL_NOT                                          AS NUMERO,
  c.LMVL_SER                                          AS SERIE,
  c.LMVL_CCF                                          AS TRANSPORTADORA,
  c.LMVL_NOI                                          AS CFOP,
  c.LMVL_SNO                                          AS SEQ,
  MIN(c.LMVL_EMI)                                     AS DT_EMISSAO,
  MIN(c.LMVL_DTM)                                     AS DT_MOVIMENTO,
  c.LMVL_CMUR                                         AS MUN_ORIGEM,
  c.LMVL_CMUD                                         AS MUN_DESTINO,
  MAX(c.LMVL_MDF)                                     AS MODELO,
  ROUND(SUM(c.LMVL_VAL), 2)                           AS VALOR_FRETE,
  ROUND(SUM(c.LMVL_BICM), 2)                          AS BASE_ICMS,
  ROUND(SUM(c.LMVL_VICM), 2)                          AS VALOR_ICMS
FROM `02794s000`.lmvliv c
WHERE c.LMVL_NOI IN (1352,2352)          -- aquisição de serviço de transporte
  AND c.LMVL_EMI >= '2024-09-01'
GROUP BY 1,2,3,4,5,6,9,10;
    """
)

def executar() -> int:
    return pipeline(query, "FATO_CTE")

if __name__ == "__main__":
    executar()
