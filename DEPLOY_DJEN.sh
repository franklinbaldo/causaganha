#!/bin/bash
# ============================================================================
# DJEN PROXY - Deploy Completo
# Cole DIRETO no Google Cloud Shell
# ============================================================================

set -e

echo "🚀 DJEN PROXY - Deploy"
echo ""

# 1. Criar código Go
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

# 2. Criar Dockerfile
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

# 3. Verificar se serviço existe e perguntar se quer deletar
if gcloud run services describe djen-proxy --region southamerica-east1 &>/dev/null; then
    echo "⚠️  Serviço djen-proxy já existe"
    echo ""
    read -p "Deletar e começar do zero? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deletando serviço existente..."
        gcloud run services delete djen-proxy --region southamerica-east1 --quiet
        echo "✅ Deletado"
        echo ""
    else
        echo "ℹ️  Vai atualizar o serviço existente"
        echo ""
    fi
fi

# 4. Deploy
echo "🚀 Fazendo deploy..."
gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --max-instances 10 \
  --timeout 30s

# 5. Pegar URL
URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

# 5. Testar
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ PRONTO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "URL: $URL"
echo ""
echo "🧪 TESTANDO..."
echo ""

echo "1. Health:"
curl -s $URL/health
echo ""

echo ""
echo "2. Bloquear /evil (deve dar 403):"
curl -s $URL/evil
echo ""

echo ""
echo "3. API DJEN (deve funcionar):"
curl -s -o /dev/null -w "Status: %{http_code}" "$URL/api/v1/comunicacao?idOrgao=2"
echo ""

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Configure no CausaGanha:"
echo "   export DJEN_PROXY_URL='$URL'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
