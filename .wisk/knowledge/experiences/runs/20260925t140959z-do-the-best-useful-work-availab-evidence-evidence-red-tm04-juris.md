---
type: "RunEvidence"
id: "run-evidence/20260925t140959z-do-the-best-useful-work-availab/evidence-red-tm04-juris"
run: "runs/20260925T140959Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "uv run pytest -q tests/causaganha/processos/test_service.py -k 'Juris or juris_artifact'"
summary: "RED confirmado antes da implementacao: 10 testes novos falhando -- AttributeError (service._juris_item_id_da_url/_validar_metadata_juris ainda nao existiam) nos 9 testes unitarios de TestMetadataJurisCoerente, e AssertionError (result.juris nao era None) no teste de integracao de mismatch, provando que buscar_processo aceitava um artefato juris com item_id de rodape divergente sem descartar."
goal: "run-goals/20260925t140959z-do-the-best-useful-work-availab/goal-tm04-juris-read-side"
---

# RunEvidence
