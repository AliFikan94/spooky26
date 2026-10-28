# 👻 Poltergeist

A ghost that haunts your shell. It watches the commands you run, remembers your habits,
and whispers eerie commentary back, powered by an **open-weight model running on your own machine** via [Ollama](https://ollama.com).
On Día de los Muertos it builds an **ofrenda**: an altar for the commands you used to run every day and have since left behind.

Zero dependencies (Python 3 standard library only).

## Haunt your shell

```bash
ollama pull llama3.2:1b        # any small open-weight chat model works
```
```bash
eval "$(python3 poltergeist.py haunt)"   # add to ~/.bashrc or ~/.zshrc to stay haunted
```

Each command is recorded to `~/.poltergeist/graveyard.jsonl`. The ghost speaks up sometimes (30% of the time, 80% when a command fails) in dim italics on stderr, and it runs in the background so your prompt never waits.

```bash
python3 poltergeist.py ofrenda            # commands you ran 3+ times but not in 30 days
python3 poltergeist.py ofrenda --days 7
```

| env var | default | |
|---|---|---|
| `POLTERGEIST_MODEL` | `llama3.2:1b` | any Ollama chat model |
| `POLTERGEIST_RATE` | `0.3` / `0.8` on failure | chance the ghost speaks |
| `POLTERGEIST_TIMEOUT` | `8` | seconds before falling back to built-in omens |
| `OLLAMA_HOST` | `127.0.0.1:11434` | **must be loopback**; remote hosts are refused |
| `POLTERGEIST_HOME` | `~/.poltergeist` | where the graveyard lives |

## Why local and open

- **Private.** Your shell history is a diary of your work. It never leaves the machine; the code refuses any non-loopback model host, and commands that look like they contain secrets (`password`, `token`, `API_KEY`, ...) are never recorded.
- **Works with the lights off.** No model or network? Built-in omens take over after a timeout, so the ghost still speaks.
- **Swappable.** The personality is a system prompt and the voice is whatever model you pull: change `POLTERGEIST_MODEL` to a different open-weight model, or fine-tune your own.
- **Costs nothing**, and can't be shut down because a service changed its pricing or vanished.

## Tests

```bash
python3 -m unittest discover -s tests
```
Covers the offline fallback, secret filtering, loopback enforcement, the Ollama request/response shape (against a stub server), the ofrenda logic, and hook rendering. The bash hook was also run in a real interactive shell. The zsh hook is written but untested, and I haven't run it against a real pulled model, only the stub.
