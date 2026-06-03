# Engineering Guidelines

This repo follows the **Karpathy Guidelines for AI Coding** to reduce common LLM coding mistakes.

## 1. Think Before Coding
- State assumptions explicitly. If uncertain, ask.
- Present multiple interpretations rather than choosing silently.
- Acknowledge simpler approaches when they exist.
- Surface confusion instead of proceeding with unclear requirements.

## 2. Simplicity First
- Minimum code that solves the problem. Nothing speculative.
- Exclude unrequested features, abstractions, or flexibility.
- Avoid error handling for impossible scenarios.
- Rewrite if code could be significantly shorter.

## 3. Surgical Changes
- Touch only what you must. Clean up only your own mess.
- Don't improve adjacent unrelated code; don't refactor unbroken code.
- Match existing style conventions.
- Only remove imports/variables/functions made unused by your changes.

## 4. Goal-Driven Execution
- Define verifiable success criteria before starting.
- Transform vague tasks into testable objectives.
- For multi-step work, outline a brief plan with verification checkpoints.

_Trade-off: these favor caution over speed; best applied to non-trivial tasks._

Source: https://github.com/multica-ai/andrej-karpathy-skills/blob/main/skills/karpathy-guidelines/SKILL.md
