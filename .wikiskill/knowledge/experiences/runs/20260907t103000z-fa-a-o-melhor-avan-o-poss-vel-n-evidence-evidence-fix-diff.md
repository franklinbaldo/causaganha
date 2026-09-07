---
type: "RunEvidence"
id: "run-evidence/20260907t103000z-fa-a-o-melhor-avan-o-poss-vel-n/evidence-fix-diff"
run: "runs/20260907T103000Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
kind: "execution"
reference: "rm -rf .wisk; ln -s .wikiskill .wisk; uv run wisk init . -- .gitignore e .claude/hourly-loop.md atualizados para descrever o symlink; tests/test_wikiskill_bundle.py ganhou test_wisk_root_is_a_symlink_into_wikiskill"
summary: "'.wisk' agora é symlink versionado para '.wikiskill'. 'uv run wisk init .' através do symlink reporta conformant=true, preserved_files=82 (todo o conhecimento real das rodadas anteriores preservado), escrevendo manifest.json/specs//knowledge/system/ direto sob .wikiskill/, ignorados por um .wikiskill/.gitignore aninhado que o próprio wisk gera."
goal: "goal-fix-wisk-bootstrap-path"
---

# RunEvidence
