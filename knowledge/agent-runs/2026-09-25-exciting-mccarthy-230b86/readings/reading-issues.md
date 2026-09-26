---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-230b86-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-230b86"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, state=OPEN, 21 abertas no inicio da rodada) cruzadas com docs/SECURITY_THREAT_MODEL.md"
finding: "#1610 (TM-03/TM-04) era a unica issue de seguranca aberta na matriz no inicio da rodada. TM-04 documentava tres emissores de KV_METADATA pendentes -- djen (feito), juris (feito por rodadas anteriores hoje, PRs #1646/#1648/#1650), datajud (aberto, PR #1651 pronta e verde) -- restando so stj (sem pipeline de export sob controle deste repo, fora de alcance documentado) e hash/row-count completo (fora de alcance, decisao ja registrada). Mesclada #1651 nesta rodada: datajud fechado (lado de escrita + leitura, Python+TS). Com isso TM-03 e TM-04 nao tem mais gap tratavel documentado -- avaliar fechamento de #1610 registrado como decisao desta rodada (nao fechada ainda, ver decision correspondente). As 3 PRs externas codex/aardvark (#1643/#1644/#1645, abertas 2026-09-25 15:04-15:05, nao investigadas em profundidade por 3+ rodadas anteriores conforme next_move de fipj1n/ci1aem) tratam de uma classe de ameaca distinta e ate entao nao rastreada por nenhuma linha TM: descoberta/fallback do Internet Archive aceitando busca global nao autenticada como canonica (catalog poisoning), em scripts/generate_catalog.py (#1643) e scripts/reconcile_processos.py (#1644, #1645). Investigado a fundo nesta rodada (ver reading-prs.md): #1643 correto e minimo mas CI stale/merge bloqueado por status check ausente na branch protection; #1644 (lint falhando) e #1645 (CodeQL + tests falhando) tambem stale, precisam de rebase e retrabalho antes de qualquer merge. Aberta issue nova #1652 consolidando as tres superficies desta classe de ameaca sob um unico threat, com secao 'status por superficie' rastreavel; TM-16 adicionado a matriz. Fechada a fatia (1) desta rodada (generate_catalog.py) com TDD proprio; (2) e (3) permanecem abertas para rodada futura reavaliar as PRs externas ja existentes. Demais 20 issues abertas seguem trilhas de longo prazo sem gate de rodada unica: Parquet/CNJ (#1470/#1469/#1471/#1472/#1468/#1022/#985) bloqueadas por credenciais IA ausentes (fato ja estabelecido por 10+ rodadas); segmenter (#1050 e derivadas) com PR aberta #1605 ainda bloqueada por conflito de merge em branch alheia; #951/#1093 produto de longo prazo sem TDD gate imediato."
---

# Leitura: issues abertas

21 issues abertas revisadas via `list_issues`, cruzadas com a matriz
completa em `docs/SECURITY_THREAT_MODEL.md`. `#1610` (TM-03/TM-04) era a
única issue de segurança aberta na matriz; a fatia `datajud` de TM-04 foi
fechada nesta rodada ao mesclar a PR já pronta `#1651`, deixando `#1610`
sem gap tratável restante (registrado como decisão a avaliar). As três PRs
externas `codex/aardvark` (`#1643`/`#1644`/`#1645`), sinalizadas como "não
investigadas" por 3+ rodadas anteriores, foram investigadas a fundo nesta
rodada: cobrem uma classe de ameaça real e não rastreada
(descoberta/fallback do Internet Archive aceitando busca global como
canônica) — consolidada na issue nova `#1652` e na linha `TM-16`, com a
fatia `scripts/generate_catalog.py` fechada nesta própria rodada via TDD
próprio, e as outras duas (`reconcile_processos.py`) deixadas explicitamente
abertas por precisarem de rebase/retrabalho das PRs externas stale.
