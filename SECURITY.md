# Security Policy

Synrail is in a narrow local alpha lane, so security reports should stay bounded and repo-specific.

## Reporting a vulnerability privately

Use [GitHub private vulnerability reporting](https://github.com/USBVadik/synrail/security/advisories/new)
for suspected vulnerabilities in Synrail. Do not open a public issue containing
an exploit, secret, private repository path, or unredacted Synrail artifact.

Include:

- the smallest redacted repro
- the observed misleading or unsafe outcome
- the local version or install path you tested

Before attaching any artifact, remove credentials, tokens, user names, absolute
paths, private repository names, source excerpts, and environment values. Do not
attach an unredacted `synrail bug-packet` to a public issue.

If private vulnerability reporting is unavailable, open a minimal public issue
asking for a private contact path. Include no exploit details or artifacts.

Ordinary non-sensitive bugs can still use the public bug-report template.

## Out of scope for this repo

Do not use this repo for broad production-host incident intake, downstream-agent incidents, or general security support outside the current local alpha support boundary.
