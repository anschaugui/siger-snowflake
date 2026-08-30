# Pendências conhecidas

Levantamento feito na leitura do código e dos logs de execução, em **30/08/2026**.
Nada aqui foi corrigido — esta página existe para registrar o que foi encontrado, com
evidência, para que a correção seja uma decisão consciente.

Ordenado por impacto.

---

## 1. A CLI local (`main.py`) não executa nenhum ETL

**Onde:** `dags/main.py:13-17` · `dags/catalogo.py:12-22`

Os valores de `ETLS` são tuplas `(função, cron)` desde que o agendamento passou a viver
no catálogo, mas `main.py` ainda trata o valor como se fosse a função:

```python
# catalogo.py — o valor é uma tupla
ETLS = {"dim_produto": (dim_produto, "0 6 * * *"), ...}

# main.py — chama a tupla
for nome, funcao in ETLS.items():
    funcao()          # TypeError: 'tuple' object is not callable
# ...
ETLS[args.etl]()      # idem
```

**Efeito:** `python .\dags\main.py fato_compra` e `python .\dags\main.py` falham com
`TypeError: 'tuple' object is not callable` antes de tocar em qualquer banco. O caminho
pelo Airflow não é afetado — `etl_siger_snowflake.py` desempacota a tupla corretamente
(`for nome, (funcao, schedule) in ETLS.items()`).

