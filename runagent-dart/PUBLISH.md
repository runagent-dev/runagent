## Publishing `runagent-dart`

The Dart SDK is distributed through pub.dev. Releasing a new version requires updating the version in `pubspec.yaml` and publishing to pub.dev.

---

### 1. Prerequisites

- Dart 3.0+ installed locally.
- Write access to the pub.dev package (or be added as an uploader).
- Clean working tree (`git status` should be clean or contain only staged release commits).
- `dart pub publish --dry-run` should pass without errors.

---

### 2. Preflight Checklist

1. **Bump the SDK version**  
   - Update `version` in `pubspec.yaml` in the root directory.  
   - Follow semver (increment patch for fixes, minor for new features, major for breaking changes).
2. **Changelog / release notes**  
   - Update the main repo changelog or docs to record the release.
3. **Verify dependencies**  
   - Run `dart pub get` from `runagent-dart/`.  
   - Ensure `pubspec.yaml` contains only the needed deps.
   - Run `dart pub outdated` to check for dependency updates.

---

### 3. Build & Test

```bash
# From runagent-dart/
dart analyze
dart test
dart pub publish --dry-run
```

For extra assurance, run the example files:

```bash
dart run example/basic_example.dart
dart run example/streaming_example.dart
dart run example/local_example.dart
```

---

### 4. Commit & Tag

```bash
git add .
git commit -m "chore(dart): release v0.1.0"

# Tag with version prefix
git tag runagent-dart-v0.1.0
git push origin main
git push origin runagent-dart-v0.1.0
```

> If releasing from a feature branch, merge it first (or push the tag from the release branch) so `main` reflects the published state.

---

### 5. Publish to pub.dev

```bash
# From runagent-dart/
dart pub publish
```

Follow the prompts to confirm publishing. You'll need to authenticate with pub.dev if not already logged in.

---

### 6. Post-Publish

- Announce the release internally and update documentation links (docs site, README tables, etc.).
- Monitor pub.dev (usually available within minutes after publishing).
- Verify `dart pub add runagent` resolves to the new version.

---

### Troubleshooting

- **`Package already exists`**: ensure the version in `pubspec.yaml` is incremented.  
- **`Upload failed`**: check your pub.dev credentials and ensure you're an uploader for the package.  
- **`Validation errors`**: run `dart pub publish --dry-run` to see what needs to be fixed.  
- **Forgot to bump version**: create a new patch release (e.g., `v0.1.1`) with the correct version.

---

### Version Format

Follow semantic versioning:
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Example: `0.1.0` → `0.1.1` (patch), `0.1.0` → `0.2.0` (minor), `0.1.0` → `1.0.0` (major)

---

You're done! 🚀

