---
goal: "Sintetizar como conhecimento durável a decisão de escopo do gate de supply-chain (#1614/TM-10): escanear apenas o conjunto --no-dev realmente embarcado, remover ferramentas de dev mortas em vez de suprimir suas vulnerabilidades, e documentar quando um pin transitivo de dev-tooling (ex.: marimo<11 travando pymdown-extensions) é aceito como fora de escopo em vez de forçar um bump não relacionado."
id: "run-goals/20260925t135611z-do-the-best-useful-work-availab/consolidate-supply-chain-scan-scope"
kind: "consolidate-knowledge"
rationale: "Rodadas futuras que auditam dependências/CI vão repetir a mesma pergunta (por que nao escanear o ambiente dev completo? por que nao só suprimir a vulnerabilidade com ignore-vuln? por que remover 'safety' em vez de so ignorar seu achado?) sem essa decisão registrada como conhecimento reutilizável -- o padrão generaliza para qualquer dependência de dev-tooling futura que trave uma versão vulnerável."
run: "runs/20260925T135611Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "Uma nova WikiEntry existe em .wisk/knowledge/wiki/ documentando esse padrão (escanear o conjunto realmente implantado, preferir remover ferramenta morta a suprimir achado, quando aceitar um pin transitivo de dev-tooling como fora de escopo) referenciando PR #1640; okf-parser check knowledge continua conformant depois de criá-la."
type: "RunGoal"
---

# RunGoal
