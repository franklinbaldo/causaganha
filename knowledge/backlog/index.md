# Backlog bloqueado

Cache durável de fatos que sobrevivem a mais de uma rodada do loop horário. Cada arquivo `issue-<n>.md` é um `BacklogItem` (schema em `knowledge/okf.schema.sql`) que registra por que a issue `#<n>` está atualmente bloqueada ou despriorizada, e qual rodada (`last_verified_run_id`) confirmou isso pela última vez.

**Por que existe:** pelo menos ~10 rodadas seguidas releram e rejustificaram do zero o mesmo conjunto de issues bloqueadas, porque `AgentReading` é preso ao `run_id` da própria rodada e morre junto com o diretório dela. Este diretório fica fora da árvore de qualquer rodada específica — como os conceitos de domínio (`Fonte`, `Processo`, ...) — para que o fato sobreviva.

**Como usar (início de rodada):** antes de reler todas as issues abertas do zero, leia `knowledge/backlog/issue-<n>.md` para cada issue aberta. Se `status` ainda for `blocked`/`deprioritized` e `blocking_reason` continuar válido, cite o arquivo na sua própria `AgentReading` de issues em vez de reinvestigar. Só reabra a investigação se: a issue mudou de estado no GitHub, o ambiente mudou (ex.: credenciais passaram a existir), ou `last_verified_at` está muito antigo.

**Como manter:** ao verificar uma issue já registrada aqui e confirmar que a razão ainda vale, atualize `last_verified_run_id`/`last_verified_at` para a rodada atual. Ao descobrir que uma issue foi desbloqueada, mude `status` para `unblocked` (ou delete o arquivo, já que a issue deixou de ser "backlog bloqueado"). Ao surgir uma issue nova claramente bloqueada, adicione um novo `issue-<n>.md`.

`tests/knowledge/test_backlog.py` valida a integridade estrutural deste diretório (chave única, enums válidos, campos não vazios, `last_verified_run_id` apontando para uma rodada real em `knowledge/agent-runs/`).
