# FAQ e Limitações

**Como configurar a chave da API do Gemini?**

-   **Para execução via GitHub Actions:** Defina o segredo `GEMINI_API_KEY` nas configurações do repositório GitHub.
-   **Para execução local:** Exporte a variável de ambiente `GEMINI_API_KEY`. Por exemplo, no seu terminal:
    ```bash
    export GEMINI_API_KEY="SUA_CHAVE_API_AQUI"
    ```
    Você pode adicionar esta linha ao seu arquivo de configuração do shell (como `.bashrc`, `.zshrc`) para que ela seja definida automaticamente em novas sessões do terminal.

**Quais são as principais limitações atuais?**

-   **Cotas da API Gemini:** O sistema depende das cotas da API do Google Gemini. O nível gratuito possui limitações de requisições por minuto (RPM) e um total diário de requisições. Exceder esses limites pode interromper a extração.
-   **Fonte de Dados Única:** Atualmente, o sistema está configurado para processar exclusivamente o Diário de Justiça Eletrônico do Tribunal de Justiça de Rondônia (TJRO).
-   **Identificação de Advogados:** A identificação dos advogados baseia-se na normalização de seus nomes extraídos dos PDFs. Isso pode levar a:
    *   **Colisões:** Advogados diferentes com nomes muito similares (ou idênticos após normalização) podem ser tratados como o mesmo indivíduo se o número da OAB não estiver presente ou não for claramente distinguível.
    *   **Falhas na Identificação:** Nomes grafados de forma inconsistente ou a ausência do nome/OAB podem impedir a correta identificação e, consequentemente, a atribuição de rating.
-   **Interpretação de Resultados pelo LLM:** A determinação do resultado da decisão (procedente, improcedente, etc.) é feita pelo modelo de linguagem (LLM). Embora o prompt seja direcionado, a precisão dessa interpretação pode variar, especialmente em textos complexos ou ambíguos, o que pode afetar a correta atribuição de vitória, derrota ou empate no sistema TrueSkill.
-   **Processamento de Empates e Decisões Parciais:** Embora o TrueSkill suporte empates, as nuances de decisões "parcialmente procedentes" ou outras formas de resultado que não são vitórias/derrotas claras são atualmente simplificadas para o conceito de empate do TrueSkill. Um tratamento mais ponderado poderia ser explorado.

**Como baixar manualmente o Diário?**

Use o endereço https://www.tjro.jus.br/diario_oficial/ultimo-diario.php. Ele redireciona automaticamente para o PDF do dia. Caso veja a mensagem "Página Bloqueada", o site detectou acesso automático; tente abrir no navegador.
