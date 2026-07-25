#!/usr/bin/env bash
# Setup tasks list for a feature
set -euo pipefail

JSON=false
HELP=false

for arg in "$@"; do
    case "$arg" in
        --json) JSON=true ;;
        --help|-h) HELP=true ;;
    esac
done

if [ "$HELP" = true ]; then
    echo "Usage: ./setup-tasks.sh [--json] [--help]"
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/common.sh"

# Get feature paths
eval "$(get_feature_paths_env)"

if [ ! -f "$IMPL_PLAN" ]; then
    echo "ERROR: plan.md not found in $FEATURE_DIR" >&2
    echo "Run /speckit-plan first to create the implementation plan." >&2
    exit 1
fi

if [ ! -f "$FEATURE_SPEC" ]; then
    echo "ERROR: spec.md not found in $FEATURE_DIR" >&2
    echo "Run /speckit-specify first to create the feature structure." >&2
    exit 1
fi

# Build available docs
docs=()
[ -f "$RESEARCH" ] && docs+=("research.md")
[ -f "$DATA_MODEL" ] && docs+=("data-model.md")
if [ -d "$CONTRACTS_DIR" ] && [ "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ]; then
    docs+=("contracts/")
fi
[ -f "$QUICKSTART" ] && docs+=("quickstart.md")

# Resolve template
tasksTemplate=""
if ! tasksTemplate=$(resolve_template "tasks-template" "$REPO_ROOT"); then
    expectedCoreTemplate="$REPO_ROOT/.specify/templates/tasks-template.md"
    echo "ERROR: Tasks template not found for repository root: $REPO_ROOT" >&2
    echo "Expected core template: $expectedCoreTemplate" >&2
    exit 1
fi

# Format AVAILABLE_DOCS for JSON
docs_json="[]"
if [ ${#docs[@]} -gt 0 ]; then
    # Simple array formatting
    docs_json=$(printf '%s\n' "${docs[@]}" | jq -R . | jq -s . 2>/dev/null || \
      (printf '['; for d in "${docs[@]}"; do printf '"%s",' "$d"; done | sed 's/,$//'; printf ']'))
fi

if [ "$JSON" = true ]; then
    if command -v jq >/dev/null 2>&1; then
        jq -n \
            --arg dir "$FEATURE_DIR" \
            --argjson docs "$docs_json" \
            --arg template "$tasksTemplate" \
            '{"FEATURE_DIR": $dir, "AVAILABLE_DOCS": $docs, "TASKS_TEMPLATE": $template}'
    else
        echo "{\"FEATURE_DIR\":\"$FEATURE_DIR\",\"AVAILABLE_DOCS\":$docs_json,\"TASKS_TEMPLATE\":\"$tasksTemplate\"}"
    fi
else
    echo "FEATURE_DIR: $FEATURE_DIR"
    echo "TASKS_TEMPLATE: ${tasksTemplate:-not found}"
    echo "AVAILABLE_DOCS:"
    [ -f "$RESEARCH" ] && echo "  [OK] research.md" || echo "  [FAIL] research.md"
    [ -f "$DATA_MODEL" ] && echo "  [OK] data-model.md" || echo "  [FAIL] data-model.md"
    if [ -d "$CONTRACTS_DIR" ] && [ "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ]; then
        echo "  [OK] contracts/"
    else
        echo "  [FAIL] contracts/"
    fi
    [ -f "$QUICKSTART" ] && echo "  [OK] quickstart.md" || echo "  [FAIL] quickstart.md"
fi
