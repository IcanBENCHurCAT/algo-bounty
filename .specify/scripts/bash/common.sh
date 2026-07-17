#!/usr/bin/env bash
# Common bash functions analogous to common.ps1

find_specify_root() {
    local current="${1:-$(pwd)}"
    while [ "$current" != "/" ] && [ -n "$current" ]; do
        if [ -d "$current/.specify" ]; then
            echo "$current"
            return 0
        fi
        current="$(dirname "$current")"
    done
    return 1
}

resolve_specify_init_dir() {
    local init_dir="$SPECIFY_INIT_DIR"
    if [ ! -d "$init_dir" ]; then
        echo "ERROR: SPECIFY_INIT_DIR does not point to an existing directory: $SPECIFY_INIT_DIR" >&2
        exit 1
    fi
    # Normalize path
    init_dir="$(cd "$init_dir" && pwd)"
    if [ ! -d "$init_dir/.specify" ]; then
        echo "ERROR: SPECIFY_INIT_DIR is not a Spec Kit project (no .specify/ directory): $init_dir" >&2
        exit 1
    fi
    echo "$init_dir"
}

get_repo_root() {
    if [ -n "${SPECIFY_INIT_DIR:-}" ]; then
        resolve_specify_init_dir
        return 0
    fi

    local specify_root
    if specify_root=$(find_specify_root); then
        echo "$specify_root"
        return 0
    fi

    # Fallback
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$script_dir/../../.." && pwd
}

get_current_branch() {
    if [ -n "${SPECIFY_FEATURE:-}" ]; then
        echo "$SPECIFY_FEATURE"
        return 0
    fi
    echo ""
}

save_feature_json() {
    local repo_root="$1"
    local feature_dir="$2"
    
    # Strip repo root prefix to make relative
    local rel_dir="${feature_dir#$repo_root/}"
    rel_dir="${rel_dir#$repo_root}" # just in case
    
    local fj_path="$repo_root/.specify/feature.json"
    local json="{\"feature_directory\":\"$rel_dir\"}"
    
    mkdir -p "$repo_root/.specify"
    echo "$json" > "$fj_path"
}

get_feature_paths_env() {
    local no_persist="${1:-}"
    local repo_root
    repo_root=$(get_repo_root)
    local current_branch
    current_branch=$(get_current_branch)

    local feature_dir=""
    local feature_json="$repo_root/.specify/feature.json"

    if [ -n "${SPECIFY_FEATURE_DIRECTORY:-}" ]; then
        feature_dir="$SPECIFY_FEATURE_DIRECTORY"
        # Make absolute if relative
        if [[ "$feature_dir" != /* ]]; then
            feature_dir="$repo_root/$feature_dir"
        fi
        if [ "$no_persist" != "--no-persist" ]; then
            save_feature_json "$repo_root" "$SPECIFY_FEATURE_DIRECTORY"
        fi
    elif [ -f "$feature_json" ]; then
        if command -v jq >/dev/null 2>&1; then
            feature_dir=$(jq -r '.feature_directory' "$feature_json")
        else
            # Fallback simple parser
            feature_dir=$(grep -o '"feature_directory":"[^"]*' "$feature_json" | cut -d'"' -f4)
        fi
        if [[ "$feature_dir" != /* ]]; then
            feature_dir="$repo_root/$feature_dir"
        fi
    else
        echo "ERROR: Feature directory not found. Set SPECIFY_FEATURE_DIRECTORY or run specify command." >&2
        exit 1
    fi

    if [ -z "$current_branch" ]; then
        current_branch=$(basename "$feature_dir")
    fi

    # Output env variables structure mimicking the custom object return
    # Callers source this function's output or capture it
    echo "REPO_ROOT=$repo_root"
    echo "CURRENT_BRANCH=$current_branch"
    echo "FEATURE_DIR=$feature_dir"
    echo "FEATURE_SPEC=$feature_dir/spec.md"
    echo "IMPL_PLAN=$feature_dir/plan.md"
    echo "TASKS=$feature_dir/tasks.md"
    echo "RESEARCH=$feature_dir/research.md"
    echo "DATA_MODEL=$feature_dir/data-model.md"
    echo "QUICKSTART=$feature_dir/quickstart.md"
    echo "CONTRACTS_DIR=$feature_dir/contracts"
}

test_file_exists() {
    local path="$1"
    local desc="$2"
    if [ -f "$path" ]; then
        echo "  [OK] $desc"
        return 0
    else
        echo "  [FAIL] $desc"
        return 1
    fi
}

test_dir_has_files() {
    local path="$1"
    local desc="$2"
    if [ -d "$path" ] && [ "$(ls -A "$path" 2>/dev/null)" ]; then
        echo "  [OK] $desc"
        return 0
    else
        echo "  [FAIL] $desc"
        return 1
    fi
}

resolve_template() {
    local template_name="$1"
    local repo_root="$2"

    local base="$repo_root/.specify/templates"
    
    # Priority 1: overrides
    local override="$base/overrides/$template_name.md"
    if [ -f "$override" ]; then
        echo "$override"
        return 0
    fi

    # Priority 2: presets registry/convention (skip python details for basic file copying fallback, 
    # but check typical paths)
    local presets_dir="$repo_root/.specify/presets"
    if [ -d "$presets_dir" ]; then
        for preset in "$presets_dir"/*; do
            if [ -d "$preset" ] && [ "$(basename "$preset")" != ".*" ]; then
                local candidate="$preset/templates/$template_name.md"
                if [ -f "$candidate" ]; then
                    echo "$candidate"
                    return 0
                fi
            fi
        done
    fi

    # Priority 3: extensions
    local ext_dir="$repo_root/.specify/extensions"
    if [ -d "$ext_dir" ]; then
        for ext in "$ext_dir"/*; do
            if [ -d "$ext" ]; then
                local candidate="$ext/templates/$template_name.md"
                if [ -f "$candidate" ]; then
                    echo "$candidate"
                    return 0
                fi
            fi
        done
    fi

    # Priority 4: core
    local core="$base/$template_name.md"
    if [ -f "$core" ]; then
        echo "$core"
        return 0
    fi

    return 1
}
