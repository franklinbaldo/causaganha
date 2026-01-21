package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"
)

const (
	ALLOWED_TARGET = "https://comunicaapi.pje.jus.br"
	ALLOWED_HOST   = "comunicaapi.pje.jus.br"
)

// Security: Block malicious proxy usage
func securityMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Block attempts to proxy to other domains
		if strings.Contains(r.URL.Path, "http://") || strings.Contains(r.URL.Path, "https://") {
			log.Printf("🚨 BLOCKED: Attempted to proxy external URL: %s", r.URL.Path)
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"Forbidden: This proxy only serves comunicaapi.pje.jus.br"}`))
			return
		}

		// Block host header manipulation
		if r.Host != "" && !strings.Contains(r.Host, ".run.app") && r.Host != "localhost:8080" {
			log.Printf("🚨 BLOCKED: Suspicious Host header: %s", r.Host)
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"Forbidden: Invalid Host header"}`))
			return
		}

		next.ServeHTTP(w, r)
	})
}

func main() {
	target, _ := url.Parse(ALLOWED_TARGET)

	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			// Force target to be DJEN only
			req.URL.Scheme = target.Scheme
			req.URL.Host = target.Host
			req.Host = target.Host
			req.Header.Set("X-Forwarded-Host", req.Header.Get("Host"))

			log.Printf("✅ %s %s → %s%s", req.Method, req.RemoteAddr, ALLOWED_TARGET, req.URL.Path)
		},
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 100,
			IdleConnTimeout:     90 * time.Second,
			DisableCompression:  false,
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			log.Printf("❌ Proxy error: %v", err)
			w.WriteHeader(http.StatusBadGateway)
			w.Write([]byte(`{"error":"DJEN API unreachable"}`))
		},
	}

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"healthy","proxy":"djen-br-secure","region":"southamerica-east1","allowed_target":"comunicaapi.pje.jus.br"}`))
	})

	// Security info endpoint
	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{
			"security": "enabled",
			"allowed_target": "comunicaapi.pje.jus.br",
			"blocked": ["external_urls", "host_manipulation", "open_proxy_abuse"],
			"note": "This proxy ONLY serves Brazilian DJEN API"
		}`))
	})

	// Apply security middleware to proxy
	http.Handle("/", securityMiddleware(http.HandlerFunc(proxy.ServeHTTP)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("🔒 DJEN Secure Proxy rodando na porta %s", port)
	log.Printf("🇧🇷 Target: %s (LOCKED)", ALLOWED_TARGET)
	log.Printf("🛡️  Security: ENABLED")

	server := &http.Server{
		Addr:         ":" + port,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	log.Fatal(server.ListenAndServe())
}
