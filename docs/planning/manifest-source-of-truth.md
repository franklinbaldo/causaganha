# Decisão: Fonte da verdade do manifesto — log append-only + compactação para Parquet

## Status
* **Proponente:** Franklin Baldo + Claude
* **Data:** 2026-06-01
* **Status:** **Decisão tomada** — substitui o trio CSV + upload-deltas + Parquet.
* **Apoia-se em:** verificação ao vivo contra o DJEN (abaixo).

---

## 1. Contexto e o sintoma que disparou isto

Hoje o estado do manifesto vive em **três representações**:

```
sync-manifest.csv      ← engine (checker/uploader) faz append    } render
upload-deltas-*.csv    ← drain/probe fazem append (correções)    } ──────► sync-manifest.parquet
```

`scripts/render_manifest_parquet.py` baixa o CSV (base), **mescla os deltas** (correções) e
emite o Parquet, que é o que todos os leitores consomem (dashboard, `drain.fetch_pending_batch`,
análise, catálogo).

**O sintoma:** o Parquet **derivado** está *mais correto* que o CSV **canônico**.

### Evidência (ground truth, ao vivo)

Amostra das linhas onde Parquet diz `absent` mas o CSV traz `djen_raw='200'`
(`djen_status='available'`):

| amostra | resultado ao vivo no DJEN |
|---|---|
| 25/25 contraditórias | **HTTP 200 com corpo `"Sem comunicações"`** → genuinamente **absent** |
| 15/15 controle (Parquet=available+uploaded) | **available** (prova que o proxy discrimina) |

Conclusão: o **Parquet está certo, o CSV está errado** para ~**79K** linhas. `djen_raw='200'`
é só o status HTTP — **não** prova disponibilidade; um 200 sem URL no corpo
(`"Sem comunicações"`) é ausente, igual a 404/400. (Ver `CLAUDE.md` → *Correctness*.)

---

## 2. O princípio violado

> **Dado derivado tem que ser função pura e reproduzível da fonte.** Você deve poder apagar o
> derivado e regenerá-lo idêntico. Se o regenerado é *mais correto* que a "fonte", então o que
> você chamou de fonte da verdade **não é a fonte**.

O `render` mistura **duas responsabilidades**: (a) conversão de formato CSV→Parquet e
(b) **aplicação de mutações** (os deltas). Isso injeta no Parquet informação que **não existe**
no CSV → o CSV apodrece e os deltas crescem sem limite.

### O que isto é, na real

Um **log-structured merge feito à mão** (estilo RocksDB/Cassandra): base (CSV) + logs de eventos
(deltas) → view compactada (Parquet). É um padrão legítimo. **O bug é único:** numa LSM de
verdade a **compactação substitui a base**; aqui ela joga o resultado num Parquet "descartável"
e **nunca escreve de volta**. Os deltas append-only existem por um bom motivo: **escritores
concorrentes** (workflows `collect-zips`, `drain`, `probe` em crons sobrepostos) não podem mutar
um único arquivo no IA sem se atropelar — então cada um anexa seu próprio segmento imutável.

---

## 3. Por que Parquet (e não SQLite) no IA

- **Leitura:** o IA serve arquivos com **HTTP Range**; o DuckDB httpfs lê o footer, pula
  row-groups por estatística e baixa só as colunas/row-groups da query. Colunar + ZSTD ≈ 22×
  menor que o CSV. É o formato certo de leitura — e os consumidores já dependem dele.
- **Escrita:** a única vantagem do SQLite seria `UPDATE` transacional in-place. **O IA anula
  isso**: não há escrita parcial nem transação — toda gravação **substitui o objeto inteiro** —
  e há escritores concorrentes. SQLite só compensaria **fora do IA** (banco com escritor único:
  Postgres/Turso/LiteFS), o que é decisão de *hosting*, não de arquivo.

O desenho blob-native correto: **escrever objetos novos imutáveis, nunca mutar.**

---

## 4. Decisão

```
Fonte da verdade = LOG append-only de eventos (segmentos imutáveis no IA)
                   └─ cada escritor concorrente grava SEU próprio segmento (sem clobber)
Compactação      = replay do log → NOVO Parquet base + poda dos segmentos consumidos
Camada de leitura = esse mesmo Parquet (colunar, range-readable)
```

Isto é **event sourcing + log compaction**, com o **Parquet como base compactada *e* formato de
leitura**. E **aposenta o `sync-manifest.csv`**: seus dois papéis somem —

- papel de **log de append** → vira o log de eventos (os `upload-deltas`, formalizados);
- papel de **estado atual** → vira o Parquet compactado.

O CSV era a **camada do meio redundante** que apodrecia porque a compactação nunca escrevia de
volta. O Parquet deixa de ser "mais correto que a fonte" porque passa a **ser** a materialização
da fonte.

### 4.1 Modelo de dados

Cada evento é um *upsert* com chave `(tribunal, date)`:

| campo | descrição |
|---|---|
| `tribunal`, `date` | chave |
| `djen_raw` | status HTTP cru observado (`200`/`404`/`400`/`403`/`timeout`/`network`) |
| `djen_status` | **veredito** derivado da resposta completa: `available` (200 **com URL**), `absent` (404/400 **ou 200 "Sem comunicações"**), `unknown` (403/timeout/network) |
| `ia_status` | `uploaded` quando arquivado no IA |
| `observed_at` | timestamp do evento (resolve conflitos: **last-observed-at vence** por chave) |

