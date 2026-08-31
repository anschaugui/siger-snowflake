from conexoes import pipeline, carregar_s3_parquet

query = (
    """
SELECT
  CAST(f.efor_idf AS SIGNED)                          AS FORMULACAO,
  CAST(f.efor_cod AS SIGNED)                          AS PRODUTO,
  CAST(f.efor_cmb AS SIGNED)                          AS COMBINACAO,
  CAST(f.efor_rev AS SIGNED)                          AS REVISAO,
  CASE WHEN f.efor_rev = u.rev_max THEN 1 ELSE 0 END  AS REVISAO_ATUAL,
  NULLIF(UPPER(TRIM(f.efor_ref)), '')                 AS REFERENCIA,
  NULLIF(TRIM(f.efor_abr), '')                        AS ABREVIACAO,
  NULLIF(TRIM(f.efor_des), '')                        AS DESCRICAO,
  NULLIF(TRIM(f.efor_del), '')                        AS DESCRICAO_LONGA,
  CAST(f.efor_sit AS SIGNED)                          AS SITUACAO_COD,
  f.efor_dtc                                          AS DATA_CADASTRO,
  f.efor_dtr                                          AS DATA_REVISAO,
  NULLIF(f.efor_pes, 0)                               AS PESO,
  NULLIF(f.efor_prd, 0)                               AS PRODUTIVIDADE
FROM `02794s000`.eformu f
JOIN (SELECT efor_cod, efor_cmb, MAX(efor_rev) AS rev_max
        FROM `02794s000`.eformu
       WHERE efor_emp = 'N03'
       GROUP BY 1, 2) u
  ON  u.efor_cod = f.efor_cod
  AND u.efor_cmb = f.efor_cmb
WHERE f.efor_emp = 'N03';
    """
)


def executar() -> int:
    return pipeline(query, "DIM_FORMULACAO", arquivo_s3=carregar_s3_parquet)


if __name__ == "__main__":
    executar()