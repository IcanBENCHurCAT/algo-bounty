---
name: "speckit-sweep"
description: "Verify that all specs/tasks are fully implemented, archive the active spec files, and compile a condensed Architectural Decision Record (ADR), marking any superseded ADRs."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/sweep.md"
---

## Goal

The `/speckit-sweep` command transitions a completed feature from specification and active tracking to a permanent part of the codebase's history. It:
1. Verifies that all tasks in the active specification directory have been completed.
2. Formats a new Architectural Decision Record (ADR) in `docs/adr/` representing the finalized architecture/decisions of the feature, including marking any previous ADRs that are superseded by this new architecture.
3. Registers the new ADR in `docs/adr/README.md`.
4. Archives the specification folder by moving it to `specs/archive/`.
5. Clears/resets the active feature setting.

---

## Execution Steps

### 1. Initialize & Verify Completion
1. Locate the active feature directory by reading `.specify/feature.json`. Derive:
   - `FEATURE_DIR` = path from `feature_directory` in `feature.json`
   - `TASKS_FILE` = `FEATURE_DIR/tasks.md`
2. If `FEATURE_DIR` or `tasks.md` does not exist, **HALT** and report: `"No active feature found or tasks.md is missing."`
3. Read `tasks.md` and check for any incomplete tasks. An incomplete task is any checklist item matching `- [ ]` (ignoring casing/whitespace).
4. If there are any incomplete tasks:
   - List the incomplete task IDs and titles.
   - **HALT** and output: `"❌ Sweep halted: Feature is not fully implemented. Please complete all tasks in tasks.md before sweeping."`

### 2. Identify and Update Superseded ADRs
1. Scan the existing files under `docs/adr/*.md` and search for related systems or decisions that this new feature overrides, extends, or replaces.
2. For any ADR that is superseded/updated:
   - Update its frontmatter or status header to clearly show its updated status:
     ```markdown
     ## Status: Superseded by ADR XXXX
     ```
   - Add a brief note under the status explaining that the decision has been updated/replaced by the new ADR.

### 3. Compile the Architectural Decision Record (ADR)
1. Determine the next sequential index for the ADR by listing `docs/adr/` files. For example, if the latest is `0009`, the new one will be `0010`.
2. Format the filename as: `docs/adr/<index>-<kebab-case-feature-name>.md`.
3. Create the new ADR file using the following structure:
   ```markdown
   # v<index_without_leading_zeros>: <Feature Name>

   This document details the architectural decisions made during the implementation of the <Feature Name> feature.

   ---

   ## Status
   Approved / Implemented

   ## Context & Problem
   <Provide a highly condensed summary of the problem, background, and objectives from the spec/plan.>

   ## Decision
   <State the concrete architectural choices made, how they were implemented, and the specific libraries/patterns used.>

   ## Consequences
   <List the positive and negative consequences of these decisions.>

   ## Superseded Decisions
   <List any prior ADRs that are superseded or updated by this record, if any. Otherwise, state "None".>
   ```

### 4. Register the ADR
1. Open `docs/adr/README.md`.
2. Append the new ADR to the list in sequential order, matching the existing formatting:
   ```markdown
   * [<index> - <Feature Name>](<index>-<kebab-case-feature-name>.md)
   ```

### 5. Archive Spec Files and Reset Active Feature
1. Move the active feature folder `specs/<feature-name>` to `specs/archive/<feature-name>`.
2. Update `.specify/feature.json` to reset `feature_directory` to an empty string `""` or `null`.
3. Output a success message summarizing:
   - The compiled ADR path
   - Superseded/updated ADRs (if any)
   - The archived specification directory
