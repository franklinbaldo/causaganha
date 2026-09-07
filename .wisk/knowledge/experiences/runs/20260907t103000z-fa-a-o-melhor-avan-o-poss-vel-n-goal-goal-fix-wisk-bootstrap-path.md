---
goal: "Fazer o loop horário do Wisk gravar de fato seu LoopRun/Experience sob .wikiskill/knowledge/ (rastreado pelo Git), em vez de silenciosamente sob .wisk/ (ignorado)"
id: "run-goals/20260907t103000z-fa-a-o-melhor-avan-o-poss-vel-n/goal-fix-wisk-bootstrap-path"
kind: "task-advance"
rationale: "wisk.bootstrap.init_repository grava seu bundle gerenciado em <repo>/.wisk (hardcoded); .claude/hourly-loop.md documenta 'wisk init .' + 'wisk session start-next ...' sem --path, e o CLI do wisk resolve o caminho padrão para .wisk/knowledge sempre que esse diretório existir. Resultado: toda rodada do loop horário desde a migração para o pacote 'wisk' (PR #1260) estava gravando LoopRun/RunReading/RunGoal/etc num diretório separado e ignorado pelo Git, perdendo esse conhecimento ao fim do container -- confirmado experimentalmente nesta própria rodada antes da correção."
run: "runs/20260907T103000Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
status: "achieved"
success_signal: "'.wisk' é um symlink versionado para '.wikiskill'; 'wisk session start-next ...' sem --path grava o LoopRun sob .wikiskill/knowledge/experiences/runs/ (verificado por execução real); novo teste tests/test_wikiskill_bundle.py::test_wisk_root_is_a_symlink_into_wikiskill fica RED antes e GREEN depois; suite completa (uv run pytest -q) permanece verde."
type: "RunGoal"
---

# RunGoal
