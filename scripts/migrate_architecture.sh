#!/bin/bash
set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${GREEN}==>${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Must be run from repository root"
    exit 1
fi

# Ask for confirmation
echo "This script will migrate CausaGanha architecture from v2/ to unified structure."
echo "It will:"
echo "  1. Remove embedding duplications"
echo "  2. Move v2/ modules to root"
echo "  3. Move infrastructure/clients to clients/"
echo "  4. Move domain/scoring to scoring/"
echo "  5. Archive legacy code to legacy_archive/"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Create backup branch
BACKUP_BRANCH="backup/pre-unification-$(date +%Y%m%d-%H%M%S)"
print_step "Creating backup branch: $BACKUP_BRANCH"
git checkout -b "$BACKUP_BRANCH"
git checkout -

# ============================================================
# PHASE 1: Remove Embedding Duplications
# ============================================================
print_step "PHASE 1: Removing embedding duplications..."

if [ -f "src/causaganha/v2/analysis/embedding_service.py" ]; then
    print_step "Removing embedding_service.py (redirect)"
    git rm src/causaganha/v2/analysis/embedding_service.py
fi

if [ -f "src/causaganha/v2/analysis/embedding_providers.py" ]; then
    print_step "Removing embedding_providers.py (redirect)"
    git rm src/causaganha/v2/analysis/embedding_providers.py
fi

if [ -f "src/causaganha/v2/analysis/embedding_service_v2.py" ]; then
    print_step "Renaming embedding_service_v2.py → embedding_service.py"
    git mv src/causaganha/v2/analysis/embedding_service_v2.py \
           src/causaganha/v2/analysis/embedding_service.py
fi

print_step "Updating imports in v2/..."
find src/causaganha/v2 -name "*.py" -type f -exec sed -i \
    's/from causaganha.v2.analysis.embedding_service_v2/from causaganha.v2.analysis.embedding_service/g' {} +

git add -A
git commit -m "refactor: remove embedding duplications (service_v2, providers redirect)" || true

print_step "Phase 1 complete ✓"

# ============================================================
# PHASE 2: Create Unified Structure
# ============================================================
print_step "PHASE 2: Creating unified structure directories..."

mkdir -p src/causaganha/cli/commands
mkdir -p src/causaganha/clients
mkdir -p src/causaganha/scoring
mkdir -p src/causaganha/models

touch src/causaganha/cli/__init__.py
touch src/causaganha/cli/commands/__init__.py
touch src/causaganha/clients/__init__.py
touch src/causaganha/scoring/__init__.py
touch src/causaganha/models/__init__.py

git add src/causaganha/cli
git add src/causaganha/clients/__init__.py
git add src/causaganha/scoring/__init__.py
git add src/causaganha/models/__init__.py
git commit -m "refactor: create unified structure directories" || true

print_step "Phase 2 complete ✓"

# ============================================================
# PHASE 3: Move v2/ to Root
# ============================================================
print_step "PHASE 3: Moving v2/ modules to root..."

# Move modules
if [ -d "src/causaganha/v2/api" ]; then
    git mv src/causaganha/v2/api src/causaganha/api
fi

if [ -d "src/causaganha/v2/analysis" ]; then
    git mv src/causaganha/v2/analysis src/causaganha/analysis
fi

if [ -d "src/causaganha/v2/pipeline" ]; then
    git mv src/causaganha/v2/pipeline src/causaganha/pipeline
fi

if [ -d "src/causaganha/v2/storage" ]; then
    git mv src/causaganha/v2/storage src/causaganha/storage
fi

if [ -d "src/causaganha/v2/utils" ] && [ "$(ls -A src/causaganha/v2/utils)" ]; then
    # Only move if not empty
    git mv src/causaganha/v2/utils/* src/causaganha/utils/ 2>/dev/null || true
fi

# Remove empty v2 directory
if [ -d "src/causaganha/v2" ]; then
    rmdir src/causaganha/v2 2>/dev/null || git rm -rf src/causaganha/v2
fi

git commit -m "refactor: move v2/ modules to causaganha/ root" || true

print_step "Updating imports from v2.* to causaganha.*..."

# Update imports in src/
find src/causaganha -name "*.py" -type f -exec sed -i \
    's/from causaganha\.v2\./from causaganha./g' {} +

find src/causaganha -name "*.py" -type f -exec sed -i \
    's/import causaganha\.v2\./import causaganha./g' {} +

# Update imports in tests/
find tests -name "*.py" -type f -exec sed -i \
    's/from causaganha\.v2\./from causaganha./g' {} +

find tests -name "*.py" -type f -exec sed -i \
    's/import causaganha\.v2\./import causaganha./g' {} +

git add -A
git commit -m "refactor: update imports from v2.* to causaganha.*" || true

print_step "Phase 3 complete ✓"

# ============================================================
# PHASE 4: Move infrastructure/clients and domain/scoring
# ============================================================
print_step "PHASE 4: Moving infrastructure/clients and domain/scoring..."

# Move infrastructure/clients
if [ -d "src/causaganha/infrastructure/clients" ]; then
    print_step "Moving infrastructure/clients/ → clients/"

    if [ -f "src/causaganha/infrastructure/clients/archive.py" ]; then
        git mv src/causaganha/infrastructure/clients/archive.py src/causaganha/clients/
    fi

    if [ -f "src/causaganha/infrastructure/clients/document.py" ]; then
        git mv src/causaganha/infrastructure/clients/document.py src/causaganha/clients/
    fi

    if [ -f "src/causaganha/infrastructure/clients/preservation.py" ]; then
        git mv src/causaganha/infrastructure/clients/preservation.py src/causaganha/clients/
    fi

    if [ -f "src/causaganha/infrastructure/clients/constants.py" ]; then
        git mv src/causaganha/infrastructure/clients/constants.py src/causaganha/clients/
    fi

    git commit -m "refactor: move infrastructure/clients to clients/" || true
fi

# Move domain/scoring
if [ -d "src/causaganha/domain/scoring" ]; then
    print_step "Moving domain/scoring/ → scoring/"
    git mv src/causaganha/domain/scoring/openskill.py src/causaganha/scoring/
    git commit -m "refactor: move domain/scoring to scoring/" || true
fi

# Update imports
print_step "Updating imports from infrastructure.clients and domain.scoring..."

find src/causaganha tests -name "*.py" -type f -exec sed -i \
    's/from causaganha\.infrastructure\.clients/from causaganha.clients/g' {} +

find src/causaganha tests -name "*.py" -type f -exec sed -i \
    's/from causaganha\.domain\.scoring/from causaganha.scoring/g' {} +

git add -A
git commit -m "refactor: update imports to new clients/ and scoring/" || true

print_step "Phase 4 complete ✓"

# ============================================================
# PHASE 5: Archive Legacy Code
# ============================================================
print_step "PHASE 5: Archiving legacy code..."

mkdir -p legacy_archive

# Move legacy directories
if [ -d "src/causaganha/application" ]; then
    git mv src/causaganha/application legacy_archive/
    print_step "Archived application/"
fi

if [ -d "src/causaganha/infrastructure" ]; then
    git mv src/causaganha/infrastructure legacy_archive/
    print_step "Archived infrastructure/"
fi

if [ -d "src/causaganha/domain" ]; then
    git mv src/causaganha/domain legacy_archive/
    print_step "Archived domain/"
fi

if [ -d "src/causaganha/ml" ]; then
    git mv src/causaganha/ml legacy_archive/
    print_step "Archived ml/"
fi

if [ -d "src/causaganha/schemas" ]; then
    git mv src/causaganha/schemas legacy_archive/
    print_step "Archived schemas/"
fi

if [ -d "src/causaganha/validation" ]; then
    git mv src/causaganha/validation legacy_archive/
    print_step "Archived validation/"
fi

git commit -m "refactor: archive legacy code to legacy_archive/" || true

print_step "Phase 5 complete ✓"

# ============================================================
# FINAL VALIDATION
# ============================================================
print_step "Running validation checks..."

# Check for remaining v2 imports
if grep -r "from causaganha\.v2" src/causaganha --include="*.py" 2>/dev/null; then
    print_warning "Found remaining v2 imports in src/"
else
    print_step "✓ No v2 imports in src/"
fi

# Check for remaining infrastructure.clients imports
if grep -r "from causaganha\.infrastructure\.clients" src/causaganha --include="*.py" 2>/dev/null; then
    print_warning "Found remaining infrastructure.clients imports"
else
    print_step "✓ No infrastructure.clients imports in src/"
fi

# Check for remaining domain.scoring imports
if grep -r "from causaganha\.domain\.scoring" src/causaganha --include="*.py" 2>/dev/null; then
    print_warning "Found remaining domain.scoring imports"
else
    print_step "✓ No domain.scoring imports in src/"
fi

# Show new structure
print_step "New structure:"
tree -L 2 -d src/causaganha 2>/dev/null || ls -la src/causaganha

echo ""
print_step "Migration complete! ✓"
echo ""
echo "Next steps:"
echo "  1. Run tests: pytest tests/v2/ -v"
echo "  2. Test CLI: uv run causaganha --help"
echo "  3. Review changes: git diff $BACKUP_BRANCH"
echo "  4. If all OK, delete backup branch: git branch -D $BACKUP_BRANCH"
echo ""
echo "Backup branch created: $BACKUP_BRANCH"
