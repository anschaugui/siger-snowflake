from conexoes import pipeline
query = (
    """
SELECT
  m.Cod_IBGE_mun                                      AS COD_IBGE,
  m.Descricao                                         AS MUNICIPIO,
  CASE FLOOR(m.Cod_IBGE_mun / 100000)
    WHEN 11 THEN 'RO' WHEN 12 THEN 'AC' WHEN 13 THEN 'AM' WHEN 14 THEN 'RR'
    WHEN 15 THEN 'PA' WHEN 16 THEN 'AP' WHEN 17 THEN 'TO' WHEN 21 THEN 'MA'
    WHEN 22 THEN 'PI' WHEN 23 THEN 'CE' WHEN 24 THEN 'RN' WHEN 25 THEN 'PB'
    WHEN 26 THEN 'PE' WHEN 27 THEN 'AL' WHEN 28 THEN 'SE' WHEN 29 THEN 'BA'
    WHEN 31 THEN 'MG' WHEN 32 THEN 'ES' WHEN 33 THEN 'RJ' WHEN 35 THEN 'SP'
    WHEN 41 THEN 'PR' WHEN 42 THEN 'SC' WHEN 43 THEN 'RS' WHEN 50 THEN 'MS'
    WHEN 51 THEN 'MT' WHEN 52 THEN 'GO' WHEN 53 THEN 'DF'
  END                                                 AS UF
FROM `02794s000`.municipios_iprisma m;
    """
)

def executar() -> int:
    return pipeline(query, "DIM_MUNICIPIO")

if __name__ == "__main__":
    executar()
