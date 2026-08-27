/* ============================================================================
   FRETE / CT-e  —  pacote dimensional para estudo no Snowflake
   Gerado em 2026-08-27 · fonte: MariaDB `02794s000` (base CRUA do Siger)

   Mesma estrutura do compras-x-estoque.sql:
     PARTE 0  roda no SNOWFLAKE   — cria as tabelas
     PARTE 1  roda no MARIADB     — extrai; exporte CSV/Parquet e carregue
     PARTE 2  roda no SNOWFLAKE   — as análises

   ⚠ A FONTE É A BASE CRUA, NÃO A `devops.bi_cte`.
     A `bi_cte` é um recorte parcial: só N03/N35 e só até jul/2025. A base crua
     tem TODAS as empresas e dados até hoje. Medido: em 2026 quem mais gasta
     frete é N35 (R$ 5,07 mi) e S02 (R$ 5,04 mi) — nenhuma das duas estaria
     completa no recorte antigo.

   O MODELO É CT-e-CÊNTRICO: parte-se do conhecimento e buscam-se as notas dele.
   Nota sem CT-e não entra em lugar nenhum (nem no numerador nem no denominador
   do % de frete) — de propósito.

   MEDIDO ANTES DE ESCREVER (2026-08-27)
     · CFOP 1352/2352 = 99,7% de todo o serviço de transporte
     · `LMVL_SNO` é SEMPRE 1 — 0 CT-e com mais de um, em 98.264 conferidos
     · `lmvliv` tem exatamente 1 LINHA por CT-e (98.264 de 98.264)
     · `LMVL_VAL` = `LMVL_VTOTNF` em 100% dos casos (R$ 38.716.132 nos dois)
     · linha de base 24 meses: 93.284 CT-e com nota · R$ 36.720.794 de frete
       sobre R$ 879.998.862 de carga = 4,17%
     · 4.980 CT-e (5%) não têm NENHUMA nota vinculada
     · 163 transportadoras distintas, de 92.479 colaboradores cadastrados

   ⚠ QUATRO ARMADILHAS TRATADAS AQUI

   (1) NÃO EXISTE PESO NEM VOLUME. `LOBL_PEB`, `LOBL_PEL` e `LOBL_QTV` estão
       ZERADOS em 100% das 120.104 linhas conferidas. R$/kg é a métrica natural
       de frete e ela NÃO é calculável nesta base — por isso não está no modelo.
       Não a reintroduza sem antes conferir que os campos passaram a ter dado.

   (2) NÃO EXISTE VALOR DE FRETE SEPARADO NO CT-e. `LMVL_VFR` (frete) e
       `LMVL_SEG` (seguro) estão zerados. O dinheiro é `LMVL_VAL`.

   (3) NUNCA USE SUBCONSULTA CORRELATA PARA SOMAR AS NOTAS. A versão com
       `(SELECT SUM(LOBL_VAC) ... WHERE x.LOBL_EMP=c.LMVL_EMP ...)` passou de
       10 MINUTOS sem terminar. O mesmo cálculo com JOIN agregado leva 1,4 s.
       A PARTE 1 usa JOIN agregado.

   (4) % DE FRETE ALTO QUASE NUNCA É FRETE CARO. É vínculo incompleto — falta
       nota no CT-e, então o denominador fica pequeno e o % explode (já houve
       26.275%). A análise A3 separa as duas coisas antes de classificar risco;
       sem isso, a lista de "frete caro" é quase toda falso positivo.
   ========================================================================= */


/* ============================================================================
   PARTE 0 — DDL no SNOWFLAKE
   ========================================================================= */

CREATE SCHEMA IF NOT EXISTS FRETE;

-- Dimensão de papel duplo: o MESMO cadastro serve de TRANSPORTADORA (quem
-- emitiu o CT-e) e de CLIENTE/EMISSOR da nota transportada. No Siger os dois
-- são "colaborador". Modelar uma vez e referenciar duas evita duplicar cadastro.
CREATE OR REPLACE TABLE FRETE.DIM_COLABORADOR (
  COLABORADOR    NUMBER(12,0),
  RAZAO_SOCIAL   VARCHAR(160),
  NOME_FANTASIA  VARCHAR(160),
  CNPJ_CPF       VARCHAR(20),
  CIDADE         VARCHAR(80),
  UF             VARCHAR(2),
  EH_TRANSPORTADORA BOOLEAN,   -- aparece como LMVL_CCF em algum CT-e
  PRIMARY KEY (COLABORADOR)
);

