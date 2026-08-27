from conexoes import pipeline
query = (
    """
SELECT
  v.Cod_colaborador                                   AS COLABORADOR,
  v.Razao_soc_longa                                   AS RAZAO_SOCIAL,
  v.Nome_fantasia                                     AS NOME_FANTASIA,
  v.CNPJ_CPF                                          AS CNPJ_CPF,
  v.Cidade                                            AS CIDADE,
  v.UF                                                AS UF,
  MAX(t.eh_transp)                                    AS EH_TRANSPORTADORA
FROM `02794s000`.view_cliente_fornecedor_iprisma v
JOIN (
  SELECT DISTINCT LMVL_CCF AS cod, 1 AS eh_transp
    FROM `02794s000`.lmvliv
   WHERE LMVL_NOI IN (1352,2352) AND LMVL_EMI >= '2024-09-01'
  UNION
  SELECT DISTINCT LOBL_CDF AS cod, 0 AS eh_transp
    FROM `02794s000`.lobliv_nfc
   WHERE LOBL_DTC >= '2024-09-01'
) t ON t.cod = v.Cod_colaborador
GROUP BY 1,2,3,4,5,6;

    """
)

def executar() -> int:
    return pipeline(query, "DIM_COLABORADOR")

if __name__ == "__main__":
    executar()
