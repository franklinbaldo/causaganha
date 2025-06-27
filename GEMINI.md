# GEMINI.md - Google Gemini AI Assistant Instructions

> 🤖 **Primary Instructions**: For comprehensive coding agent instructions, development workflow, and plan-first approach, see **`CLAUDE.md`** - the primary source of truth for all AI coding assistants working with this repository.

---

## 🎯 **Gemini-Specific Guidelines**

This document provides Gemini-specific instructions for working with the CausaGanha judicial analysis platform.

### **📋 Before Starting Work**
1. **Read CLAUDE.md first** - Contains complete development workflow and plan-first approach
2. **Check MASTERPLAN.md** - Current implementation phases and coordination
3. **Review AGENTS.md** - Technical architecture and testing requirements
4. **Follow alpha development guidelines** - Breaking changes are acceptable

### **🔧 Key Commands for Gemini**
```bash
# Setup
uv venv && source .venv/bin/activate
uv sync --dev && uv pip install -e .

# Always run tests before committing
uv run pytest -q

# Check database status
PYTHONPATH=src uv run causaganha db status

# Run pipeline
PYTHONPATH=src uv run causaganha pipeline --help
```

### **⚠️ Alpha Development Context**
- **Status**: Alpha software with frequent breaking changes
- **Approach**: Plan-first development (see CLAUDE.md)
- **Coordination**: Use MASTERPLAN.md for all implementation decisions
- **Testing**: Always run `uv run pytest -q` before commits
- **Quality**: >60% test coverage required

### **🏗️ Current Architecture**
- **Database**: DuckDB with Internet Archive synchronization
- **CLI**: Modern Typer-based interface (causaganha command)
- **Pipeline**: 4-stage process (queue → archive → analyze → score)
- **Rating System**: OpenSkill for lawyer performance evaluation

### **📚 Documentation Hierarchy**
1. **CLAUDE.md** - Primary instructions and development workflow
2. **MASTERPLAN.md** - Live coordination document
3. **AGENTS.md** - Technical specifics and architecture
4. **README.md** - User documentation

### **🎯 Development Priorities**
Current focus areas (see MASTERPLAN.md for details):
- Database integration fixes (Critical)
- Diario dataclass implementation
- Multi-tribunal collection support
- DTB database migration
- Prompt versioning system

---

## 🤖 **For Google Gemini**

When working with this codebase:
- **Always consult CLAUDE.md** for complete development guidelines
- **Follow plan-first approach** - create plans before implementation
- **Update MASTERPLAN.md** when adding new features or plans
- **Respect alpha status** - breaking changes are expected
- **Test thoroughly** - minimum 60% coverage required

**CLAUDE.md contains the authoritative development workflow and must be consulted before making any code changes.**