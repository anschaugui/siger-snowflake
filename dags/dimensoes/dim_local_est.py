from conexoes import pipeline

query = """
                SELECT
                  l.etbe_emp                                          AS EMPRESA,
                  l.etbe_cloc                                         AS LOCAL,     -- ⚠ etbe_cloc, não etbe_loc
                  l.etbe_des001                                       AS DESCRICAO,
                  CASE WHEN l.etbe_cloc = 1 THEN 1 ELSE 0 END         AS NAO_USAR
                FROM 02794s000.etbemp_loc l
                WHERE l.etbe_emp IN ('S01','S02','N03','N35');
        """,

def executar() -> int:
    return pipeline(query, "DIM_PRODUTO")
if __name__ == "__main__":
    executar()