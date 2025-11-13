# Publishing `runagent`

This package ships the TypeScript SDK that mirrors the RunAgent CLI/Python client. Follow these steps whenever you publish an updated build to npm.

---

## 1. Prerequisites

- npm account with publish rights to the `runagent` package.
- `npm login` already performed in your shell.
- Local environment with Node.js ≥ 18.

---

## 2. Preflight Checklist

1. **Update version**: bump `"version"` in `package.json` following semver (major/minor/patch).
2. **Changelog**: ensure release notes exist (main repository changelog, or add release notes to the docs site).
3. **Dependencies**: verify `peerDependencies` remain accurate (`ws`, `better-sqlite3` optional).

---

## 3. Build & Test

```bash
# From runagent-ts/
npm install                 # installs dev deps
npm run type-check          # TypeScript compile check
npm run build               # bundles cjs + esm + dts
```

Optional sanity checks:

```bash
npm pack                    # creates a local tarball for inspection
```

Inspect `dist/` and the pack output to confirm only the expected files are included (`runagent-client.js`, `.cjs`, `index.d.ts`, etc.).

---

## 4. Publish

The package uses the contents of the `dist/` folder that `vite build` produces.

```bash
npm publish --access public
```

> **Dry run**: add `--dry-run` if you want to verify the payload before publishing.

If two-factor auth is enabled on npm, complete the OTP prompt.

---

## 5. Post-Publish

- Tag the release in git (e.g. `git tag sdk-ts-v0.1.27 && git push origin sdk-ts-v0.1.27`).
- Notify the team / update release notes.
- Ensure docs references (CLI docs, SDK docs) point at the new version.

---

## Troubleshooting

- **`npm ERR! publish fail`**: verify you have publish rights and that the version is new (npm rejects republishing the same version).
- **Bundled `better-sqlite3`**: confirm the dependency stayed as optional peer; browser consumers should not be forced to install it.
- **Missing WebSocket support**: remind Node users to install `ws`, or include that note in the release notes if API changes require it.

---

You’re done! 🚀

