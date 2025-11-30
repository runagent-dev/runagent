# Publishing `runagent-php`

The PHP SDK is distributed through Packagist (Composer's package repository). Releasing a new version requires updating the version in relevant files and publishing to Packagist.

---

## 1. Prerequisites

- PHP 8.0+ installed locally
- Composer installed
- Write access to the GitHub repository
- Packagist account with access to the package (or register the package)
- Clean working tree (`git status` should be clean or contain only staged release commits)

---

## 2. Preflight Checklist

1. **Bump the SDK version**  
   - Update `version` in `composer.json`
   - Update version in `src/Utils/Constants.php` (userAgent method)
   - Follow semver (increment patch for fixes, minor for new features, major for breaking changes)

2. **Changelog / release notes**  
   - Update `README.md` Changelog section with new version notes
   - Document breaking changes, new features, and bug fixes

3. **Verify dependencies**  
   - Run `composer install` from `runagent-php/`
   - Ensure `composer.json` contains only the needed dependencies
   - Run `composer outdated` to check for dependency updates

4. **Code quality checks**  
   - Run `composer phpstan` to check for static analysis issues
   - Fix any errors or warnings
   - Ensure all examples run correctly

---

## 3. Build & Test

```bash
# From runagent-php/
composer install

# Run static analysis
composer phpstan

# Test examples (requires valid agent credentials)
php examples/basic_example.php
php examples/local_example.php
php examples/streaming_example.php

# Validate composer.json
composer validate

# Check autoload
composer dump-autoload -o
```

---

## 4. Commit & Tag

```bash
# Stage changes
git add .

# Commit with semantic version message
git commit -m "chore(php): release v0.1.0"

# Create annotated tag with version
git tag -a runagent-php-v0.1.0 -m "Release v0.1.0"

# Push to repository
git push origin main
git push origin runagent-php-v0.1.0
```

> If releasing from a feature branch, merge it first (or push the tag from the release branch) so `main` reflects the published state.

---

## 5. Publish to Packagist

### First Time Setup

1. Go to https://packagist.org
2. Sign in with your GitHub account
3. Click "Submit" and enter your repository URL: `https://github.com/YOUR_ORG/runagent`
4. Configure auto-update webhook:
   - Go to Settings > Webhooks on GitHub
   - Add webhook: `https://packagist.org/api/github?username=YOUR_USERNAME`
   - Select "Just the push event"

### Publishing a New Version

Once the GitHub webhook is configured, Packagist automatically updates when you push a new tag.

Manually trigger an update:
1. Go to https://packagist.org/packages/runagent/runagent-php
2. Click "Update" button
3. Verify the new version appears in the versions list

---

## 6. Post-Publish

- Announce the release internally and update documentation links
- Monitor Packagist (usually available within minutes after tagging)
- Verify `composer require runagent/runagent-php` resolves to the new version:
  ```bash
  composer create-project temp-test
  cd temp-test
  composer require runagent/runagent-php
  composer show runagent/runagent-php
  ```
- Update any dependent projects or documentation

---

## 7. Troubleshooting

### Package Not Found on Packagist

- Ensure the package is submitted to Packagist
- Check that the GitHub webhook is configured correctly
- Manually trigger an update on Packagist

### Version Not Updating

- Ensure the tag was pushed to GitHub: `git push origin --tags`
- Check Packagist webhook logs on GitHub
- Manually trigger update on Packagist website

### Composer Install Fails

- Run `composer validate` to check for issues
- Ensure all required extensions are listed in composer.json
- Check that PSR-4 autoload paths are correct

### Static Analysis Errors

- Run `composer phpstan` to see all errors
- Fix errors before publishing
- Consider adding `@phpstan-ignore-line` for expected issues (use sparingly)

---

## 8. Version Format

Follow semantic versioning:
- **MAJOR**: Breaking changes (e.g., `1.0.0` → `2.0.0`)
- **MINOR**: New features, backward compatible (e.g., `0.1.0` → `0.2.0`)
- **PATCH**: Bug fixes (e.g., `0.1.0` → `0.1.1`)

Examples:
- `0.1.0` → `0.1.1` (patch: bug fix)
- `0.1.0` → `0.2.0` (minor: new feature)
- `0.1.0` → `1.0.0` (major: breaking change or stable release)

---

## 9. Pre-release Versions

For alpha/beta releases, use semantic versioning with pre-release suffix:

```bash
# Alpha release
git tag -a runagent-php-v0.2.0-alpha.1 -m "Release v0.2.0-alpha.1"

# Beta release
git tag -a runagent-php-v0.2.0-beta.1 -m "Release v0.2.0-beta.1"
```

In `composer.json`, set `minimum-stability` to `dev` or `alpha`/`beta` as needed.

---

## 10. Rollback

If a release has critical issues:

1. **Yank the release on Packagist**:
   - Go to package page on Packagist
   - Click on the problematic version
   - Click "Delete" (only works if no dependencies)

2. **Create a patch release**:
   - Fix the issue
   - Release a new patch version (e.g., `v0.1.2`)

3. **Update documentation**:
   - Add note about the problematic version
   - Recommend upgrading to the fixed version

---

## 11. Release Checklist Summary

- [ ] Update version in `composer.json`
- [ ] Update version in `src/Utils/Constants.php`
- [ ] Update `README.md` changelog
- [ ] Run `composer install`
- [ ] Run `composer phpstan`
- [ ] Run `composer validate`
- [ ] Test examples
- [ ] Commit changes: `git commit -m "chore(php): release vX.Y.Z"`
- [ ] Create tag: `git tag -a runagent-php-vX.Y.Z -m "Release vX.Y.Z"`
- [ ] Push: `git push origin main --tags`
- [ ] Verify on Packagist
- [ ] Test installation: `composer require runagent/runagent-php:^X.Y.Z`
- [ ] Announce release

---

You're done! 🚀

## Additional Notes for Packagist

### Package Naming

- Package name: `runagent/runagent-php`
- GitHub repository: Should match the package name structure

### Required Files

- `composer.json` - Package metadata and dependencies
- `README.md` - Package documentation (displayed on Packagist)
- `LICENSE` - License file (MIT recommended)

### Badge for README

Add Packagist badges to your README:

```markdown
[![Latest Stable Version](https://poser.pugx.org/runagent/runagent-php/v/stable)](https://packagist.org/packages/runagent/runagent-php)
[![Total Downloads](https://poser.pugx.org/runagent/runagent-php/downloads)](https://packagist.org/packages/runagent/runagent-php)
[![License](https://poser.pugx.org/runagent/runagent-php/license)](https://packagist.org/packages/runagent/runagent-php)
```
