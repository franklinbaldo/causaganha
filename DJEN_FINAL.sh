#!/bin/bash
# ============================================================================
# DJEN PROXY - SOLUÇÃO FINAL
# Copie e cole TUDO no Google Cloud Shell
# ============================================================================

set -e

cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 DJEN PROXY - Setup do Zero
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

# 1. CRIAR CÓDIGO GO
echo ""
echo "📝 Criando djen_proxy.go..."
cat > djen_proxy.go << 'GOCODE'
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

const TARGET = "https://comunicaapi.pje.jus.br"

var WHITELIST = []string{"/api/", "/swagger/", "/comunicacao", "/login"}

func allowed(path string) bool {
	if path == "/" || path == "/health" || path == "/security" {
		return true
	}
	for _, p := range WHITELIST {
		if strings.HasPrefix(path, p) {
			return true
		}
	}
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
	proxy := &httputil.ReverseProxy{
		Director: func(r *http.Request) {
			r.URL.Scheme = target.Scheme
			r.URL.Host = target.Host
			r.Host = target.Host
		},
		Transport: &http.Transport{MaxIdleConns: 100, IdleConnTimeout: 90 * time.Second},
	}

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"status":"ok"}`))
	})

	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"whitelist":["/api/","/swagger/","/comunicacao","/login"]}`))
	})

	http.Handle("/", security(http.HandlerFunc(proxy.ServeHTTP)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("🔒 Proxy: %s", port)
	http.ListenAndServe(":"+port, nil)
}
GOCODE

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

# 3. TESTE LOCAL
cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTE LOCAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

go build -o djen_proxy djen_proxy.go
PORT=8888 ./djen_proxy &> /tmp/proxy.log &
PID=$!
sleep 2

echo ""
echo "1. Health: $(curl -s http://localhost:8888/health)"
echo "2. Malicious: $(curl -s -w '%{http_code}' http://localhost:8888/evil)"
echo "3. Whitelist: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8888/api/v1/test)"

kill $PID 2>/dev/null
echo ""

# 4. CONFIRMAR DEPLOY
cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

# Verificar se serviço já existe
if gcloud run services describe djen-proxy --region southamerica-east1 &>/dev/null; then
    echo "⚠️  Serviço djen-proxy já existe"
    read -p "Deletar e começar do zero? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deletando serviço existente..."
        gcloud run services delete djen-proxy --region southamerica-east1 --quiet
        echo "✅ Deletado"
    else
        echo "ℹ️  Vai atualizar o serviço existente"
    fi
    echo ""
fi

read -p "Deploy? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelado"
    exit 0
fi

# 5. DEPLOY
cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 DEPLOY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --max-instances 10 \
  --timeout 30s \
  --quiet

URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

echo ""
cat << EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PRONTO!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

URL: $URL

Teste:
  curl $URL/health
  curl $URL/evil  (deve dar 403)

Configure:
  export DJEN_PROXY_URL='$URL'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