Eventos parciais são permitidos (ex.: o uploader só seta `ia_status`; o checker só seta
`djen_raw`+`djen_status`). A compactação faz o merge campo-a-campo por `observed_at`.

### 4.2 Escrita (concorrência)

- Escritores **nunca tocam a base**. Cada run grava **um segmento novo e imutável**, nome único:
  `manifest-log/<YYYYMMDDTHHMMSSZ>-<writer>-<run_id>.csv` (CSV pequeno = append trivial; pode ser
  Parquet também — o que importa é ser imutável e único).
- Sem clobber possível: dois jobs concorrentes geram nomes distintos.

### 4.3 Compactação (escritor único)

Job agendado, serializado por `concurrency:` no workflow **e** pelo per-item lock do IA:

1. Lê a base Parquet atual + todos os segmentos ainda não compactados.
2. Aplica upserts (merge por `observed_at`, last-write-wins por chave).
3. Escreve a **nova base Parquet** de forma atômica (sobe com nome temporário → renomeia/substitui).
4. Registra quais segmentos foram absorvidos e **poda** (move para `manifest-log/compacted/` ou
   apaga, mantendo os últimos N para auditoria/replay).

### 4.4 Leitura

**Inalterada.** Consumidores continuam lendo `sync-manifest.parquet` via DuckDB httpfs
(dashboard, `drain.fetch_pending_batch`, análise, catálogo). É a mesma base, agora confiável.

---

## 5. Migração (sem perda de dado)

> **Ponto crítico:** a nova base é semeada a partir do **Parquet atual** (verificado correto),
> **não** do CSV (provado errado). Esta é a reconciliação única que conserta os ~79K.

Fases incrementais — cada uma é segura e entrega valor isolado:

- **Fase 0 — congelar a verdade.** Snapshot do Parquet atual como `manifest.parquet` base inicial.
  Manter o `sync-manifest.csv` como backup histórico (não apagar o arquivo ainda).
- **Fase 1 — compactação com write-back (mata a deriva já).** Alterar `render_manifest_parquet`
  para que o merge **vire a nova base** e os segmentos consumidos sejam podados. Mesmo antes de
  aposentar o CSV, isto estanca a divergência. *(Menor mudança, maior retorno.)*
  - **Sequência obrigatória de ops:** `parar o engine → rodar o write-back → reiniciar o engine`.
    Um engine em execução segura as ~79K linhas legadas como `available` em memória e **não
    re-checa** linhas que já têm `djen_status`, então o upload periódico de 10 min dele
    sobrescreveria o CSV corrigido de volta para `available`-200. A ordem não é "ideal", é
    requisito.
  - **Autoconsistência da linha corrigida:** o merge dos deltas só vira `djen_status='absent'` e
    deixa `djen_raw='200'` para trás — uma linha que se contradiz (`interpret_djen_raw('200')`
    deriva `available`). O write-back reescreve esse raw para o sentinela `no_publications` (já em
    `ABSENT_CODES`), então a linha re-deriva para `absent` independentemente de quem leia, sem
    depender de cada consumidor confiar no `djen_status` salvo em vez do raw. *(Fecha a questão §7.3
    para o legado.)*
- **Fase 2 — escritores emitem só segmentos.** `SyncManifest` (`manifest.py`) e o checker param
  de reescrever o CSV canônico; passam a gravar segmentos de log. Drain/probe já fazem isto.
- **Fase 3 — remover o CSV.** Tirar as referências a `sync-manifest.csv` dos ~27 arquivos / 7
  workflows; aposentar `to_csv`/persist como fonte. (Exportar CSV sob demanda, se algum consumidor
  externo precisar, vira um derivado opcional do Parquet.)

---

## 6. Consequências

- **Positivas:** uma fonte autoritativa; Parquet nunca mais "mais correto que a fonte";
  deltas/segmentos param de crescer sem limite; concorrência segura por construção; leitores
  intactos.
- **Custo:** mexe no `render`, em `manifest.py`, nos writers (checker/drain/probe) e em 7
  workflows. Mitigado pelo faseamento (Fase 1 sozinha já corrige o problema atual).
- **Schema:** `djen_raw` permanece como **transporte** e `djen_status` como **veredito**. Para
  reduzir ambiguidade futura, considerar registrar o 200-vazio de forma distinta (ex.:
  `djen_raw='200-empty'`) — opcional, ver §7.

---

## 7. Questões em aberto

1. **Formato do segmento de log:** CSV minúsculo (append trivial, debugável) vs Parquet uniforme.
   Recomendação: CSV para segmentos, Parquet para a base compactada.
2. **Retenção de segmentos compactados:** apagar vs arquivar os últimos N para replay/auditoria.
3. **Desambiguar o 200-vazio no `djen_raw`** (`200-empty`/`sem_comunicacoes`) para que o veredito
   seja reproduzível direto do raw, sem depender só do `djen_status`. *(Para o legado já resolvido
   na Fase 1: o write-back grava `no_publications`. Em aberto fica só padronizar o que os
   **checkers ao vivo** persistem daqui pra frente — hoje o engine já grava `no_publications`.)*
4. **Tombstones / reset para `unknown`:** como um evento representa "esqueça o veredito anterior".
5. **Bootstrap:** confirmar por auditoria ampla (não só amostra) que o Parquet atual está 100%
   correto antes de promovê-lo a base — ou rodar um `probe` completo de reconciliação primeiro.
