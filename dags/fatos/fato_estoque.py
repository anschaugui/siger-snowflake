from conexoes import pipeline, por_periodo
from conexoes.util import lista_sql, periodo_janela
from constantes import CONST_EMPRESAS

def executar(n_meses: int | None = 100) -> int:
    filtro_periodo = ""
    if n_meses is not None:
        periodos = periodo_janela(n_meses)
        filtro_periodo = f"AND a.eacu_per IN ({','.join(str(p) for p in periodos)})"
    query = f"""
        SELECT  
          a.eacu_emp AS EMPRESA, a.eacu_per AS PERIODO, a.eacu_cod AS PRODUTO,
          a.eacu_loc AS LOCAL, a.eacu_cmb AS COMBINACAO,
          a.eacu_qfi AS SALDO_QTD, a.eacu_vto AS SALDO_VALOR,
          a.eacu_qet AS ENTRADA_QTD, a.eacu_vet AS ENTRADA_VALOR,
          a.eacu_qsa AS SAIDA_QTD, a.eacu_vsa AS SAIDA_VALOR,
          a.eacu_datult AS ULT_ALTERACAO
        FROM 02794s000.eacumu a
        WHERE a.eacu_emp IN ({lista_sql(CONST_EMPRESAS)})
          {filtro_periodo}
    """
    return pipeline(query, "FATO_ESTOQUE", destino=None, arquivo_s3=por_periodo)

if __name__ == "__main__":
    executar()