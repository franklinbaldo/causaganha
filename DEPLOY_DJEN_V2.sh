#!/bin/bash
# ============================================================================
# DJEN PROXY - Deploy Script
# VERSÃO: v2.0 (2026-01-21 17:30 UTC)
# ============================================================================

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 DJEN PROXY - Deploy Script"
echo "📌 VERSÃO: v2.0 (2026-01-21 17:30)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. CRIAR CÓDIGO GO
echo "📝 Criando djen_proxy.go..."
cat > djen_proxy.go << 'GO'
package main
import ("fmt";"log";"net/http";"net/http/httputil";"net/url";"os";"strings";"time")
const TARGET = "https://comunicaapi.pje.jus.br"
var WHITELIST = []string{"/api/", "/swagger/", "/comunicacao", "/login"}
func allowed(path string) bool {
	if path == "/" || path == "/health" || path == "/security" { return true }
	for _, p := range WHITELIST { if strings.HasPrefix(path, p) { return true } }
	return false
}
func security(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !allowed(r.URL.Path) {
			log.Printf("🚨 BLOCKED: %s", r.URL.Path)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(403)
			w.Write([]byte(fmt.Sprintf(`{"error":"forbidden","path":"%s"}`, r.URL.Path)))
			return
		}
		next.ServeHTTP(w, r)
	})
}
func main() {
	target, _ := url.Parse(TARGET)
	proxy := &httputil.ReverseProxy{Director: func(r *http.Request) { r.URL.Scheme = target.Scheme; r.URL.Host = target.Host; r.Host = target.Host }, Transport: &http.Transport{MaxIdleConns: 100, IdleConnTimeout: 90 * time.Second}}
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) })
	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"whitelist":["/api/","/swagger/","/comunicacao","/login"]}`)) })
	http.Handle("/", security(http.HandlerFunc(proxy.ServeHTTP)))
	port := os.Getenv("PORT"); if port == "" { port = "8080" }
	log.Printf("🔒 Proxy: %s", port)
	http.ListenAndServe(":"+port, nil)
}
GO

# 2. CRIAR DOCKERFILE
echo "📝 Criando Dockerfile..."
cat > Dockerfile << 'DOCKER'
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY djen_proxy.go .
RUN go build -o djen_proxy djen_proxy.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/djen_proxy .
EXPOSE 8080
CMD ["./djen_proxy"]
DOCKER

echo "✅ Arquivos criados"
echo ""

# 3. VERIFICAR SE SERVIÇO EXISTE
if gcloud run services describe djen-proxy --region southamerica-east1 &>/dev/null; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  SERVIÇO JÁ EXISTE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    read -p "Deletar e começar do zero? (y/n): " -n 1 -r
    echo ""
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deletando serviço existente..."
        gcloud run services delete djen-proxy --region southamerica-east1 --quiet
        echo "✅ Deletado com sucesso"
        echo ""
    else
        echo "ℹ️  Atualizando serviço existente (não deletou)"
        echo ""
    fi
fi

# 4. DEPLOY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 FAZENDO DEPLOY NO CLOUD RUN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --max-instances 10 \
  --timeout 30s

# 5. PEGAR URL
URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

# 6. TESTAR
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOY CONCLUÍDO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 URL: $URL"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TESTANDO PROXY..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "1️⃣ Health endpoint:"
curl -s $URL/health
echo ""

echo ""
echo "2️⃣ Bloqueio de path malicioso (/evil):"
curl -s $URL/evil
echo ""

echo ""
echo "3️⃣ API DJEN (whitelist):"
curl -s -o /dev/null -w "Status HTTP: %{http_code}" "$URL/api/v1/comunicacao?idOrgao=2"
echo ""

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 CONFIGURAÇÃO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Copie e cole no terminal do CausaGanha:"
echo ""
echo "  export DJEN_PROXY_URL='$URL'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CONCLUÍDO - v2.0"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