CREATE OR REPLACE TABLE FRETE.DIM_MUNICIPIO (
  COD_IBGE       NUMBER(9,0),
  MUNICIPIO      VARCHAR(90),
  UF             VARCHAR(2),   -- derivada dos 2 primeiros dígitos do IBGE
  PRIMARY KEY (COD_IBGE)
);

CREATE OR REPLACE TABLE FRETE.DIM_EMPRESA (
  EMPRESA        VARCHAR(3),
  CT_ES          NUMBER(10,0), -- quantos CT-e a empresa tem na janela extraída
  PRIMARY KEY (EMPRESA)
);

-- FATO CABEÇALHO: uma linha por CT-e.
-- Chave natural = (EMPRESA, NUMERO, SERIE, TRANSPORTADORA, CFOP, SEQ)
CREATE OR REPLACE TABLE FRETE.FATO_CTE (
  EMPRESA        VARCHAR(3),
  NUMERO         NUMBER(12,0),
  SERIE          VARCHAR(6),
  TRANSPORTADORA NUMBER(12,0),   -- FK -> DIM_COLABORADOR
  CFOP           NUMBER(6,0),    -- 1352 = dentro do estado · 2352 = fora
  SEQ            NUMBER(6,0),    -- LMVL_SNO (sempre 1 até hoje)
  DT_EMISSAO     DATE,
  DT_MOVIMENTO   DATE,
  MUN_ORIGEM     NUMBER(9,0),    -- FK -> DIM_MUNICIPIO
  MUN_DESTINO    NUMBER(9,0),    -- FK -> DIM_MUNICIPIO
  MODELO         VARCHAR(4),     -- 57 = CT-e
  VALOR_FRETE    NUMBER(16,2),   -- LMVL_VAL — o dinheiro
  BASE_ICMS      NUMBER(16,2),
  VALOR_ICMS     NUMBER(16,2),
  PRIMARY KEY (EMPRESA, NUMERO, SERIE, TRANSPORTADORA, CFOP, SEQ)
);

-- FATO DETALHE: uma linha por NOTA vinculada ao CT-e (média 1,2 por CT-e).
CREATE OR REPLACE TABLE FRETE.FATO_CTE_NOTA (
  EMPRESA        VARCHAR(3),
  NUMERO         NUMBER(12,0),   -- \
  SERIE          VARCHAR(6),     --  | FK composta -> FATO_CTE
  TRANSPORTADORA NUMBER(12,0),   --  |
  CFOP           NUMBER(6,0),    -- /
  NOTA           NUMBER(12,0),   -- LOBL_NOC
  NOTA_SERIE     VARCHAR(6),     -- LOBL_SEC
  CLIENTE        NUMBER(12,0),   -- LOBL_CDF -> DIM_COLABORADOR
  CFOP_NOTA      NUMBER(6,0),    -- LOBL_NOP
  SENTIDO        VARCHAR(9),     -- SAIDA (>=5000) / ENTRADA (<5000)
  EH_DEVOLUCAO   BOOLEAN,
  DT_NOTA        DATE,
  VALOR_NOTA     NUMBER(16,2),   -- LOBL_VAC — a carga
  PRIMARY KEY (EMPRESA, NUMERO, SERIE, TRANSPORTADORA, CFOP, NOTA, NOTA_SERIE, CLIENTE)
);


/* ============================================================================
   PARTE 1 — EXTRAÇÃO no MARIADB
   Janela sugerida: 24 meses. Ajuste as datas em E3 e E4.
   ========================================================================= */

/* ---- E1 · DIM_COLABORADOR --------------------------------------------- */
/* Só quem aparece no frete. O cadastro tem 92.479 colaboradores; puxar todos
   seria carregar a base de clientes inteira para responder sobre transporte. */
SELECT
  v.Cod_colaborador                                   AS COLABORADOR,
  v.Razao_soc_longa                                   AS RAZAO_SOCIAL,
  v.Nome_fantasia                                     AS NOME_FANTASIA,
  v.CNPJ_CPF                                          AS CNPJ_CPF,
  v.Cidade                                            AS CIDADE,
  v.UF                                                AS UF,
  MAX(t.eh_transp)                                    AS EH_TRANSPORTADORA
