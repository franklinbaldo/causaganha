GOTOOLCHAIN ?= go1.26.3

.PHONY: build test lint install clean

build:
	GOTOOLCHAIN=$(GOTOOLCHAIN) go build -o bin/djen-pp-cli ./cmd/djen-pp-cli

test:
	GOTOOLCHAIN=$(GOTOOLCHAIN) go test ./...

lint:
	golangci-lint run

install:
	GOTOOLCHAIN=$(GOTOOLCHAIN) go install ./cmd/djen-pp-cli

clean:
	rm -rf bin/

build-mcp:
	GOTOOLCHAIN=$(GOTOOLCHAIN) go build -o bin/djen-pp-mcp ./cmd/djen-pp-mcp

install-mcp:
	GOTOOLCHAIN=$(GOTOOLCHAIN) go install ./cmd/djen-pp-mcp

build-all: build build-mcp
