---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-orr2e3-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Releitura integral no início da rodada. Nenhum trabalho desta rodada toca djen-backup/manifest, contratos `.qmd` ou a fronteira Panda/Svelte, então a maior parte do guia não se aplica diretamente. O que se aplica: a seção 'Correctness' documenta explicitamente a disciplina deste projeto de nunca aceitar um status registrado como verdadeiro sem verificação ao vivo ('Não confunda X com Y'; 'verifique contra Y ao vivo... não assuma que um status registrado está certo só porque parece canônico') -- esse princípio motivou diretamente a investigação desta rodada: em vez de aceitar a issue #950 fechada e o texto de `docs/SECURITY_THREAT_MODEL.md` TM-02 como corretos, cada um foi verificado contra o estado observável real (workflow runs do GitHub Actions; código+testes do CF relay), revelando que ambos estavam desalinhados com a realidade em direções opostas (uma issue fechada sem o critério de aceite cumprido; uma linha do threat model marcando como pendente um controle que já foi implementado e testado)."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no início da rodada. A seção
"Correctness" (disciplina de verificar contra o estado ao vivo antes de
confiar num status registrado) motivou a escolha de trabalho desta
rodada: duas discrepâncias entre o que o repositório/GitHub *diz* e o que
é observavelmente verdadeiro, encontradas ao verificar issues fechadas e
o threat model contra o código e os workflow runs reais.
