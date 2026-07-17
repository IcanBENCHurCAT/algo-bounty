#!/usr/bin/env bash
# Create a new feature spec structure
set -euo pipefail

JSON=false
ALLOW_EXISTING_BRANCH=false
DRY_RUN=false
SHORT_NAME=""
NUMBER=0
TIMESTAMP=false
HELP=false
DESC_PARTS=()

while [ $# -gt 0 ]; do
    case "$1" in
        --json) JSON=true; shift ;;
        --allow-existing-branch) ALLOW_EXISTING_BRANCH=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --short-name) SHORT_NAME="$2"; shift 2 ;;
        --number) NUMBER="$2"; shift 2 ;;
        --timestamp) TIMESTAMP=true; shift ;;
        --help|-h) HELP=true; shift ;;
        *) DESC_PARTS+=("$1"); shift ;;
    esac
done

if [ "$HELP" = true ] || [ ${#DESC_PARTS[@]} -eq 0 ]; then
    echo "Usage: ./create-new-feature.sh [OPTIONS] <feature description>"
    exit 0
fi

feature_desc=$(echo "${DESC_PARTS[@]}" | xargs)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/common.sh"

repo_root=$(get_repo_root)
specs_dir="$repo_root/specs"

get_highest_number_from_specs() {
    local highest=0
    if [ -d "$specs_dir" ]; then
        for d in "$specs_dir"/*; do
            if [ -d "$d" ]; then
                local base
                base=$(basename "$d")
                if [[ "$base" =~ ^([0-9]{3,})- ]] && [[ ! "$base" =~ ^[0-9]{8}-[0-9]{6}- ]]; then
                    local num="${BASH_REMATCH[1]}"
                    # Strip leading zeros for arithmetic comparison
                    num=$((10#$num))
                    if [ "$num" -gt "$highest" ]; then
                        highest=$num
                    fi
                fi
            fi
        done
    fi
    echo "$highest"
}

get_branch_name_from_desc() {
    local desc="$1"
    # Basic clean-up to lowercase alphanumeric and hyphens
    local clean
    clean=$(echo "$desc" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g' | sed -E 's/^-//; s/-$//; s/-+/-/g')
    # Split into words and filter stop words
    local words=()
    local stop_words=(i a an the to for of in on at by with from is are was were be been being have has had do does did will would should could can may might must shall this that these those want need add get set)
    
    IFS='-' read -ra ADDR <<< "$clean"
    for w in "${ADDR[@]}"; do
        local is_stop=false
        for s in "${stop_words[@]}"; do
            if [ "$w" = "$s" ]; then
                is_stop=true
                break
            fi
        done
        if [ "$is_stop" = false ] && [ ${#w} -ge 3 ]; then
            words+=("$w")
        fi
    done
    
    if [ ${#words[@]} -gt 0 ]; then
        # Join first 3-4 words
        local limit=3
        [ ${#words[@]} -eq 4 ] && limit=4
        local result=""
        for ((i=0; i<limit && i<${#words[@]}; i++)); do
            result="${result:+$result-}${words[i]}"
        done
        echo "$result"
    else
        # Fallback to first 3 words
        echo "$clean" | cut -d'-' -f1-3
    fi
}

# Determine suffix
if [ -n "$SHORT_NAME" ]; then
    branch_suffix=$(echo "$SHORT_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g' | sed -E 's/^-//; s/-$//; s/-+/-/g')
else
    branch_suffix=$(get_branch_name_from_desc "$feature_desc")
fi

# Determine prefix
if [ "$TIMESTAMP" = true ]; then
    feature_num=$(date +'%Y%m%d-%H%M%S')
    branch_name="$feature_num-$branch_suffix"
else
    if [ "$NUMBER" -eq 0 ]; then
        highest=$(get_highest_number_from_specs)
        NUMBER=$((highest + 1))
    fi
    feature_num=$(printf "%03d" "$NUMBER")
    branch_name="$feature_num-$branch_suffix"
fi

# Truncate branch name to 244 chars (GitHub limit)
if [ ${#branch_name} -gt 244 ]; then
    local prefix_len=${#feature_num}
    local max_suffix=$((244 - prefix_len - 1))
    branch_suffix="${branch_suffix:0:$max_suffix}"
    branch_suffix=$(echo "$branch_suffix" | sed -E 's/-$//')
    branch_name="$feature_num-$branch_suffix"
fi

feature_dir="$specs_dir/$branch_name"
spec_file="$feature_dir/spec.md"

if [ "$DRY_RUN" = false ]; then
    if [ -d "$feature_dir" ] && [ "$ALLOW_EXISTING_BRANCH" = false ]; then
        echo "ERROR: Feature directory '$feature_dir' already exists." >&2
        exit 1
    fi
    mkdir -p "$feature_dir"
    
    if [ ! -f "$spec_file" ]; then
        if template=$(resolve_template "spec-template" "$repo_root"); then
            cp "$template" "$spec_file"
        else
            echo "Warning: Spec template not found; created empty spec file" >&2
            touch "$spec_file"
        fi
    fi
    
    save_feature_json "$repo_root" "$feature_dir"
fi

if [ "$JSON" = true ]; then
    if command -v jq >/dev/null 2>&1; then
        jq -n \
            --arg branch "$branch_name" \
            --arg spec "$spec_file" \
            --arg num "$feature_num" \
            '{"BRANCH_NAME": $branch, "SPEC_FILE": $spec, "FEATURE_NUM": $num}'
    else
        echo "{\"BRANCH_NAME\":\"$branch_name\",\"SPEC_FILE\":\"$spec_file\",\"FEATURE_NUM\":\"$feature_num\"}"
    fi
else
    echo "BRANCH_NAME: $branch_name"
    echo "SPEC_FILE: $spec_file"
    echo "FEATURE_NUM: $feature_num"
fi
