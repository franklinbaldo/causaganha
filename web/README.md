# CausaGanha Web — Static Zero-Backend Architecture

O site público do **CausaGanha** é uma aplicação estática pura hospedada no **GitHub Pages** em `/causaganha/`.

## Arquitetura Zero-Backend

A plataforma opera com acesso direto a acervos preservados em shards imutáveis (ZIP Stored) no Internet Archive e no GitHub Pages:

1. **Micro-índices estáticos:** localizados em `indexes/` particionados por tribunal e ano (`{j_tr}_{ano}.json`), contendo o mapeamento de CNJ para o shard, offset de byte e tamanho exato da carga.
2. **HTTP Range Requests:** o cliente no navegador solicita apenas a fatia binária do processo desejado via header `Range: bytes=START-END`, transferindo apenas os bytes exatos do processo.
3. **Codec de alta densidade:** descompressão Zstd em WebAssembly (`fzstd.umd.js`) com decodificação do schema canônico Protobuf (`processo.proto`) e catálogo TPU para enriquecimento semântico.
4. **Sem runtime server:** custo de infraestrutura zero, cache agressivo por CDN, latência sub-segundo e 100% de privacidade para o usuário.

## Estrutura de Arquivos

```
web/
├── public/
│   ├── index.html           # Interface do leitor de processos
│   ├── fzstd.umd.js         # Decompressor Zstd WASM/JS
│   ├── catalogo_tpu.json    # Catálogo CNJ TPU (classes, assuntos, movimentos)
│   ├── indexes/             # Micro-índices por tribunal e ano
│   ├── shards/              # Shards locais/demo em ZIP Stored
│   ├── favicon.svg          # Ícone CausaGanha
│   └── og/                  # Brasões dos tribunais
├── queries/                 # Contratos analíticos DuckDB (.qmd)
└── README.md
```

## Deploy

O deploy é automatizado via GitHub Actions em `.github/workflows/deploy-web.yml`, publicando diretamente a pasta `web/public/` para o GitHub Pages.
