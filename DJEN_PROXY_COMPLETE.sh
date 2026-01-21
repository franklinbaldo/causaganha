#!/bin/bash
# ============================================================================
# DJEN PROXY COMPLETO - Testa local primeiro, depois deploy
# Cole TUDO isso no Google Cloud Shell
# ============================================================================

set -e

echo "🚀 DJEN PROXY - Setup Completo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Criar Dockerfile
echo "📝 Criando Dockerfile..."
cat > Dockerfile << 'DOCKERFILE_END'
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
DOCKERFILE_END

# 2. Criar código Go seguro
echo "📝 Criando djen_proxy.go..."
cat > djen_proxy.go << 'GO_END'
package main

import (
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"
)

const ALLOWED_TARGET = "https://comunicaapi.pje.jus.br"

func securityMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		uri := r.RequestURI

		log.Printf("📥 Request: path=%s uri=%s", path, uri)

		// Bloquear URLs externas no path OU no URI
		if strings.Contains(path, "http://") || strings.Contains(path, "https://") ||
		   strings.Contains(uri, "http://") || strings.Contains(uri, "https://") {
			log.Printf("🚨 BLOCKED: path=%s uri=%s", path, uri)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(fmt.Sprintf(`{"error":"Forbidden: DJEN only","blocked_path":"%s","blocked_uri":"%s"}`, path, uri)))
			return
		}

		next.ServeHTTP(w, r)
	})
}

func main() {
	target, _ := url.Parse(ALLOWED_TARGET)

	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = target.Scheme
			req.URL.Host = target.Host
			req.Host = target.Host
			log.Printf("✅ Proxy: %s", req.URL.Path)
		},
		Transport: &http.Transport{MaxIdleConns: 100, IdleConnTimeout: 90 * time.Second},
	}

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"healthy","secure":"true","version":"v2"}`))
	})

	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"security":"enabled","target":"comunicaapi.pje.jus.br","blocks":["external_urls"]}`))
	})

	http.HandleFunc("/debug", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(fmt.Sprintf(`{"path":"%s","uri":"%s","host":"%s"}`, r.URL.Path, r.RequestURI, r.Host)))
	})

	http.Handle("/", securityMiddleware(http.HandlerFunc(proxy.ServeHTTP)))

	port := os.Getenv("PORT")
	if port == "" { port = "8080" }

	log.Printf("🔒 DJEN Proxy: localhost:%s", port)
	http.ListenAndServe(":"+port, nil)
}
GO_END

echo "✅ Arquivos criados"
echo ""

# 3. TESTAR LOCALMENTE PRIMEIRO
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 FASE 1: TESTE LOCAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Compilando e rodando localmente..."

# Compilar
go build -o djen_proxy djen_proxy.go

# Rodar em background
PORT=8888 ./djen_proxy > /tmp/djen_proxy.log 2>&1 &
PID=$!
echo "✅ Proxy rodando local no PID $PID (porta 8888)"

# Aguardar iniciar
sleep 2

# Testar localmente
echo ""
echo "📊 Testes locais:"
echo ""

echo "1️⃣ Health check:"
curl -s http://localhost:8888/health
echo ""

echo ""
echo "2️⃣ Security info:"
curl -s http://localhost:8888/security
echo ""

echo ""
echo "3️⃣ Debug endpoint:"
curl -s http://localhost:8888/debug
echo ""

echo ""
echo "4️⃣ Tentar bloquear http://google.com (deve retornar 403):"
HTTP_CODE=$(curl -s -o /tmp/test.txt -w "%{http_code}" http://localhost:8888/http://google.com)
echo "Status: $HTTP_CODE"
cat /tmp/test.txt
echo ""

if [ "$HTTP_CODE" == "403" ]; then
    echo "✅ BLOQUEIO FUNCIONOU LOCALMENTE!"
else
    echo "❌ BLOQUEIO FALHOU! Status: $HTTP_CODE (esperado 403)"
    echo ""
    echo "Ver logs:"
    cat /tmp/djen_proxy.log
    kill $PID
    exit 1
fi

echo ""
echo "5️⃣ API DJEN legítima (deve funcionar):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8888/api/v1/comunicacao?idOrgao=2")
echo "Status: $HTTP_CODE"

# Matar processo local
kill $PID
echo ""
echo "✅ Testes locais PASSARAM!"
echo ""

# 4. PERGUNTAR SE QUER FAZER DEPLOY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "🚀 Deploy no Cloud Run? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deploy cancelado pelo usuário"
    exit 0
fi

# 5. FAZER DEPLOY
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 FASE 2: DEPLOY NO CLOUD RUN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --max-instances 10 \
  --timeout 30s \
  --concurrency 80 \
  --quiet

PROXY_URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

echo ""
echo "✅ Deploy concluído!"
echo ""

# 6. TESTAR NO CLOUD RUN
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 FASE 3: TESTE NO CLOUD RUN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "URL: $PROXY_URL"
echo ""

echo "Aguardando 10s para propagação..."
sleep 10

echo ""
echo "1️⃣ Health check:"
curl -s $PROXY_URL/health
echo ""

echo ""
echo "2️⃣ Debug endpoint:"
curl -s $PROXY_URL/debug
echo ""

echo ""
echo "3️⃣ Bloquear http://google.com:"
HTTP_CODE=$(curl -s -o /tmp/cloud_test.txt -w "%{http_code}" "$PROXY_URL/http://google.com")
echo "Status: $HTTP_CODE"
cat /tmp/cloud_test.txt
echo ""

if [ "$HTTP_CODE" == "403" ]; then
    echo "✅ BLOQUEIO FUNCIONOU NO CLOUD RUN!"
else
    echo "❌ BLOQUEIO FALHOU NO CLOUD RUN!"
    echo ""
    echo "Ver logs do Cloud Run:"
    gcloud run services logs read djen-proxy --region southamerica-east1 --limit 30
fi

echo ""
echo "4️⃣ API DJEN legítima:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_URL/api/v1/comunicacao?idOrgao=2")
echo "Status: $HTTP_CODE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CONCLUÍDO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔒 URL do Proxy: $PROXY_URL"
echo ""
echo "📝 Configure no CausaGanha:"
echo "   export DJEN_PROXY_URL='$PROXY_URL'"
echo ""
echo "📊 Ver logs:"
echo "   gcloud run services logs read djen-proxy --region southamerica-east1"
echo ""
