# PROMPT_BRIDGE_001

## Purpose

Define one controlled prompt bridge from a repair packet.

The goal is not to invent richer continuation vocabulary.
The goal is to turn the current repair packet into one bounded follow-up prompt for the next agent call.

## What it carries

- what is currently broken
- which repair step is active
- which scope is allowed
- what must pass
- what must not be touched

## Current reading

- the repair packet can now drive one bounded next-agent prompt directly
- this is one bridge from tightened core truth into the next repair attempt, not a broader UX shell
