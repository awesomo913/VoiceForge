# vendor/

This folder is gitignored (except this file) — nothing in it is committed.
It holds the optional `rubberband` command-line tool (needed for formant
shift) as a verified, checksum-pinned binary rather than a tracked file.

## How it gets here

As of 2026-10-01, a specific Rubber Band 4.0.0 Windows release has been
verified (zip sha256, `rubberband.exe` sha256, and its Authenticode
signature by Christopher Cannam / Particular Programs Ltd, Rubber Band's own
author — full record in `THIRD_PARTY.md`) and its exact download URL and
checksums are pinned in `build.py` (`VENDOR_RUBBERBAND_ZIP_URL`,
`VENDOR_RUBBERBAND_ZIP_SHA256`, `VENDOR_RUBBERBAND_SHA256`).

- **Already have it locally?** `python build.py` just uses it — nothing is
  re-downloaded.
- **Clean checkout (CI, or a fresh dev machine)?** `build.py`'s
  `fetch_vendor_rubberband()` downloads the pinned zip, verifies its sha256,
  extracts `rubberband.exe` + `sndfile.dll` + `COPYING.txt` into
  `vendor/rubberband/`, and verifies `rubberband.exe`'s own sha256 again —
  aborting the build on any mismatch rather than ever bundling an unverified
  file. `release.yml` calls this explicitly as its own CI step; `build.py`'s
  `main()` also calls it, so a plain `python build.py` works unattended too.
- **Folder missing/empty and fetching fails or is skipped?** The build
  proceeds exactly as before — formant shift falls back to pedalboard's
  pitch-only shifter (see README Limitations). Nothing breaks either way.

## Updating to a newer Rubber Band release

Bumping the pinned version is a deliberate, reviewed change, not something
that happens automatically:

1. Download the new release from <https://breakfastquay.com/rubberband/>.
2. Verify it independently — compute its sha256, and check its Authenticode
   signature (`Get-AuthenticodeSignature` on Windows) really does show
   Christopher Cannam / Particular Programs Ltd as the signer.
3. Update `VENDOR_RUBBERBAND_ZIP_URL`, `VENDOR_RUBBERBAND_ZIP_SHA256`, and
   `VENDOR_RUBBERBAND_SHA256` in `build.py` to the new values.
4. Update the version number and checksums recorded in `THIRD_PARTY.md`.
5. Delete the old `vendor/rubberband/` (if present) and run `python build.py`
   to confirm the new one fetches, verifies, and bundles cleanly.

## Why verification matters here

Rubber Band is GPL-2.0-or-later, and VoiceForge itself is GPL-3.0-or-later
(see `LICENSE`) — bundling it as a separate executable invoked over the
command line (not linked into the app) is compatible either way. The
checksum + signature pinning isn't about licensing, though: it's the
supply-chain control that makes it acceptable to let a build pipeline
re-fetch a third-party executable automatically at all — the pin means a
tampered or substituted file fails the build loudly instead of silently
shipping.