**Observação:** o `README.md` e o [Runbook](runbook.md#localmente-teste-rapido)
documentam essa CLI como a forma de testar localmente. Enquanto isso não for
resolvido, o teste local precisa passar por `airflow tasks test` dentro do contêiner.

---

## 2. `dim_local_est` grava em `DIM_PRODUTO`

**Onde:** `dags/dimensoes/dim_local_est.py:16`

```python
def executar() -> int:
    return pipeline(query, "DIM_PRODUTO")     # deveria ser "DIM_LOCAL_EST"
```

**Efeito:** dois ETLs escrevendo na mesma tabela de destino. Como a carga é
`if_table_exists="replace"`, o que sobrevive é o último a rodar — e `DIM_LOCAL_EST`
nunca chega a existir no DW.

**Evidência nos logs.** Este é o `[ERROR]` de conferência registrado em 27/08:

```text
[OK]    DIM_PRODUTO: extraído=135668 | snowflake=135668
[ERROR] DIM_PRODUTO: extraído=257    | snowflake=135668
```

A segunda linha é o `dim_local_est` extraindo suas 257 linhas e conferindo contra a
tabela de produto.

## 3. A `query` de `dim_local_est` é uma tupla

**Onde:** `dags/dimensoes/dim_local_est.py:12`

```python
query = """
    SELECT ...
""",     # ← vírgula sobrando
```

A vírgula transforma a string numa tupla de um elemento.

**Efeito:** `Error: query must be either str or a list of str` — o erro aparece 8 vezes
nos logs. O ETL falha na extração, o que na prática impede o problema do item 2 de
sobrescrever `DIM_PRODUTO`. Corrigir só a vírgula, sem corrigir o nome da tabela,
**ativaria** aquele defeito.

!!! danger "Corrigir os dois juntos"
    Os itens 2 e 3 estão no mesmo arquivo e precisam ser resolvidos na mesma alteração.

---

## 4. `extrair_postgres_senda()` passa `"DW"` como protocolo da URI

**Onde:** `dags/conexoes/origens.py:12`

```python
df = pl.read_database_uri(query, uri=montar_uri("POSTGRESQL", "DW"))
```

O segundo parâmetro de `montar_uri()` é o **protocolo/driver** da URI, não o schema do
banco — a própria docstring da função destaca isso. Como está, a URI gerada fica
`DW://user:senha@host:porta/banco`, que nenhum driver reconhece. O valor esperado é
`postgresql`.

**Efeito:** nenhum hoje — a função não é usada por nenhum ETL do catálogo. Vai falhar
no primeiro uso.

**Relacionado:** o `.env.example` não documenta as cinco variáveis `POSTGRESQL_*` que
essa função exige (`POSTGRESQL_USER`, `POSTGRESQL_PASSWORD`, `POSTGRESQL_HOST`,
`POSTGRESQL_PORT`, `POSTGRESQL_DB`).

---

## 5. A divergência de contagem não faz a task falhar

**Onde:** `dags/conexoes/__init__.py` — `conferir_carga()`

A função compara `df.height` com o `COUNT(*)` do destino e **imprime** `[OK]` ou
`[ERROR]`. Não levanta exceção.

**Efeito:** uma carga divergente termina como *success* no Airflow. Não há alerta, e o
`[ERROR]` só é descoberto por quem for ler o log — foi o que aconteceu com o item 2,
que ficou registrado nos logs desde 27/08 sem nenhuma task vermelha na interface.

**Se o comportamento for intencional** (não derrubar a DAG por divergência), vale ao
menos elevar a mensagem para `logging.warning`, que o Airflow destaca, em vez de
`print`.

---

## 6. Senha não é escapada ao montar a URI

**Onde:** `dags/conexoes/util.py` — `montar_uri()` · `dags/conexoes/destinos.py` —
`carregar_snowflake()`

Ambas interpolam a senha direto na URI, sem `urllib.parse.quote_plus`. Uma senha com
`@`, `/`, `:`, `?` ou `#` quebra a URI — e o modo de falha é confuso, porque o parser
interpreta o trecho após o `@` como host.

**Efeito:** nenhum com as senhas atuais; vira uma armadilha na próxima rotação de
credencial.

---

## 7. Os 9 ETLs disparam no mesmo minuto

**Onde:** `dags/catalogo.py` — todos com `"0 6 * * *"`

Nove DAGs abrem conexões com o SIGER e com o Snowflake simultaneamente às 06:00 UTC.

**Efeito observado:** com uma credencial errada no `.env`, o Snowflake recebe nove
tentativas de login falhas em sequência e bloqueia a conta —
`390102: Your user account has been temporarily locked`, que aparece **24 vezes** nos
logs. Escalonar os horários (`0 6`, `10 6`, `20 6`, …) reduziria tanto o pico de carga
quanto a velocidade com que o bloqueio é atingido.

---

## 8. `requirements.txt` está em UTF-16

**Onde:** `requirements.txt`

```console
$ file requirements.txt
requirements.txt: Unicode text, UTF-16, little-endian text, with CRLF line terminators
```

O arquivo tem BOM `FF FE` e um byte nulo entre cada caractere — resultado típico de um
`>` ou `Out-File` do PowerShell. `requirements-docs.txt`, criado depois, está em ASCII.

**Efeito:** o `pip install -r` do `Dockerfile` lê o arquivo com a codificação padrão do
ambiente; UTF-16 pode ser interpretado como lixo. Vale confirmar se a imagem realmente
tem todas as dependências instaladas — o erro
`ModuleNotFoundError: No module named 'websockets'` (50 ocorrências nos logs) é
consistente com uma instalação incompleta.

Para reescrever em UTF-8:

```powershell
Get-Content requirements.txt | Set-Content -Encoding utf8 requirements.txt.novo
```

---

## Itens menores

| Onde | O quê |
|---|---|
| `conexoes/origens.py:1`, `conexoes/__init__.py` | `import os` sem uso |
| `catalogo.py:14` | O ETL de `dim_local_est.py` é registrado como `"dim_local"`; a DAG vira `etl_dim_local`, e existe uma pasta de logs órfã `dag_id=etl_dim_local_est` de um nome anterior |
| `dags/dimensoes/.idea/` | Pasta de configuração de IDE dentro do pacote. Está corretamente ignorada (o padrão `.idea/` do `.gitignore` casa em qualquer profundidade) e não é rastreada — mas é resquício de um projeto PyCharm aninhado e pode ser apagada |
| Todo o código, exceto `montar_uri()` | Nenhuma outra função tem docstring; a documentação de referência gerada fica limitada às assinaturas |
| Queries | `2024-09-01` e a lista `S01, S02, N03, N35` estão repetidos em vários arquivos; mudar o escopo exige editar cada um |
