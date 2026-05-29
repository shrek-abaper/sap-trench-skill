# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

`sap-functional-skill` is a SAP Business Domain AI Skill package collection, following the standard **SKILL format specification**. The project contains practical troubleshooting knowledge distilled from 10+ years of real SAP project implementations.

**Important Context**: This is not a code project. It is a knowledge repository packaged as AI skills. All content is in Markdown format following specific structuring rules.

---

## Current Skills

Currently contains one skill: `sap-trench-skill` located at `skills/sap-trench-skill/`.

The skill contains 14 reference files organized by SAP module:
- `abap.md` — ABAP development, BAdI, Enhancement Spot, performance tuning
- `mm.md` — Materials Management, procurement, stock, STO, account determination
- `sd.md` — Sales & Distribution, pricing, delivery, billing, credit, ATP
- `fico.md` — FI/CO, document posting, exchange rates, document splitting, COPA
- `pp.md` — Production Planning, BOM, routing, MRP, ATP
- `wm.md` — Warehouse Management, transfer orders, bins, physical inventory
- `pm.md` — Plant Maintenance, equipment, functional location, maintenance orders
- `qm.md` — Quality Management, inspection lots, usage decisions
- `vms.md` — Vehicle Management System (IS-AUTO VELO)
- `integration.md` — PI/PO, IDoc, Proxy, OData, CPI integration
- `auth.md` — Authorization, AUTHORITY-CHECK, SU53, roles
- `print.md` — SmartForms, SAPscript, NACE message control
- `reference-tables.md` — T-code, table, BAPI index across all modules
- `troubleshooting.md` — Troubleshooting case library (CASE-001 through CASE-015)

---

## Architecture

### Skill Format Compliance

The `sap-trench-skill/` directory complies with the standard SKILL format:
- `SKILL.md` — Trigger layer with YAML frontmatter (name, description, keywords) and routing table
- `references/` — Knowledge layer with module-specific markdown files
- `CONTRIBUTING.md` — Contribution guidelines

### Content Structure

Every knowledge card in `references/troubleshooting.md` follows a **four-part structure**:
1. **现象** (Phenomenon) — What happened, what the user did, error messages
2. **根本原因** (Root Cause) — Why the problem occurred (the most critical part)
3. **解决方案** (Solution) — Actionable steps, ranked by recommendation
4. **经验总结** (Experience Summary) — Patterns for future reference

### Routing Table (SKILL.md)

The routing table in `SKILL.md` maps question types to specific reference files. When adding new modules, add a corresponding row to this table.

---

## Development

### No Build/Test/Lint

This repository contains only documentation. There are no build commands, test suites, or linting configured.

### Creating Content

**When adding new knowledge cards**, follow the template in `CONTRIBUTING.md`:

```markdown
## CASE-NNN：[Problem title with module and symptoms]

**标签**：`#module` `#keyword1` `#keyword2` `#SAPversion`

**现象**

**根本原因**

**如何定位**

**解决方案**

**经验总结**
```

**Quality standards**:
- Must come from real project scenarios (not theoretical or SAP Help documentation)
- Must explain "why" (root cause), not just "how"
- Solutions must be verified in actual environments
- Tags must include: `#模块`, `#关键技术`, `#SAP版本` (ECC/S4HANA)

### Adding New Skills

To add a new skill:
1. Create directory under `skills/new-skill-name/`
2. Create `SKILL.md` with proper YAML frontmatter and routing table
3. Create `references/` directory for knowledge files
4. Create `CONTRIBUTING.md` with contribution guidelines
5. Add skill to `README.md` and `CHANGELOG.md`

### File Size Guidelines

- `SKILL.md` — Keep under 150 lines (trigger layer only)
- `references/*.md` — Ideal 200-400 lines; split if over 400 lines

---

## Platform Compatibility

The skills follow the standard SKILL format and are compatible with:
- Any AI Agent framework supporting SKILL format (native)
- [OpenCode](https://github.com/opencode-ai/opencode)
- [oh-my-opencode](https://github.com/oh-my-opencode/oh-my-opencode)

---

## Important Content Principles

1. **Real project focus** — Content must come from actual delivery scenarios, not SAP Help or theoretical knowledge
2. **Root cause emphasis** — Knowledge must explain "why," not just "how"
3. **Version specificity** — Always specify SAP version (ECC 6.0, S/4HANA 1909+, etc.)
4. **Non-obvious value** — Focus on what's missing from standard SAP documentation

---

## Git Workflow

No special git hooks or commit message conventions are configured. Standard git practices apply.

When contributing:
- Follow the PR template in `.github/PULL_REQUEST_TEMPLATE.md`
- Review content quality checklist before submitting
- Update routing table in `SKILL.md` when adding new modules