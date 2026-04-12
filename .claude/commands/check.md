# Check

Use this command to validate changes before handing work back.

## Instructions

1. Run the most relevant tests for the change.
2. If the change touches deployment or docs, verify the referenced paths and commands still make sense.
3. If the change touches core behavior, run the smallest useful test subset first, then expand if needed.
4. Summarize pass/fail clearly.

## Validation Priorities

- Unit tests for code changes
- Integration tests for cloud-edge flow changes
- Doc consistency for workflow changes
- Minimal smoke checks for environment changes

## Output Format

- Commands run
- Result
- Any failures
- Recommended next action
