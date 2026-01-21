# Jules Scheduler Setup Guide

This guide helps you set up the Jules automation system for CausaGanha.

## Prerequisites

1. **Python 3.11+** installed
2. **uv** package manager installed
3. **GitHub CLI (gh)** installed (optional, for PR management)

## Environment Variables

Set up the following environment variables:

```bash
# Required for Jules API
export JULES_API_KEY="your-jules-api-key"

# Required for GitHub operations
export GITHUB_TOKEN="your-github-token"

# Required for local development
export PYTHONPATH=".team"
```

### Getting API Keys

1. **Jules API Key**: Contact Google Jules team or sign up at https://developers.google.com/jules
2. **GitHub Token**: Create a personal access token at https://github.com/settings/tokens with:
   - `repo` scope (full repository access)
   - `workflow` scope (for triggering workflows)
   - `write:packages` scope (for package operations)

## Installation

```bash
# Clone the repository
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha

# Install dependencies
uv sync --all-extras

# Verify installation
PYTHONPATH=.team uv run jules --help
```

## Testing Locally

```bash
# Run a dry-run to test the scheduler
PYTHONPATH=.team uv run jules schedule tick --dry-run

# Run a specific persona (dry-run)
PYTHONPATH=.team uv run jules schedule tick --prompt-id refactor --dry-run

# Check mail system
PYTHONPATH=.team uv run mail --help
```

## GitHub Actions Setup

The Jules scheduler runs automatically via GitHub Actions every 5 minutes.

### Required Secrets

Add these secrets to your GitHub repository (Settings > Secrets and variables > Actions):

1. `JULES_API_KEY` - Your Jules API key (required for Jules automation)
2. `GITHUB_TOKEN` - Automatically provided by GitHub Actions (no setup needed)

**Note:** If `JULES_API_KEY` is not configured, the workflow will skip Jules-related steps and display a warning message. This allows the workflow to run successfully even without the API key, making it safe to enable the workflow before obtaining a Jules API key.

### Manual Trigger

You can manually trigger the scheduler:

1. Go to Actions tab in GitHub
2. Select "Jules Scheduler" workflow
3. Click "Run workflow"
4. Choose options:
   - **prompt_id**: Run specific persona (e.g., "refactor")
   - **run_all**: Run all personas
   - **dry_run**: Don't make actual API calls
   - **reset**: Reset cycle to first persona

## Troubleshooting

### Module not found: 'repo'

Ensure `PYTHONPATH=.team` is set:

```bash
export PYTHONPATH=.team
```

### Jules API 403 Error

Check that `JULES_API_KEY` is set correctly:

```bash
echo $JULES_API_KEY
```

### GitHub CLI not found

Install GitHub CLI:

```bash
# macOS
brew install gh

# Ubuntu/Debian
sudo apt install gh

# Other systems: https://cli.github.com/manual/installation
```

## Next Steps

1. Review persona configurations in `.team/personas/`
2. Customize personas for CausaGanha-specific tasks
3. Update `.team/README.md` for project-specific documentation
4. Set up GitHub Actions secrets
5. Enable the workflow in GitHub Actions tab

## Resources

- [.team/README.md](.team/README.md) - Complete Jules system documentation
- [Jules Documentation](https://developers.google.com/jules) - Jules API reference
- [GitHub CLI](https://cli.github.com/) - GitHub CLI documentation
