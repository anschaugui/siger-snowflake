# DIM_CLIENTE — uma linha por cliente do Siger.
#
# GRÃO: fcad_cod. SEM empresa.
#
# ⚠ O CADASTRO É REPLICADO POR EMPRESA e o conteúdo é IDÊNTICO. Medido em
#   31/08/2026 nas quatro empresas (S01, S02, N03, N35): 79.309 clientes em
#   cada uma, mesmo conjunto de códigos, e ZERO divergência em CNPJ, razão
#   social, cidade, representante e situação. Carregar as quatro daria 317.236
#   linhas para descrever 79.309 clientes, e obrigaria todo JOIN de fato a
#   casar por empresa também — sob pena de multiplicar os valores por 4.
#   Por isso lê só N03, a mesma master já usada em DIM_PRODUTO.
#
# ⚠ O REPRESENTANTE NÃO ESTÁ AQUI. fcad_rep tem 2 valores distintos em 79 mil
#   cadastros — o campo não é usado. O vínculo cliente↔representante vem da
#   geografia e do pedido, não do cadastro.
#
# ⚠ TRIM EM TUDO QUE ENTRA EM CHAVE OU JOIN. fcad_est é CHAR(2) e fcad_emp é
#   CHAR(3): no Parquet isso vira string com espaço à direita, e no Athena o
#   JOIN simplesmente NÃO CASA — sem erro, a linha some.

from conexoes import pipeline

query = (
    """
SELECT
  CAST(c.fcad_cod AS SIGNED)                          AS CLIENTE,
  TRIM(c.fcad_cgc)                                    AS CNPJ_CPF,
  CASE TRIM(c.fcad_tin) WHEN 'J' THEN 'JURIDICA'
                        WHEN 'F' THEN 'FISICA'
                        ELSE 'NAO INFORMADO' END      AS TIPO_PESSOA,
  NULLIF(TRIM(c.fcad_del), '')                        AS RAZAO_SOCIAL,
  NULLIF(TRIM(c.fcad_fan), '')                        AS NOME_FANTASIA,
  NULLIF(TRIM(c.fcad_ies), '')                        AS INSCRICAO_ESTADUAL,
  NULLIF(TRIM(c.fcad_log), '')                        AS LOGRADOURO,
  NULLIF(CAST(c.fcad_num AS SIGNED), 0)               AS NUMERO,
  NULLIF(TRIM(c.fcad_bai), '')                        AS BAIRRO,
  NULLIF(CAST(c.fcad_cep AS SIGNED), 0)               AS CEP,
  NULLIF(TRIM(c.fcad_cid), '')                        AS CIDADE,
  NULLIF(TRIM(c.fcad_est), '')                        AS UF,
  NULLIF(CAST(c.fcad_cmu AS SIGNED), 0)               AS COD_IBGE,
  NULLIF(CAST(c.fcad_rlj AS SIGNED), 0)               AS REDE_LOJA,
  NULLIF(TRIM(r.ftab_des096), '')                     AS REDE_LOJA_NOME,
  CAST(c.fcad_sit AS SIGNED)                          AS SITUACAO_COD,
  c.fcad_dtca                                         AS DATA_CADASTRO,
  CASE WHEN TRIM(c.fcad_cgc) REGEXP '^[0-9]+$'
        AND LENGTH(TRIM(c.fcad_cgc)) IN (11, 14)
        AND TRIM(c.fcad_cgc) NOT IN ('00000000000000', '00000000000191',
                                     '00000000191', '11111111111111',
                                     '99999999999999')
       THEN 1 ELSE 0 END                              AS CNPJ_VALIDO
FROM `02794s000`.fcadas c
LEFT JOIN `02794s000`.ftabel_rlj r ON r.ftab_crlj = c.fcad_rlj
WHERE c.fcad_emp = 'N03'
  AND c.fcad_tip = 'C';
    """
)


def executar() -> int:
    return pipeline(query, "DIM_CLIENTE")


if __name__ == "__main__":
    executar()
