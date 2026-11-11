# Demonstração reproduzível de Protobuf no DataJud

Este experimento compila o `src/datajud/schema/processo.proto` existente e demonstra
codificação/recuperação integral dos hits reais das fixtures. Não altera os codecs
de produção nem decide a arquitetura definitiva (#1710, #1711).

```bash
uv run --no-project experiments/datajud_protobuf_demo/run.py
uv run --no-project experiments/datajud_protobuf_demo/run.py \
  --scope legacy-68 --output artifacts/protobuf-legacy-68
```

O workflow **DataJud Protobuf demonstration** executa duas amostras:

- `all-hits`: todas as 94 capturas das fixtures, sem deduplicar por `_index/_id`;
- `legacy-68`: os mesmos 68 documentos selecionados pelo benchmark da PR #1712,
  explicitamente identificado como controle histórico, não como acervo completo.

Em cada amostra, compara JSON integral, Protobuf canônico, Protobuf com templates
estruturais de movimentos e JSON do **mesmo modelo lógico compacto**. Mede bytes
sem/com Zstd L3, incluindo dicionários, e publica os custos residuais separadamente.
As medidas agregam todas as coleções, não representam bytes/tempo por processo.
Tempos são locais em memória, com aquecimento e repetições; não medem IA, RAM,
índices de descoberta ou latência de rede. O JSON compacto é um controle do mesmo
modelo Protobuf, não a melhor modelagem JSON possível.

## Fidelidade explícita

O schema proto3 atual não representa diretamente toda diferença entre ausente,
null, zero, campos desconhecidos, inteiros arbitrários e valores heterogêneos.
`demo.proto` envolve as mensagens tipadas existentes com **correções residuais
JSON**, contendo somente as diferenças necessárias à reconstrução exata. Não se
armazena uma segunda cópia integral do documento para os hits do corpus.
Estruturas não representáveis podem exigir fallback residual maior; esse custo
é incluído. Isso demonstra Protobuf com adaptação reversível, sem alegar que o
schema tipado sozinho já cobre todos os casos.

Na variante compacta, templates conservam os nomes literais, códigos, estrutura
dos complementos e campos extras. Cada ocorrência continua representada,
incluindo data, órgão, valores, posição na lista e vínculo com seu hit. O residual
preserva nulos, presença e tipos que não cabem nos campos originais. Não há
deduplicação de eventos ou descarte de versões/capturas por identidade de origem.

Um **segundo processo** lê os `.pb`, `.pb.zst` e catálogo do disco, compara cada
documento com as fixtures e confere CNJ, cardinalidade e hashes. Sem fixture ou
com corrupção de catálogo o job falha. O teste adicional exercita esses casos de
schema e alteração de catálogo. O resultado só é verde com recuperação integral;
não há meta de tamanho que possa mascarar perda.

## Evidências

O artefato de Actions contém `summary.md`, `results.json`, `manifest.json`, catálogo,
classes geradas naquele run e coleções serializadas nas quatro variantes. O
manifesto registra SHA do código, hashes das fixtures e dos resultados esperados.
A matriz de resumo aparece na página do run.

Para conferir novamente um artefato baixado:

```bash
uv run --no-project experiments/datajud_protobuf_demo/run.py \
  --output /caminho/do/artefato --verify-only
```

O total sem/com compressão inclui o dicionário de templates uma vez. O custo frio
por CNJ depende de baixar/cachear esse catálogo e ainda precisa de ensaio de rede.
O encoding end-to-end inclui projeção, serialização e cálculo do residual por
coleção; o catálogo é construído previamente e seu custo não está nesse tempo.
Nenhum número fixa antecipadamente os **41.272 bytes** relatados historicamente:
é uma medição nova e verificável do schema existente com fidelidade integral.
