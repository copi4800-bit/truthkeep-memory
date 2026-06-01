# Enterprise Release Checklist

## Core checks

- [ ] `python -m compileall aegis_py truthkeep`
- [ ] focused graph/OpenClaw tests pass
- [ ] `python scripts/verify_enterprise_release.py`
- [ ] `python scripts/make_enterprise_release_manifest.py --root . --out ENTERPRISE_RELEASE_MANIFEST.json`

## Hygiene

- [ ] No `__pycache__`
- [ ] No `*.pyc`
- [ ] No `.pytest_cache`
- [ ] No `.git` in release zip
- [ ] No `memory_aegis.db`, WAL, SHM, or log files

## OpenClaw Easy Mode

- [ ] Easy manifest exposes exactly five tools
- [ ] Advanced manifest exists separately
- [ ] `truthkeep openclaw doctor` passes
- [ ] OpenClaw restarted and recognizes plugin

## Signing

- [ ] Windows Authenticode signed, timestamped, verified
- [ ] macOS pkg signed and notarized if distributed outside internal dev
- [ ] Linux artifact signed with GPG/cosign if distributed externally

## Claim hygiene

- [ ] Do not claim external audit before audit is done
- [ ] Do not claim absolute security
- [ ] Do not claim production cloud/multi-user service
- [ ] Keep wording: local-first, MCP stdio, no open ports
