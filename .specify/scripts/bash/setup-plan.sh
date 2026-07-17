#!/usr/bin/env bash
# Setup implementation plan for a feature
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
    echo "Usage: ./setup-plan.sh [--json] [--help]"
    echo "  --json     Output results in JSON format"
    echo "  --help     Show this help message"
    exit 0
fi

# Sourcing common.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/common.sh"

# Get feature paths
eval "$(get_feature_paths_env)"

# Ensure the feature directory exists
mkdir -p "$FEATURE_DIR"

# Copy plan template if it doesn't exist
if [ -f "$IMPL_PLAN" ]; then
    if [ "$JSON" = true ]; then
        echo "Plan already exists at $IMPL_PLAN, skipping template copy" >&2
    else
        echo "Plan already exists at $IMPL_PLAN, skipping template copy"
    fi
else
    template=""
    if template=$(resolve_template "plan-template" "$REPO_ROOT"); then
        cp "$template" "$IMPL_PLAN"
        if [ "$JSON" = true ]; then
            echo "Copied plan template to $IMPL_PLAN" >&2
        else
            echo "Copied plan template to $IMPL_PLAN"
        fi
    else
        if [ "$JSON" = true ]; then
            echo "Warning: Plan template not found" >&2
        else
            echo "Warning: Plan template not found"
        fi
        touch "$IMPL_PLAN"
    fi
fi

# Output results
if [ "$JSON" = true ]; then
    if command -v jq >/dev/null 2>&1; then
        jq -n \
            --arg spec "$FEATURE_SPEC" \
            --arg plan "$IMPL_PLAN" \
            --arg specs_dir "$FEATURE_DIR" \
            --arg branch "$CURRENT_BRANCH" \
            '{"FEATURE_SPEC": $spec, "IMPL_PLAN": $plan, "SPECS_DIR": $specs_dir, "BRANCH": $branch}'
    else
        echo "{\"FEATURE_SPEC\":\"$FEATURE_SPEC\",\"IMPL_PLAN\":\"$IMPL_PLAN\",\"SPECS_DIR\":\"$FEATURE_DIR\",\"BRANCH\":\"$CURRENT_BRANCH\"}"
    fi
else
    echo "FEATURE_SPEC: $FEATURE_SPEC"
    echo "IMPL_PLAN: $IMPL_PLAN"
    echo "SPECS_DIR: $FEATURE_DIR"
    echo "BRANCH: $CURRENT_BRANCH"
fi
