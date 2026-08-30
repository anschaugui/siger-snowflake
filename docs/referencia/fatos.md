# Fatos

Mesmo formato das dimensões: uma `query` e um `executar()` por módulo. A diferença está
no SQL — todos os fatos **já chegam agregados** da origem, com `GROUP BY` e `SUM()`
rodando no MySQL. O grão de cada tabela, portanto, está fixado na query.

Grão, colunas e cálculos completos em
[Modelo de dados → Fatos](../modelo-dados.md#fatos).

---

## `fato_compra`

Compras agregadas por empresa × período × produto × combinação. `PERIODO` é
`AAAAMM` como inteiro (`DATE_FORMAT(nped_dte, '%Y%m') + 0`). Traz medidas de
quantidade e valor, além de `COUNT(DISTINCT)` de notas e clientes.

Três conjuntos de filtros definem o que conta como compra:

- `nped_pos <> 9` e `nipf_pos <> 9` — descarta cancelados
- `nped_ees IN (20, 22, 23, 37, 88)` — situações válidas do pedido
- `nipf_cfo IN (5101, 5401, 6101, 6107, 6109, 6118, 6151, 7101, 7127)` — CFOPs considerados

::: fatos.fato_compra
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [executar]

---

## `fato_estoque`

Acumulado de estoque por empresa × período × produto × local × combinação, com saldo,
entradas e saídas em quantidade e valor.

É o maior ETL do projeto — 1,6 a 2,0 milhões de linhas — e o **único sem corte por
data**: traz todo o histórico das quatro empresas. É onde o caminho
connectorx → Arrow → ADBC mais compensa; qualquer conversão para Pandas no meio
dominaria o tempo de execução.

::: fatos.fato_estoque
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [executar]

---

## `fato_cte`

Conhecimentos de transporte de **aquisição de serviço** — CFOP `1352` e `2352`. Um
registro por documento, com valor do frete, base e valor de ICMS somados, e os
municípios de origem e destino ligando a `DIM_MUNICIPIO`.

Datas e modelo entram como `MIN()`/`MAX()` porque são constantes dentro do grupo; os
agregados só existem para satisfazer o `GROUP BY`.

::: fatos.fato_cte
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [executar]

---

## `fato_cte_nota`

As notas fiscais transportadas dentro de cada CT-e — o detalhe de `fato_cte`. Junta-se
a ele pela quádrupla `EMPRESA + NUMERO + SERIE + TRANSPORTADORA`.

Duas colunas são derivadas da estrutura do CFOP brasileiro:

| Coluna | Regra | Racional |
|---|---|---|
| `SENTIDO` | `'SAIDA'` se `CFOP_NOTA >= 5000` | o primeiro dígito indica o sentido: 1–3 entrada, 5–7 saída |
| `EH_DEVOLUCAO` | `MOD(CFOP_NOTA, 1000) IN (201,202,203,204,410,411)` | os três últimos dígitos indicam a natureza, independente de ser interna, interestadual ou de exterior |

::: fatos.fato_cte_nota
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [executar]
