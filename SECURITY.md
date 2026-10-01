# Security Policy

## Supported versions

Only the latest released version of VoiceForge is supported with security fixes.

## Reporting a vulnerability

Please report security issues using **[GitHub's private vulnerability reporting](https://github.com/awesomo913/VoiceForge/security/advisories/new)** (Security tab → "Report a vulnerability") rather than a public issue. This lets the report be triaged before details are public.

If private reporting isn't available for you, open a regular GitHub issue with as much detail as you're comfortable sharing publicly, and note that it's a security concern in the title.

Please include:

- A description of the issue and its potential impact
- Steps to reproduce, if possible
- The VoiceForge version and OS you're running

## Scope notes

- VoiceForge runs entirely locally — it does not transmit your microphone input, recordings, or exported audio anywhere. There is no network activity at all during normal use.
- No account, API key, or telemetry is involved.
- Voice conversion (RVC) models are **user-supplied only** — VoiceForge ships with none, and loading a `.pth`/`.index` file is always a manual, explicit action you take. VoiceForge does not validate that a model file is safe; only load model files from sources you trust, the same way you would with any other machine-learning weights file.
- The release `.exe` is unsigned. Reports about SmartScreen or antivirus false positives are welcome context but are not themselves security vulnerabilities — see the README FAQ for the current recommended workaround (verify checksums, or build from source).
