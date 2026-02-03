# Publishing Guide for RunAgent C# SDK

This guide covers the process of publishing new versions of the RunAgent C# SDK to NuGet.

## Prerequisites

1. **NuGet Account**: Create an account at [nuget.org](https://www.nuget.org/)
2. **API Key**: Generate an API key from your NuGet account settings
3. **.NET SDK**: Install .NET SDK 6.0 or higher
4. **Repository Access**: Write access to the runagent-csharp repository

## Version Bump Checklist

Before publishing a new version:

- [ ] Update version number in `RunAgent.csproj`
- [ ] Update version in examples (if referencing version)
- [ ] Update `CHANGELOG.md` with new version and changes
- [ ] Update README if there are API changes or new features
- [ ] Run all tests and ensure they pass
- [ ] Build the project in Release mode
- [ ] Review changes in PR before merging to main

## Build and Test

### 1. Clean and Restore

```bash
dotnet clean
dotnet restore
```

### 2. Build in Release Mode

```bash
dotnet build --configuration Release
```

### 3. Run Tests (when available)

```bash
dotnet test --configuration Release
```

### 4. Create NuGet Package

```bash
dotnet pack --configuration Release --output ./nupkg
```

This creates a `.nupkg` file in the `./nupkg` directory.

## Publishing to NuGet

### Option 1: Using dotnet CLI

1. **Set API Key** (first time only):
   ```bash
   dotnet nuget push --help
   ```

2. **Push Package**:
   ```bash
   dotnet nuget push ./nupkg/RunAgent.0.1.47.nupkg --api-key YOUR_API_KEY --source https://api.nuget.org/v3/index.json
   ```

### Option 2: Using NuGet.org Web Interface

1. Go to [nuget.org/packages/manage/upload](https://www.nuget.org/packages/manage/upload)
2. Upload the `.nupkg` file from `./nupkg` directory
3. Review and publish

## Post-Publication

After publishing:

1. **Verify Package**: Check that the package appears at https://www.nuget.org/packages/RunAgent
2. **Test Installation**: Install the package in a test project:
   ```bash
   dotnet new console -n TestRunAgent
   cd TestRunAgent
   dotnet add package RunAgent
   ```
3. **Tag Release**: Create a git tag for the version:
   ```bash
   git tag -a v0.1.47 -m "Release version 0.1.47"
   git push origin v0.1.47
   ```
4. **Create GitHub Release**: Create a release on GitHub with changelog notes
5. **Update Documentation**: Update docs.run-agent.ai if needed
6. **Announce**: Share update on Discord, social media, etc.

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version (X.0.0): Breaking changes
- **MINOR** version (0.X.0): New features, backward compatible
- **PATCH** version (0.0.X): Bug fixes, backward compatible

### Examples:
- `0.1.47` → `0.1.48`: Bug fix or small improvement
- `0.1.47` → `0.2.0`: New feature added
- `0.1.47` → `1.0.0`: Breaking API change or first stable release

## Troubleshooting

### Package Push Fails

**Error**: "The package already exists"

**Solution**: Increment version number - NuGet doesn't allow overwriting published versions

### Build Errors

**Error**: Missing dependencies

**Solution**: Run `dotnet restore` and ensure all dependencies are available

### API Key Issues

**Error**: "The API key is invalid"

**Solution**:
1. Verify API key is correct
2. Check API key has push permissions
3. Regenerate API key if needed

## Release Checklist

Complete checklist before publishing:

- [ ] Version bumped in `.csproj`
- [ ] CHANGELOG updated
- [ ] README updated (if needed)
- [ ] All tests passing
- [ ] Build succeeds in Release mode
- [ ] Package created successfully
- [ ] Package pushed to NuGet
- [ ] Installation tested
- [ ] Git tag created
- [ ] GitHub release created
- [ ] Documentation updated
- [ ] Announcement made

## Contact

For questions about publishing:
- **Discord**: [RunAgent Community](https://discord.gg/Q9P9AdHVHz)
- **Email**: team@run-agent.ai
- **GitHub Issues**: [runagent-csharp/issues](https://github.com/runagent-dev/runagent-csharp/issues)
