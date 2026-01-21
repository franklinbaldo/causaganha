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

// Middleware de segurança com logging detalhado
func securityMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Log completo do request
		log.Printf("📥 REQUEST: Method=%s Path=%s RawPath=%s RequestURI=%s",
			r.Method, r.URL.Path, r.URL.RawPath, r.RequestURI)

		// Bloquear URLs externas no path
		if strings.Contains(r.URL.Path, "http://") || strings.Contains(r.URL.Path, "https://") {
			log.Printf("🚨 BLOCKED: External URL in Path: %s from %s", r.URL.Path, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"Forbidden: DJEN only","blocked":"external_url","path":"` + r.URL.Path + `"}`))
			return
		}

		// Também checar RequestURI
		if strings.Contains(r.RequestURI, "http://") || strings.Contains(r.RequestURI, "https://") {
			log.Printf("🚨 BLOCKED: External URL in RequestURI: %s from %s", r.RequestURI, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"Forbidden: DJEN only","blocked":"external_url","uri":"` + r.RequestURI + `"}`))
			return
		}

		next.ServeHTTP(w, r)
	})
}

func main() {
	target, _ := url.Parse(ALLOWED_TARGET)

	// Criar reverse proxy
	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = target.Scheme
			req.URL.Host = target.Host
			req.Host = target.Host
			log.Printf("✅ Proxying: %s %s → %s%s", req.Method, req.RemoteAddr, ALLOWED_TARGET, req.URL.Path)
		},
		Transport: &http.Transport{
			MaxIdleConns:    100,
			IdleConnTimeout: 90 * time.Second,
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			log.Printf("❌ Proxy error: %v", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadGateway)
			w.Write([]byte(`{"error":"DJEN API unreachable"}`))
		},
	}

	// Debug endpoint - mostra o que foi recebido
	http.HandleFunc("/debug", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		debug := fmt.Sprintf(`{
			"method": "%s",
			"path": "%s",
			"raw_path": "%s",
			"request_uri": "%s",
			"host": "%s",
			"remote_addr": "%s"
		}`, r.Method, r.URL.Path, r.URL.RawPath, r.RequestURI, r.Host, r.RemoteAddr)
		w.Write([]byte(debug))
	})

	// Health check endpoint
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"healthy","secure":"true","version":"debug-enabled"}`))
	})

	// Security info endpoint
	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"security":"enabled","allowed_target":"comunicaapi.pje.jus.br","debug":"/debug"}`))
	})

	// Apply security middleware to all proxy requests
	http.Handle("/", securityMiddleware(http.HandlerFunc(proxy.ServeHTTP)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("🔒 DJEN Secure Proxy (DEBUG MODE) starting on port %s", port)
	log.Printf("🇧🇷 Target: %s (LOCKED)", ALLOWED_TARGET)
	log.Printf("🛡️  Security: ENABLED with detailed logging")
	log.Printf("🐛 Debug endpoint: /debug")

	server := &http.Server{
		Addr:         ":" + port,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	log.Fatal(server.ListenAndServe())
}
