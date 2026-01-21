package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"syscall"
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
			log.Printf("🚨 BLOCKED: %s from %s", r.URL.Path, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(fmt.Sprintf(`{"error":"forbidden","path":"%s"}`, r.URL.Path)))
			return
		}
		next.ServeHTTP(w, r)
	})
}

func main() {
	target, err := url.Parse(TARGET)
	if err != nil {
		log.Fatalf("❌ Invalid target URL: %v", err)
	}

	// Create reverse proxy
	proxy := &httputil.ReverseProxy{
		Director: func(r *http.Request) {
			r.URL.Scheme = target.Scheme
			r.URL.Host = target.Host
			r.Host = target.Host
		},
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 100,
			IdleConnTimeout:     90 * time.Second,
		},
	}

	// Setup routes
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"ok","version":"v3.1"}`))
	})

	mux.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"whitelist":["/api/","/swagger/","/comunicacao","/login"],"version":"v3.1"}`))
	})

	mux.Handle("/", security(http.HandlerFunc(proxy.ServeHTTP)))

	// Get port
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	// Create server
	server := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Setup graceful shutdown
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// Start server in goroutine
	go func() {
		log.Printf("🔒 DJEN Proxy v3.1 starting on :%s", port)
		log.Printf("🛡️  Whitelist: %v", WHITELIST)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("❌ Server error: %v", err)
		}
	}()

	// Wait for interrupt signal
	<-ctx.Done()

	// Graceful shutdown
	log.Println("🛑 Shutdown signal received, gracefully shutting down...")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("❌ Shutdown error: %v", err)
	} else {
		log.Println("✅ Server stopped gracefully")
	}
}
