from conexoes import pipeline
from constantes import CONST_EMPRESAS

query = f"""
    SELECT
      l.etbe_emp                                          AS EMPRESA,
      l.etbe_cloc                                         AS LOCAL,
      l.etbe_des001                                       AS DESCRICAO,
      CASE WHEN l.etbe_cloc = 1 THEN 1 ELSE 0 END         AS NAO_USAR
    FROM 02794s000.etbemp_loc l
    WHERE l.etbe_emp IN ({",".join(f"'{e}'" for e in CONST_EMPRESAS)})
"""

def executar() -> int:
    return pipeline(query, "DIM_LOCAL_EST")

if __name__ == "__main__":
    executar()