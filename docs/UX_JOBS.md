# CausaGanha — jobs de utilidade do site

O site não deve apenas expor dados. Cada superfície deve reduzir o caminho entre uma pergunta do usuário e a próxima ação verificável.

## Jobs principais

### Tenho um número CNJ

Quero descobrir rapidamente:

1. o que o CausaGanha encontrou sobre o processo;
2. de quando é essa evidência;
3. em quais fontes ela existe;
4. onde há publicações e documentos para ler;
5. o que posso consultar a seguir quando o snapshot não basta.

A página de processo deve ser um **dossiê acionável**, não uma lista de campos.

### Tenho um nome, OAB, parte ou assunto

Quero localizar publicações relevantes, entender por que elas apareceram e, quando houver CNJ, atravessar imediatamente para o dossiê do processo.

A busca deve preservar URL reproduzível, filtros ativos, origem do resultado e acesso ao inteiro teor. Resultados exportados precisam dizer claramente se representam a página atual ou o conjunto completo.

### Não encontrei o que procurava

Quero saber se:

- a consulta é inválida;
- a fonte estava indisponível;
- não há registro no snapshot;
- a cobertura do tribunal/período pode explicar a ausência;
- existe outra superfície do CausaGanha que ainda vale consultar.

Estado vazio não é fim de fluxo.

### Quero voltar depois

Quero guardar processos e buscas úteis sem criar conta e sem entregar uma lista privada ao servidor.

Quando implementado, o padrão preferido é armazenamento local no navegador, com exportação/importação simples e aviso explícito de que limpar os dados do navegador apaga a lista.

### Quero reutilizar os dados

Quero sair do site com um caminho concreto: copiar um permalink, baixar resultados explicitamente delimitados, ou reconstruir os datasets públicos com as receitas documentadas.

## Princípios

- **Próxima ação visível:** resultados e estados vazios oferecem rotas semanticamente justificadas.
- **Sem becos sem saída:** ausência em uma fonte nunca é apresentada como inexistência do processo.
- **Proveniência antes da conveniência:** cruzar superfícies não apaga qual fonte sustenta cada afirmação.
- **Snapshot não é live:** o site deve mostrar a época do dataset e apontar para consulta de estado atual quando essa capacidade existir.
- **Sem conta por padrão:** utilidades pessoais devem preferir estado local quando não houver necessidade real de servidor.
- **URLs são contratos:** consultas compartilháveis devem continuar reproduzíveis por URL.
- **Exportação honesta:** nunca chamar de “exportar resultados” algo que contém apenas uma página sem dizer isso claramente.

## Ordem de produto

1. tornar o dossiê por CNJ acionável;
2. ligar publicação → processo e melhorar ações da busca;
3. transformar estados vazios em rotas alternativas informadas por cobertura;
4. adicionar consultas salvas localmente;
5. medir/revisar os fluxos completos em desktop e mobile.
