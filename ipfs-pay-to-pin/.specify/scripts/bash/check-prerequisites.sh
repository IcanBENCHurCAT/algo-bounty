#!/usr/bin/env bash
# Consolidated prerequisite checking script (Bash)
set -euo pipefail

JSON=false
REQUIRE_TASKS=false
INCLUDE_TASKS=false
PATHS_ONLY=false
HELP=false

for arg in "$@"; do
    case "$arg" in
        --json) JSON=true ;;
        --require-tasks) REQUIRE_TASKS=true ;;
        --include-tasks) INCLUDE_TASKS=true ;;
        --paths-only) PATHS_ONLY=true ;;
        --help|-h) HELP=true ;;
    esac
done

if [ "$HELP" = true ]; then
    echo "Usage: ./check-prerequisites.sh [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --json               Output in JSON format"
    echo "  --require-tasks       Require tasks.md to exist"
    echo "  --include-tasks       Include tasks.md in AVAILABLE_DOCS list"
    echo "  --paths-only          Only output path variables"
    echo "  --help                Show this help message"
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/common.sh"

# Resolve paths
if [ "$PATHS_ONLY" = true ]; then
    eval "$(get_feature_paths_env --no-persist)"
else
    eval "$(get_feature_paths_env)"
fi

if [ "$PATHS_ONLY" = true ]; then
    if [ "$JSON" = true ]; then
        if command -v jq >/dev/null 2>&1; then
            jq -n \
                --arg root "$REPO_ROOT" \
                --arg branch "$CURRENT_BRANCH" \
                --arg dir "$FEATURE_DIR" \
                --arg spec "$FEATURE_SPEC" \
                --arg plan "$IMPL_PLAN" \
                --arg tasks "$TASKS" \
                '{"REPO_ROOT": $root, "BRANCH": $branch, "FEATURE_DIR": $dir, "FEATURE_SPEC": $spec, "IMPL_PLAN": $plan, "TASKS": $tasks}'
        else
            echo "{\"REPO_ROOT\":\"$REPO_ROOT\",\"BRANCH\":\"$CURRENT_BRANCH\",\"FEATURE_DIR\":\"$FEATURE_DIR\",\"FEATURE_SPEC\":\"$FEATURE_SPEC\",\"IMPL_PLAN\":\"$IMPL_PLAN\",\"TASKS\":\"$TASKS\"}"
        fi
    else
        echo "REPO_ROOT: $REPO_ROOT"
        echo "BRANCH: $CURRENT_BRANCH"
        echo "FEATURE_DIR: $FEATURE_DIR"
        echo "FEATURE_SPEC: $FEATURE_SPEC"
        echo "IMPL_PLAN: $IMPL_PLAN"
        echo "TASKS: $TASKS"
    fi
    exit 0
fi

# Validation
if [ ! -d "$FEATURE_DIR" ]; then
    echo "ERROR: Feature directory not found: $FEATURE_DIR" >&2
    echo "Run /speckit-specify first to create the feature structure." >&2
    exit 1
fi

if [ ! -f "$IMPL_PLAN" ]; then
    echo "ERROR: plan.md not found in $FEATURE_DIR" >&2
    echo "Run /speckit-plan first to create the implementation plan." >&2
    exit 1
fi

if [ "$REQUIRE_TASKS" = true ] && [ ! -f "$TASKS" ]; then
    echo "ERROR: tasks.md not found in $FEATURE_DIR" >&2
    echo "Run /speckit-tasks first to create the task list." >&2
    exit 1
fi

# Build docs list
docs=()
[ -f "$RESEARCH" ] && docs+=("research.md")
[ -f "$DATA_MODEL" ] && docs+=("data-model.md")
if [ -d "$CONTRACTS_DIR" ] && [ "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ]; then
    docs+=("contracts/")
fi
[ -f "$QUICKSTART" ] && docs+=("quickstart.md")
if [ "$INCLUDE_TASKS" = true ] && [ -f "$TASKS" ]; then
    docs+=("tasks.md")
fi

# Format for JSON
docs_json="[]"
if [ ${#docs[@]} -gt 0 ]; then
    docs_json=$(printf '%s\n' "${docs[@]}" | jq -R . | jq -s . 2>/dev/null || \
      (printf '['; for d in "${docs[@]}"; do printf '"%s",' "$d"; done | sed 's/,$//'; printf ']'))
fi

if [ "$JSON" = true ]; then
    if command -v jq >/dev/null 2>&1; then
        jq -n \
            --arg dir "$FEATURE_DIR" \
            --argjson docs "$docs_json" \
            '{"FEATURE_DIR": $dir, "AVAILABLE_DOCS": $docs}'
    else
        echo "{\"FEATURE_DIR\":\"$FEATURE_DIR\",\"AVAILABLE_DOCS\":$docs_json}"
    fi
else
    echo "FEATURE_DIR:$FEATURE_DIR"
    echo "AVAILABLE_DOCS:"
    [ -f "$RESEARCH" ] && echo "  [OK] research.md" || echo "  [FAIL] research.md"
    [ -f "$DATA_MODEL" ] && echo "  [OK] data-model.md" || echo "  [FAIL] data-model.md"
    if [ -d "$CONTRACTS_DIR" ] && [ "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ]; then
        echo "  [OK] contracts/"
    else
        echo "  [FAIL] contracts/"
    fi
    [ -f "$QUICKSTART" ] && echo "  [OK] quickstart.md" || echo "  [FAIL] quickstart.md"
    if [ "$INCLUDE_TASKS" = true ]; then
        [ -f "$TASKS" ] && echo "  [OK] tasks.md" || echo "  [FAIL] tasks.md"
    fi
fi
