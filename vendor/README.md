# vendor/

This folder is gitignored (except this file) — nothing in it is committed. It
exists so a human can manually vendor the optional `rubberband` command-line
tool for a release build that includes working formant shift.

**VoiceForge itself never downloads anything into this folder.** Automating a
fetch-and-bundle of a third-party executable as part of a build or CI
pipeline isn't something this project's tooling does — see THIRD_PARTY.md for
the full reasoning. This is a deliberate, manual, one-time step for whoever
is cutting a release, not something `build.py` or CI performs on its own.

## To enable formant shift in a release build

1. Download the official Windows command-line build from
   <https://breakfastquay.com/rubberband/> (the project's own site — check
   for a published checksum or signature on that page and verify against it
   if one exists).
2. Unzip it and copy `rubberband.exe` (and any `.dll` files it ships with)
   into this folder: `vendor/rubberband/rubberband.exe`, etc.
3. Run `sha256sum vendor/rubberband/rubberband.exe` (or
   `Get-FileHash -Algorithm SHA256` in PowerShell) and compare it against
   whatever the official site publishes, if anything.
4. Open `build.py` and set `VENDOR_RUBBERBAND_SHA256` to that hash, so future
   builds fail loudly instead of silently bundling a different binary.
5. Run `python build.py` as normal — it detects `vendor/rubberband/`,
   verifies the checksum, and bundles it. If the folder is empty/missing, the
   build proceeds exactly as before (formant shift uses pedalboard's
   pitch-only fallback) — nothing breaks either way.

## Why a human has to do this

Rubber Band is GPL-2.0-licensed. Shipping it as a separate executable that
VoiceForge invokes over the command line (not linked into the app) qualifies
as "mere aggregation" under the GPL, so it doesn't require VoiceForge itself
to be GPL-licensed — but it does require the license text and a source offer
to be included (see `licenses/rubberband-COPYING` and `THIRD_PARTY.md`), and
it means a real binary from a real download has to be verified by someone
before it ships. That verification step belongs to a person, not an
automated script.
