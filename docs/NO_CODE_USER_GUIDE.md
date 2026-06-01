# TruthKeep No-Code User Guide

This guide is for users who do not want to edit JSON or read Python tracebacks.

## Goal

Open TruthKeep, connect it to OpenClaw, and use memory safely.

## Install

Windows: double-click `RUN_TRUTHKEEP_WINDOWS.cmd`.

macOS/Linux: run `./RUN_TRUTHKEEP_MAC_LINUX.sh`.

## Daily use

1. Start OpenClaw.
2. Ask your agent to remember or correct facts.
3. Use `memory_status` if you want to check health.

## Safety

TruthKeep Easy Mode:

- Does not open HTTP ports.
- Does not expose LAN or internet APIs.
- Stores memory locally.
- Keeps advanced tools hidden by default.

## If something breaks

Run:

```bash
truthkeep repair
truthkeep openclaw doctor
```


## Public setup command

OpenClaw and npm/package users can also run:

```bash
truthkeep-setup
```

It launches the same Easy Mode setup.
