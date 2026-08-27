from conexoes import pipeline
query = """
    SELECT
      a.eacu_emp AS EMPRESA, a.eacu_per AS PERIODO, a.eacu_cod AS PRODUTO,
      a.eacu_loc AS LOCAL, a.eacu_cmb AS COMBINACAO,
      a.eacu_qfi AS SALDO_QTD, a.eacu_vto AS SALDO_VALOR,
      a.eacu_qet AS ENTRADA_QTD, a.eacu_vet AS ENTRADA_VALOR,
      a.eacu_qsa AS SAIDA_QTD, a.eacu_vsa AS SAIDA_VALOR,
      a.eacu_datult AS ULT_ALTERACAO
    FROM 02794s000.eacumu a
    WHERE a.eacu_emp IN ('S01','S02','N03','N35')
      AND a.eacu_per >= 202409
"""

def executar() -> int:
    return pipeline(query, "FATO_ESTOQUE")

if __name__ == "__main__":
    executar()
