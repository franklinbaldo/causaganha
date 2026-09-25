---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-5pnpmt-decision-add-relay-cf-ci-job"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
question: "Ao procurar onde deployment/relay-cf/test/index.test.js roda em CI para confirmar que a suite nova (TM-02/#1609) sera de fato aplicada em todo PR futuro, um grep em .github/workflows/*.yml por 'relay-cf' nao encontrou nenhum job -- ao contrario de deployment/archive-cors-proxy, que tem um job dedicado em test.yml. O relay Cloudflare simplesmente nunca teve CI. Adicionar o job faltante nesta mesma rodada, ou deixar como achado registrado para depois?"
choice: "Adicionar um job 'relay-cf' a .github/workflows/test.yml nesta mesma rodada, espelhando exatamente o job 'archive-cors-proxy' ja existente (mesmo padrao: actions/setup-node, npm ci, npm test, npm run check como dry-run)."
rationale: "Sem esse job, a suite de 18 casos escrita e verificada localmente nesta rodada (incluindo os 9 novos que fecham TM-02 no lado Cloudflare) nunca rodaria de novo em nenhum PR futuro -- uma regressao no relay CF (por exemplo, algum PR reintroduzindo o encaminhamento de Authorization) passaria por CI verde sem ser pega, deixando #1609 'fechada' apenas de nome. O custo de adicionar o job e baixo (10 linhas, mesmo padrao ja provado pelo job irmao archive-cors-proxy) e o ganho e direto: e o proprio criterio de 'sinal observavel de sucesso' desta rodada -- um teste sem gate automatizado nao e uma regra imposta, e so documentacao. Validado localmente (yaml.safe_load confirma sintaxe valida) antes de commitar, ja que esta sessao nao pode disparar o workflow real do GitHub Actions para confirmar o job novo roda verde no CI hospedado."
---

# Decisao: adicionar job de CI para o relay Cloudflare

`deployment/relay-cf/` nunca teve job de CI, ao contrario de todo
outro deploy JS do repositorio (`archive-cors-proxy`, `web`). A suite
de testes que fecha `TM-02`/`#1609` no lado Cloudflare so vale como
gate real se rodar em todo PR futuro -- por isso o job foi adicionado
nesta mesma rodada, nao deixado como achado para depois.
