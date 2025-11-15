# Publishing the Rust SDK (`runagent-rust/runagent`)

Follow this checklist whenever you cut a new release of the Rust SDK.

## 1. Prerequisites

- Cargo credentials with publish rights to `runagent`.
- `cargo login <token>` already configured on the machine/CI runner.
- Clean git tree (all changes committed).

## 2. Version Bump

1. Update `version` in `runagent-rust/runagent/Cargo.toml`.
2. Update `runagent-rust/Cargo.toml` (workspace) if needed.
3. Update the version badge/examples in `runagent-rust/runagent/README.md`.

## 3. Build & Test

```bash
cd runagent-rust/runagent
cargo fmt
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
```

Optional: exercise key examples (local + remote) before publishing.

## 4. Package Audit

```bash
cargo package
```

Inspect `target/package/runagent-*.crate` (or run `cargo package --list`) to ensure only the expected files are included.

## 5. Publish

```bash
cargo publish
```

If 2FA is enabled, be ready to provide the OTP.

## 6. Post-Publish

- Tag the release: `git tag runagent-rust-vX.Y.Z && git push origin runagent-rust-vX.Y.Z`.
- Update release notes / changelog as needed.
- Ensure docs (README, SDK checklist) reflect any new behavior.