FROM `02794s000`.view_cliente_fornecedor_iprisma v
JOIN (
  SELECT DISTINCT LMVL_CCF AS cod, 1 AS eh_transp
    FROM `02794s000`.lmvliv
   WHERE LMVL_NOI IN (1352,2352) AND LMVL_EMI >= '2024-09-01'
  UNION
  SELECT DISTINCT LOBL_CDF AS cod, 0 AS eh_transp
    FROM `02794s000`.lobliv_nfc
   WHERE LOBL_DTC >= '2024-09-01'
) t ON t.cod = v.Cod_colaborador
GROUP BY 1,2,3,4,5,6;

/* ---- E2 · DIM_MUNICIPIO ------------------------------------------------ */
/* ⚠ A UF NÃO EXISTE nesta view — só o código IBGE e o nome. Os 2 primeiros
      dígitos do código IBGE são a UF, e é assim que a app de CT-e já resolve. */
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

/* ---- E3 · DIM_EMPRESA -------------------------------------------------- */
SELECT LMVL_EMP AS EMPRESA, COUNT(*) AS CT_ES
FROM `02794s000`.lmvliv
WHERE LMVL_NOI IN (1352,2352) AND LMVL_EMI >= '2024-09-01'
GROUP BY 1;

/* ---- E4 · FATO_CTE ----------------------------------------------------- */
/* O GROUP BY é defensivo: hoje há exatamente 1 linha por CT-e (98.264 de
   98.264 conferidos), mas somar é o certo caso um dia venha partido.        */
SELECT
  c.LMVL_EMP                                          AS EMPRESA,
  c.LMVL_NOT                                          AS NUMERO,
  c.LMVL_SER                                          AS SERIE,
  c.LMVL_CCF                                          AS TRANSPORTADORA,
  c.LMVL_NOI                                          AS CFOP,
  c.LMVL_SNO                                          AS SEQ,
  MIN(c.LMVL_EMI)                                     AS DT_EMISSAO,
  MIN(c.LMVL_DTM)                                     AS DT_MOVIMENTO,
  c.LMVL_CMUR                                         AS MUN_ORIGEM,
  c.LMVL_CMUD                                         AS MUN_DESTINO,
  MAX(c.LMVL_MDF)                                     AS MODELO,
  ROUND(SUM(c.LMVL_VAL), 2)                           AS VALOR_FRETE,
  ROUND(SUM(c.LMVL_BICM), 2)                          AS BASE_ICMS,
  ROUND(SUM(c.LMVL_VICM), 2)                          AS VALOR_ICMS
FROM `02794s000`.lmvliv c
WHERE c.LMVL_NOI IN (1352,2352)          -- aquisição de serviço de transporte
  AND c.LMVL_EMI >= '2024-09-01'
GROUP BY 1,2,3,4,5,6,9,10;

/* ---- E5 · FATO_CTE_NOTA ------------------------------------------------ */
SELECT
  n.LOBL_EMP                                          AS EMPRESA,
  n.LOBL_NOT008                                       AS NUMERO,
  n.LOBL_SER008                                       AS SERIE,
  n.LOBL_CCF008                                       AS TRANSPORTADORA,
  n.LOBL_NOI008                                       AS CFOP,
  n.LOBL_NOC                                          AS NOTA,
  n.LOBL_SEC                                          AS NOTA_SERIE,
  n.LOBL_CDF                                          AS CLIENTE,
  MAX(n.LOBL_NOP)                                     AS CFOP_NOTA,
  CASE WHEN MAX(n.LOBL_NOP) >= 5000 THEN 'SAIDA' ELSE 'ENTRADA' END AS SENTIDO,
  -- devolução: últimos 3 dígitos do CFOP (compra/venda/ST)
  MAX(CASE WHEN MOD(n.LOBL_NOP,1000) IN (201,202,203,204,410,411) THEN 1 ELSE 0 END) AS EH_DEVOLUCAO,
  MIN(n.LOBL_DTC)                                     AS DT_NOTA,
  ROUND(SUM(n.LOBL_VAC), 2)                           AS VALOR_NOTA
FROM `02794s000`.lobliv_nfc n
WHERE n.LOBL_NOI008 IN (1352,2352)
  AND n.LOBL_DTC >= '2024-09-01'
GROUP BY 1,2,3,4,5,6,7,8;


/* ============================================================================
   PARTE 2 — ANÁLISE no SNOWFLAKE
   ========================================================================= */

/* ---- A0 · CONFERÊNCIA — rode antes de confiar em qualquer número -------- */
SELECT COUNT(*)                AS CT_ES,
       SUM(VALOR_FRETE)        AS FRETE,
       MIN(DT_EMISSAO)         AS DE,
       MAX(DT_EMISSAO)         AS ATE
