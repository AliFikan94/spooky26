---
title: Poltergeist: a ghost in my shell that runs on a local open model
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

## What I Built
Poltergeist haunts your terminal. A tiny hook records every command you run and, sometimes, a ghost whispers back with a dry, eerie remark that remembers your habits ("You have run `git push` 41 times. It has never once been enough.").

For Día de los Muertos it also builds an **ofrenda**: `poltergeist ofrenda` lists commands you ran constantly and then stopped running (that `svn update` you typed 400 times in 2019) and writes a small remembrance for each. Your shell history is a record of who you were, and the ofrenda is how it gets honoured.

## Demo
<!-- TODO: add a screen recording of the ghost whispering and of `poltergeist ofrenda` -->

## Code
<!-- embed the repo: {% embed https://github.com/alifikan94/spooky26 %} -->

## How I Built It
- **Model:** any small open-weight chat model through **Ollama** (default `llama3.2:1b`), called over its local `/api/chat` endpoint.
- **Harness:** pure Python stdlib. A bash/zsh hook sends `(command, exit status)` to `poltergeist whisper` in a background subshell so the prompt never blocks.
- **Memory:** a local JSONL "graveyard". The prompt includes how often you've run the command, when you last did, and your favourite commands lately, which is what makes it feel like it *knows* you.
- **Offline fallback:** if the model is unreachable or slow, hand-written omens take over, so the ghost always answers.

## Why Does Open Innovation Matter?
A shell history contains project names, hostnames and half-typed secrets. I wasn't willing to send that to a hosted API for the sake of a spooky one-liner. With an open-weight model:
- the history never leaves the machine (the code refuses non-loopback model hosts and never records commands that look like they hold secrets);
- it works offline, and the ghost has a graceful degraded mode;
- the personality is just a system prompt and the voice is just a model name, so you can swap models or fine-tune your own;
- it costs nothing and can't disappear when a vendor changes its terms.

## The Spirit of It
<!-- TODO: add the moment it landed, e.g. the first time the ofrenda listed a command you forgot you loved -->
