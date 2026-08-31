from conexoes import pipeline, carregar_s3_parquet

query = (
"""
SELECT
  CAST(f.fcad_cod AS SIGNED)                          AS FORNECEDOR,
  TRIM(f.fcad_cgc)                                    AS CNPJ_CPF,
  CASE TRIM(f.fcad_tin) WHEN 'J' THEN 'JURIDICA'
                        WHEN 'F' THEN 'FISICA'
                        ELSE 'NAO INFORMADO' END      AS TIPO_PESSOA,
  NULLIF(TRIM(f.fcad_del), '')                        AS RAZAO_SOCIAL,
  NULLIF(TRIM(f.fcad_fan), '')                        AS NOME_FANTASIA,
  NULLIF(TRIM(f.fcad_ies), '')                        AS INSCRICAO_ESTADUAL,
  NULLIF(TRIM(f.fcad_log), '')                        AS LOGRADOURO,
  NULLIF(CAST(f.fcad_num AS SIGNED), 0)               AS NUMERO,
  NULLIF(TRIM(f.fcad_bai), '')                        AS BAIRRO,
  NULLIF(CAST(f.fcad_cep AS SIGNED), 0)               AS CEP,
  NULLIF(TRIM(f.fcad_cid), '')                        AS CIDADE,
  NULLIF(TRIM(f.fcad_est), '')                        AS UF,
  NULLIF(CAST(f.fcad_cmu AS SIGNED), 0)               AS COD_IBGE,
  CAST(f.fcad_sit AS SIGNED)                          AS SITUACAO_COD,
  f.fcad_dtca                                         AS DATA_CADASTRO,
  CASE WHEN t.cod IS NOT NULL THEN 1 ELSE 0 END       AS EH_TRANSPORTADORA,
  CASE WHEN TRIM(f.fcad_cgc) REGEXP '^[0-9]+$'
        AND LENGTH(TRIM(f.fcad_cgc)) IN (11, 14)
        AND TRIM(f.fcad_cgc) NOT IN ('00000000000000', '00000000000191',
                                     '00000000191', '11111111111111',
                                     '99999999999999')
       THEN 1 ELSE 0 END                              AS CNPJ_VALIDO
FROM `02794s000`.fcadas f
LEFT JOIN (SELECT DISTINCT LMVL_CCF AS cod
             FROM `02794s000`.lmvliv
            WHERE LMVL_NOI IN (1352, 2352)) t ON t.cod = f.fcad_cod
WHERE f.fcad_emp = 'N03'
  AND f.fcad_tip = 'F';
""")

def executar() -> int:
    return pipeline(query, "DIM_FORNECEDOR", arquivo_s3=carregar_s3_parquet)

if __name__ == '__main__':
    executar()