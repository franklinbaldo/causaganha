# CausaGanha MCP — deploy HTTP

Artefato reproduzível para publicar a mesma fachada read-only servida por `causaganha-mcp` via Streamable HTTP.

## Build local

```bash
docker build \
  -f deployment/mcp/Dockerfile \
  --build-arg GIT_SHA="$(git rev-parse HEAD)" \
  -t causaganha-mcp:local .

docker run --rm -p 8080:8080 causaganha-mcp:local
curl --fail http://127.0.0.1:8080/health
```

O container faz bind externo apenas no ambiente empacotado. O entrypoint local continua loopback-safe por padrão.

## Contrato operacional

Defaults do artefato:

- `CAUSAGANHA_MCP_HOST=0.0.0.0`;
- `CAUSAGANHA_MCP_PORT=8080`;
- `CAUSAGANHA_MCP_PATH=/mcp`;
- `CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS=45`;
- `CAUSAGANHA_MCP_MAX_CONCURRENCY=4`;
- `CAUSAGANHA_MCP_COMMIT` recebe o SHA passado em `--build-arg GIT_SHA=...`.

Nenhuma credencial de Internet Archive, DataJud ou outra fonte faz parte do contrato do cliente.

## Exemplo Cloud Run

A publicação é deliberadamente manual até a revisão de #950 decidir a URL estável. Um rollout pode usar:

```bash
PROJECT_ID="seu-projeto"
REGION="southamerica-east1"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/causaganha/mcp:$(git rev-parse --short=12 HEAD)"
SHA="$(git rev-parse HEAD)"

gcloud builds submit \
  --tag "$IMAGE" \
  --project "$PROJECT_ID" \
  --config deployment/mcp/cloudbuild.yaml \
  --substitutions "_IMAGE=$IMAGE,_GIT_SHA=$SHA" \
  .

gcloud run deploy causaganha-mcp \
  --image "$IMAGE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --concurrency 4 \
  --timeout 60 \
  --port 8080
```

O timeout do runtime deve ser maior que o limite de tool call para permitir que o MCP devolva um erro classificado antes de a plataforma cortar a conexão.

## Smoke pós-deploy

Antes de divulgar uma URL, provar no mínimo:

1. `GET /health` retorna `status=ok`, commit e contagem de tools;
2. um cliente MCP novo conecta em `<SERVICE_URL>/mcp` sem checkout local;
3. `tools/list` corresponde ao catálogo canônico;
4. `processo_consultar` funciona para um CNJ de smoke conhecido;
5. uma busca de produto (`publicacoes_buscar` ou `decisoes_buscar`) retorna resposta MCP válida;
6. timeout e saturação permanecem erros, nunca `not_found`.

A URL pública e o snippet copiável do site só entram depois dessa prova.
