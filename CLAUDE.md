# HermesNexus Claude Code Guide

This repository is the working area for the HermesNexus distributed edge management system.

## Project Summary

HermesNexus is a cloud-edge device management platform for managing hosts, IoT devices, and network equipment through a cloud control plane and Hermes-based edge nodes.

## MVP Scope

For MVP work, stay within Phase 1 unless the user explicitly expands scope:

- Linux hosts only
- SSH only
- One edge node first
- Minimal cloud control plane
- Task create -> edge receive -> SSH execute -> result return -> cloud visible

Do not expand into multi-protocol, multi-device, HA, or production hardening unless requested.

## Environment Model

- Local machine: code writing, fast iteration, unit tests
- Development/test server: `scsun@172.16.100.101:22`
- Edge node runtime: runs only the edge service, not the developer toolchain

Use the development/test server for deployment, integration testing, and validation of cloud/edge flows.

## Key Documents to Read First

1. `docs/09-MVP开发路线图.md`
2. `docs/65-Claude Code MVP落地开发与集成步骤.md`
3. `docs/66-Claude Code 可直接粘贴执行的任务提示词.md`
4. `docs/67-第一轮Claude Code任务拆分.md`
5. `docs/58-代码仓库落地版总览.md`
6. `docs/52-仓库初始化与本地启动.md`
7. `docs/61-开发脚本与Makefile约定.md`
8. `docs/62-环境变量与配置文件规范.md`
9. `docs/54-测试与联调规范.md`
10. `docs/55-发布回滚与验收流程.md`
11. `docs/56-故障处理Runbook.md`
12. `docs/63-本地调试与模拟器.md`
13. `docs/68-技术栈决策与MVP边界.md`
14. `docs/69-本机Hermes开发隔离方案.md`
15. `docs/70-开发前置条件与启动清单.md`
16. `docs/71-开发启动Checklist.md`
17. `docs/72-开工前10条清单.md`

## Working Rules

- Read the relevant docs before changing code.
- Keep changes small and reversible.
- Prefer the simplest implementation that satisfies MVP.
- Write or update tests for behavioral changes.
- Verify changes after each meaningful step.
- If scope is unclear, stop and restate the assumption before editing.
- Do not use the system-wide Hermes install as the project environment.
- Treat Hermes as a controlled dependency, not a global prerequisite.

## Preferred Execution Flow

1. Inspect repo state and matching docs.
2. Identify the smallest task that advances the MVP.
3. Implement the minimal change.
4. Run the most relevant verification command.
5. Summarize files changed, commands run, and result.

## Output Style

Be direct and concise. Favor action over commentary.
