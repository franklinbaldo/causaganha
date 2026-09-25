---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-230b86-goal-catalog-discovery-allowlist"
run_id: "2026-09-25-exciting-mccarthy-230b86"
goal: "Fechar a lacuna real em scripts/generate_catalog.py onde uma rebuild --verified-inventory podia cair em busca global do IA (list_ia_items, identifier:djen-*) em vez de usar exclusivamente o sync-manifest.csv do projeto, com TDD proprio; e converter as tres PRs externas codex/aardvark (#1643/#1644/#1645) -- sinalizadas por 3+ rodadas anteriores como 'possivel overlap com #1610, nao investigado' sem nunca receber veredito -- num achado de seguranca rastreado formalmente (issue nova + linha de matriz)."
rationale: "Investigar essas PRs a fundo revelou um bug real e sem nenhum teste de regressao cobrindo o caminho verified-inventory, e uma classe de ameaca inteira (catalog/data poisoning via descoberta IA nao autenticada) sem nenhuma linha na matriz de seguranca. Deixar isso repetir 'nao investigado' rodada apos rodada, enquanto as PRs externas ficam paradas e cada vez mais stale, nao e um estado aceitavel -- o proprio relatorio anterior (qjwekj) listou isso como item (4) do next_move sem resolucao."
success_signal: "Teste novo em tests/test_archive_partitions.py falha com AttributeError antes da mudanca (RED); scripts.generate_catalog.discover_catalog_items existe e, com verified_inventory=True, nunca chama list_ia_items() mesmo com manifesto vazio, comprovado por dois testes GREEN; uv run ruff check/format --check limpos; uv run pytest -q (suite completa) verde; issue #1652 aberta com secao 'status por superficie' cobrindo as tres PRs; TM-16 adicionado a docs/SECURITY_THREAT_MODEL.md."
status: "achieved"
---

# Goal: allowlist de descoberta de catálogo IA + rastreamento formal

O valor real aqui não é apenas o fix pontual em `generate_catalog.py` —
é encerrar um ciclo de 3+ rodadas em que a mesma pergunta ("essas PRs
overlapam com #1610?") era registrada e nunca respondida. Investigar,
responder com evidência concreta (diffs lidos, CI checado, arquivos
tocados comparados), fechar a fatia tratável com TDD próprio desta sessão,
e dar às duas fatias restantes um lugar formal para continuar (issue +
linha de matriz) em vez de ficarem soltas em PRs externas paradas.