FROM FRETE.FATO_CTE;
-- referência medida na origem em 27/08/2026 (janela desde 2024-09-01):
--   98.264 CT-e · R$ 38.716.132 de frete

/* ---- A1 · O % DE FRETE, o número que a diretoria pergunta --------------- */
/* ⚠ JOIN AGREGADO, não subconsulta correlata (ver armadilha 3).             */
WITH carga AS (
  SELECT EMPRESA, NUMERO, SERIE, TRANSPORTADORA, CFOP,
         SUM(VALOR_NOTA) AS VALOR_NOTAS,
         COUNT(*)        AS QT_NOTAS
  FROM FRETE.FATO_CTE_NOTA
  GROUP BY 1,2,3,4,5
)
SELECT DATE_TRUNC('month', c.DT_EMISSAO)              AS MES,
       COUNT(*)                                       AS CT_ES,
       SUM(c.VALOR_FRETE)                             AS FRETE,
       SUM(g.VALOR_NOTAS)                             AS CARGA,
       ROUND(SUM(c.VALOR_FRETE) / NULLIF(SUM(g.VALOR_NOTAS),0) * 100, 2) AS PCT_FRETE
FROM FRETE.FATO_CTE c
JOIN carga g
  ON  g.EMPRESA = c.EMPRESA AND g.NUMERO = c.NUMERO AND g.SERIE = c.SERIE
  AND g.TRANSPORTADORA = c.TRANSPORTADORA AND g.CFOP = c.CFOP
WHERE g.VALOR_NOTAS > 0
GROUP BY 1 ORDER BY 1 DESC;
-- referência: 93.284 CT-e com nota · R$ 36.720.794 / R$ 879.998.862 = 4,17%

/* ---- A2 · CUSTO POR TRANSPORTADORA E ROTA ------------------------------ */
SELECT t.RAZAO_SOCIAL                                 AS TRANSPORTADORA,
       o.UF                                           AS UF_ORIGEM,
       d.UF                                           AS UF_DESTINO,
       COUNT(*)                                       AS CT_ES,
       SUM(c.VALOR_FRETE)                             AS FRETE,
       ROUND(AVG(c.VALOR_FRETE), 2)                   AS FRETE_MEDIO
FROM FRETE.FATO_CTE c
LEFT JOIN FRETE.DIM_COLABORADOR t ON t.COLABORADOR = c.TRANSPORTADORA
LEFT JOIN FRETE.DIM_MUNICIPIO   o ON o.COD_IBGE    = c.MUN_ORIGEM
LEFT JOIN FRETE.DIM_MUNICIPIO   d ON d.COD_IBGE    = c.MUN_DESTINO
GROUP BY 1,2,3
ORDER BY FRETE DESC;

/* ---- A3 · AUDITORIA: frete caro DE VERDADE ----------------------------- */
/* ⚠ ESTE É O CORAÇÃO DA ANÁLISE. Sem separar vínculo-incompleto de frete-caro,
      a lista de "críticos" é quase toda falso positivo: já apareceu CT-e com
      26.275% porque faltavam notas no vínculo, não porque o frete fosse caro.
      Prova do diagnóstico: nas faixas de % alto o valor médio das notas
      despenca (R$ 9.325 → R$ 66) enquanto o frete fica estável — ou seja, é o
      denominador que sumiu.                                                  */
WITH carga AS (
  SELECT EMPRESA, NUMERO, SERIE, TRANSPORTADORA, CFOP,
         SUM(VALOR_NOTA) AS VALOR_NOTAS, COUNT(*) AS QT_NOTAS
  FROM FRETE.FATO_CTE_NOTA GROUP BY 1,2,3,4,5
),
base AS (
  SELECT c.*, COALESCE(g.VALOR_NOTAS,0) AS VALOR_NOTAS, COALESCE(g.QT_NOTAS,0) AS QT_NOTAS,
         CASE WHEN COALESCE(g.VALOR_NOTAS,0) > 0
              THEN c.VALOR_FRETE / g.VALOR_NOTAS * 100 END AS PCT
  FROM FRETE.FATO_CTE c
  LEFT JOIN carga g
    ON  g.EMPRESA = c.EMPRESA AND g.NUMERO = c.NUMERO AND g.SERIE = c.SERIE
    AND g.TRANSPORTADORA = c.TRANSPORTADORA AND g.CFOP = c.CFOP
),
classificado AS (
  SELECT b.*,
    CASE WHEN b.QT_NOTAS = 0                                   THEN 'SEM_NOTA'
         WHEN b.PCT >= 100                                     THEN 'INCOMPLETO'
         WHEN b.PCT >= 50 AND b.VALOR_NOTAS < 5000             THEN 'INCOMPLETO'
         ELSE 'OK' END                                         AS STATUS_VINCULO
  FROM base b
)
SELECT t.RAZAO_SOCIAL                                 AS TRANSPORTADORA,
       c.EMPRESA, c.NUMERO, c.DT_EMISSAO,
       c.VALOR_FRETE, c.VALOR_NOTAS, ROUND(c.PCT,2)   AS PCT_FRETE,
       CASE WHEN c.PCT >= 25 THEN 'CRITICO'
            WHEN c.PCT >= 15 THEN 'ALTO'
            WHEN c.PCT >=  8 THEN 'ATENCAO'
            ELSE 'NORMAL' END                         AS RISCO_CUSTO
