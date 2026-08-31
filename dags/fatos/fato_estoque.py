from datetime import date
from conexoes import pipeline
from conexoes import destinos
from constantes import CONST_EMPRESAS

def _periodo_janela(n_meses: int = 2) -> list[int]:
    hoje = date.today()
    periodos = []
    anos, mes = hoje.year, hoje.month
    for _ in range(n_meses):
        periodos.append(anos * 100 + mes)
        mes -= 1
        if mes == 0:
            mes, anos = 12, anos - 1
    return periodos

def executar(n_meses: int | None = 2) -> int:
    filtro_periodo = ""
    if n_meses is not None:
        periodos = _periodo_janela(n_meses)
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
        WHERE a.eacu_emp IN ({",".join(f"'{e}'" for e in CONST_EMPRESAS)})
          {filtro_periodo}
    """
    return pipeline(query, "FATO_ESTOQUE",
                    destino=None,
                    arquivo_s3=lambda df, tabela: destinos.carregar_s3_particionado(df, tabela, "PERIODO"))

if __name__ == "__main__":
    executar()