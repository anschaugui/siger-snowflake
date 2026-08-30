# Dimensões

Cada módulo em `dags/dimensoes/` tem exatamente duas coisas: uma variável `query` com o
SQL e uma função `executar()` que a entrega a `pipeline()`.

```python
from conexoes import pipeline

query = """SELECT ..."""

def executar() -> int:
    return pipeline(query, "DIM_ALGO")

if __name__ == "__main__":
    executar()
```

O grão e as colunas de cada tabela estão em
[Modelo de dados → Dimensões](../modelo-dados.md#dimensoes). Abaixo, o SQL e a função
de cada uma.

---

## `dim_produto`

Cadastro de produtos, enriquecido com marca e grupo. Maior dimensão do DW
(~135.000 linhas). Os dois `LEFT JOIN` garantem que produto sem marca ou sem grupo
cadastrado continue aparecendo.

::: dimensoes.dim_produto
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [executar]

---

## `dim_local_est`

Locais de estoque por empresa. A coluna correta é **`etbe_cloc`** — existe uma
`etbe_loc` vizinha, com outro significado, e o comentário no SQL marca isso.
`NAO_USAR` sinaliza ao BI o local genérico (`LOCAL = 1`).

!!! bug "Dois defeitos conhecidos neste módulo"
    A `query` termina com uma vírgula depois das aspas triplas, virando uma **tupla**,
    e `executar()` grava em **`DIM_PRODUTO`** em vez de `DIM_LOCAL_EST`. Detalhes e
    impacto em [Pendências](../pendencias.md).

::: dimensoes.dim_local_est
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [executar]

---

## `dim_colaborador`

Clientes e fornecedores que aparecem em algum documento desde `2024-09-01` — não é o
cadastro completo do ERP. A flag `EH_TRANSPORTADORA` vem de um `UNION` entre as
transportadoras de CT-e (`lmvliv`) e os clientes das notas vinculadas
(`lobliv_nfc`); o `MAX()` resolve quem aparece nas duas listas a favor de
"é transportadora".

::: dimensoes.dim_colaborador
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [executar]

---

## `dim_municipio`

Municípios do IBGE. A `UF` é derivada dos dois primeiros dígitos do código IBGE, via um
`CASE` sobre `FLOOR(Cod_IBGE_mun / 100000)` que cobre as 27 unidades federativas — um
código fora da lista produz `UF` nula.

Serve de dimensão para `MUN_ORIGEM` e `MUN_DESTINO` em `FATO_CTE`.

::: dimensoes.dim_municipio
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [executar]

---

## `dim_empresa`

Empresas com movimento de CT-e na janela, com a contagem de linhas de cada uma
(`CT_ES`). Diferente das demais, é derivada do movimento e não de um cadastro: uma
empresa sem CT-e desde `2024-09-01` simplesmente não aparece, e `CT_ES` muda a cada
carga.

::: dimensoes.dim_empresa
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: [executar]
