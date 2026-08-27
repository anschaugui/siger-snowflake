from conexoes import pipeline
query = (
    """
SELECT LMVL_EMP AS EMPRESA, COUNT(*) AS CT_ES
FROM `02794s000`.lmvliv
WHERE LMVL_NOI IN (1352,2352) AND LMVL_EMI >= '2024-09-01'
GROUP BY 1;
    """
)

def executar() -> int:
    return pipeline(query, "DIM_EMPRESA")

if __name__ == "__main__":
    executar()