FROM classificado c
LEFT JOIN FRETE.DIM_COLABORADOR t ON t.COLABORADOR = c.TRANSPORTADORA
WHERE c.STATUS_VINCULO = 'OK'          -- <- só aqui o % significa alguma coisa
  AND c.PCT >= 15
ORDER BY c.VALOR_FRETE DESC;

/* ---- A4 · QUANTO CADA STATUS PESA (a saúde do vínculo) ----------------- */
WITH carga AS (
  SELECT EMPRESA, NUMERO, SERIE, TRANSPORTADORA, CFOP,
         SUM(VALOR_NOTA) AS VALOR_NOTAS, COUNT(*) AS QT_NOTAS
  FROM FRETE.FATO_CTE_NOTA GROUP BY 1,2,3,4,5
)
SELECT CASE WHEN COALESCE(g.QT_NOTAS,0) = 0 THEN 'SEM_NOTA'
            WHEN c.VALOR_FRETE / NULLIF(g.VALOR_NOTAS,0) * 100 >= 100 THEN 'INCOMPLETO'
            WHEN c.VALOR_FRETE / NULLIF(g.VALOR_NOTAS,0) * 100 >= 50
                 AND g.VALOR_NOTAS < 5000 THEN 'INCOMPLETO'
            ELSE 'OK' END                             AS STATUS_VINCULO,
       COUNT(*)                                       AS CT_ES,
       SUM(c.VALOR_FRETE)                             AS FRETE,
       ROUND(AVG(g.VALOR_NOTAS), 2)                   AS CARGA_MEDIA
FROM FRETE.FATO_CTE c
LEFT JOIN carga g
  ON  g.EMPRESA = c.EMPRESA AND g.NUMERO = c.NUMERO AND g.SERIE = c.SERIE
  AND g.TRANSPORTADORA = c.TRANSPORTADORA AND g.CFOP = c.CFOP
GROUP BY 1 ORDER BY FRETE DESC;
-- se CARGA_MEDIA despencar na faixa INCOMPLETO, é a confirmação de que o
-- problema é vínculo faltando e não frete caro.

/* ---- A5 · DEVOLUÇÃO: frete que se paga para receber mercadoria de volta - */
SELECT t.RAZAO_SOCIAL                                 AS TRANSPORTADORA,
       COUNT(DISTINCT c.EMPRESA || c.NUMERO || c.SERIE) AS CT_ES,
       SUM(c.VALOR_FRETE)                             AS FRETE_DEVOLUCAO
FROM FRETE.FATO_CTE c
JOIN FRETE.FATO_CTE_NOTA n
  ON  n.EMPRESA = c.EMPRESA AND n.NUMERO = c.NUMERO AND n.SERIE = c.SERIE
  AND n.TRANSPORTADORA = c.TRANSPORTADORA AND n.CFOP = c.CFOP
LEFT JOIN FRETE.DIM_COLABORADOR t ON t.COLABORADOR = c.TRANSPORTADORA
WHERE n.EH_DEVOLUCAO
GROUP BY 1 ORDER BY FRETE_DEVOLUCAO DESC;

/* ---- A6 · ICMS DO FRETE ------------------------------------------------ */
SELECT DATE_TRUNC('month', DT_EMISSAO)                AS MES,
       SUM(VALOR_FRETE)                               AS FRETE,
       SUM(BASE_ICMS)                                 AS BASE_ICMS,
       SUM(VALOR_ICMS)                                AS ICMS,
       ROUND(SUM(VALOR_ICMS) / NULLIF(SUM(BASE_ICMS),0) * 100, 2) AS ALIQUOTA_EFETIVA
FROM FRETE.FATO_CTE
GROUP BY 1 ORDER BY 1 DESC;