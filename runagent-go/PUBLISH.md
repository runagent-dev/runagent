## Publishing `runagent-go`

The Go SDK is distributed through this monorepo using Go modules. Releasing a new version requires tagging the repository so `go get github.com/runagent-dev/runagent/runagent-go/runagent@vX.Y.Z` resolves to the new code.

---

### 1. Prerequisites

- Go 1.21+ installed locally.
- Write access to the repo and permission to push tags.
- Clean working tree (`git status` should be clean or contain only staged release commits).

---

### 2. Preflight Checklist

1. **Bump the SDK version**  
   - Update `runagent/runagent-go/runagent/version.go`.  
   - Follow semver (increment patch for fixes, minor for new features, major for breaking changes).
2. **Changelog / release notes**  
   - Update the main repo changelog or docs to record the release.
3. **Verify dependencies**  
   - Run `go mod tidy` from `runagent-go/`.  
   - Ensure `go.mod`/`go.sum` contain only the needed deps.

---

### 3. Build & Test

```bash
# From runagent-go/
go test ./runagent/...
golangci-lint run ./runagent/...   # optional but recommended
```

For extra assurance, run the example binaries:

```bash
go run ./examples/basic.go
go run ./examples/streaming.go
```

---

### 4. Commit & Tag

```bash
git add runagent-go
git commit -m "chore(go): release v0.1.34"

# Tag with the `sdk-go-` prefix so automation can detect it
git tag sdk-go-v0.1.34
git push origin main
git push origin sdk-go-v0.1.34
```

> If releasing from a feature branch, merge it first (or push the tag from the release branch) so `main` reflects the published state.

---

### 5. Post-Publish

- Announce the release internally and update documentation links (docs site, README tables, etc.).
- Monitor `go proxy` and `pkg.go.dev` (usually available within minutes after pushing the tag).
- Verify `go list -m github.com/runagent-dev/runagent/runagent-go/runagent@latest` resolves to the new version.

---

### Troubleshooting

- **`module lookup disabled`**: ensure the tag exists on the default branch and follows the `vX.Y.Z` semver format.  
- **Stale code from `go get`**: run `GONOSUMDB=* GOPROXY=direct go list -m github.com/...@latest` to force a refresh.  
- **Forgot to bump version**: retagging is not supported; create a new patch release (e.g., `v0.1.35`) with the correct version.

---

You’re done! 🚀

