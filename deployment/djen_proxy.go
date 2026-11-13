package main

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"regexp"
	"strings"
	"time"
)

const TARGET = "https://comunicaapi.pje.jus.br"
const ARCHIVE_UPSTREAM = "https://archive.org"

// WHITELIST is the only path prefix this proxy forwards to the DJEN
// backend. web/src/lib/djenClient.ts documents that all 7 generated spec
// endpoints (openapi/djen.yml) live under /api/v1/ — /swagger/, bare
// /comunicacao and /login are unused by any caller in this repo (TM-02,
// issue #1609) and are dropped rather than kept "just in case".
var WHITELIST = []string{"/api/"}

// ALLOWED_METHODS is the only HTTP method this proxy forwards to the DJEN backend.
var ALLOWED_METHODS = map[string]bool{http.MethodGet: true}

// ARCHIVE_DOWNLOAD_RE matches narrow Internet Archive Parquet download paths
// (/download/{item}/{file}.parquet for djen-*, datajud-*, tjro-juris-*, or
// causaganha-* items), mirroring deployment/archive-cors-proxy/src/index.js
// (issue #1482) so DuckDB-WASM httpfs can perform CORS + HTTP Range reads.
var ARCHIVE_DOWNLOAD_RE = regexp.MustCompile(`^/download/((?:djen|datajud|tjro-juris|causaganha)-[a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+\.parquet)$`)

var ARCHIVE_STRIP_HEADERS = map[string]bool{
	"connection":        true,
	"content-length":    true,
	"keep-alive":        true,
	"transfer-encoding": true,
	"upgrade":           true,
}

func setArchiveCorsHeaders(h http.Header) {
	h.Set("Access-Control-Allow-Origin", "*")
	h.Set("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
	h.Set("Access-Control-Allow-Headers", "Range, If-Range")
	h.Set("Access-Control-Expose-Headers", "Accept-Ranges, Content-Range, Content-Length, Content-Type, ETag")
	h.Set("Access-Control-Max-Age", "86400")
}

func isArchiveDownloadPath(path string) bool {
	return ARCHIVE_DOWNLOAD_RE.MatchString(path)
}

func handleArchiveDownload(client *http.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodOptions {
			setArchiveCorsHeaders(w.Header())
			w.WriteHeader(http.StatusNoContent)
			return
		}
		if r.Method != http.MethodGet && r.Method != http.MethodHead {
			setArchiveCorsHeaders(w.Header())
			w.Header().Set("Allow", "GET, HEAD, OPTIONS")
			w.Header().Set("Content-Type", "text/plain; charset=utf-8")
			w.WriteHeader(http.StatusMethodNotAllowed)
			w.Write([]byte("method not allowed"))
			return
		}
		matches := ARCHIVE_DOWNLOAD_RE.FindStringSubmatch(r.URL.Path)
		if matches == nil {
			setArchiveCorsHeaders(w.Header())
			w.Header().Set("Content-Type", "text/plain; charset=utf-8")
			w.WriteHeader(http.StatusNotFound)
			w.Write([]byte("not found"))
			return
		}

		upstreamURL := fmt.Sprintf("%s/download/%s/%s", ARCHIVE_UPSTREAM, matches[1], matches[2])
		req, err := http.NewRequestWithContext(r.Context(), r.Method, upstreamURL, nil)
		if err != nil {
			setArchiveCorsHeaders(w.Header())
			w.WriteHeader(http.StatusBadGateway)
			w.Write([]byte("upstream error"))
			return
		}
		if rng := r.Header.Get("Range"); rng != "" {
			req.Header.Set("Range", rng)
		}

		resp, err := client.Do(req)
		if err != nil {
			log.Printf("🚨 ARCHIVE UPSTREAM ERROR: %v", err)
			setArchiveCorsHeaders(w.Header())
			w.WriteHeader(http.StatusBadGateway)
			w.Write([]byte("upstream error"))
			return
		}
		defer resp.Body.Close()

		for k, vals := range resp.Header {
			if ARCHIVE_STRIP_HEADERS[strings.ToLower(k)] {
				continue
			}
			for _, v := range vals {
				w.Header().Add(k, v)
			}
		}
		setArchiveCorsHeaders(w.Header())
		w.Header().Set("Cache-Control", "public, max-age=3600")
		w.WriteHeader(resp.StatusCode)
		if r.Method != http.MethodHead {
			io.Copy(w, resp.Body)
		}
	}
}

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
	archiveClient := &http.Client{
		Timeout: 60 * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:    100,
			IdleConnTimeout: 90 * time.Second,
		},
	}
	archiveHandler := handleArchiveDownload(archiveClient)

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/download/") {
			archiveHandler.ServeHTTP(w, r)
			return
		}
		if !ALLOWED_METHODS[r.Method] {
			log.Printf("🚨 BLOCKED METHOD: %s %s", r.Method, r.URL.Path)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(405)
			w.Write([]byte(fmt.Sprintf(`{"error":"method not allowed","method":"%s"}`, r.Method)))
			return
		}
		if !allowed(r.URL.Path) {
			log.Printf("🚨 BLOCKED: %s", r.URL.Path)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(403)
			w.Write([]byte(fmt.Sprintf(`{"error":"forbidden","path":"%s"}`, r.URL.Path)))
			return
		}
		log.Printf("✅ ALLOWED: %s", r.URL.Path)
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
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) })
	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"whitelist":["/api/","/download/"],"methods":["GET","HEAD","OPTIONS"]}`))
	})
	http.Handle("/", security(http.HandlerFunc(proxy.ServeHTTP)))
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("🔒 Proxy: %s", port)
	http.ListenAndServe(":"+port, nil)
}
