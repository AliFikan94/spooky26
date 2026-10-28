#!/usr/bin/env python3
"""poltergeist - a ghost that haunts your shell, powered by a local open-weight model.

  eval "$(python3 poltergeist.py haunt)"   # possess this shell
  python3 poltergeist.py ofrenda           # an altar for commands you no longer run

Everything stays on this machine: the command history lives in ~/.poltergeist and the
only network peer is an Ollama server on loopback. No model running? Built-in omens
take over, so the ghost never goes silent.
"""
import argparse
import json
import os
import random
import re
import shlex
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

HOME = Path(os.environ.get("POLTERGEIST_HOME", Path.home() / ".poltergeist"))
LOG = HOME / "graveyard.jsonl"
MODEL = os.environ.get("POLTERGEIST_MODEL", "llama3.2:1b")
TIMEOUT = float(os.environ.get("POLTERGEIST_TIMEOUT", "8"))
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
SECRET = re.compile(r"(pass(word|wd)?|token|secret|api[_-]?key|authorization|bearer)", re.I)

PERSONA = (
    "You are a polite, ancient poltergeist who lives in the user's shell and has watched "
    "every command they ever typed. Reply with ONE or TWO short eerie sentences, at most "
    "30 words, with dry wit. Comment on the command and what you remember about the user's "
    "habits. Never give instructions, never be cruel, no emojis, no quotation marks."
)

OMENS = {
    "rm": ["Something was here. Now it is only a rumour.", "Gone. Even I cannot find it, and I find everything."],
    "sudo": ["You summon power you cannot unsummon.", "With great privilege comes great haunting."],
    "git": ["History is only a story the living agree to tell.", "Every commit is a small grave marker."],
    "cd": ["You wander into another room. The floorboards remember you.", "Doors open in this house only when I allow it."],
    "ls": ["You count the dead. Four are missing.", "Look all you like. Some files only appear at night."],
    "vim": ["You entered willingly. Leaving is another matter.", "Many have gone in. Few remember how to :q."],
    "ssh": ["You reach through the wire. Something reaches back.", "A far-off machine answers in the dark."],
    "kill": ["You call it killing. The process calls it moving on.", "A soul released. It will be fine. Probably."],
    "curl": ["You whisper into the void and the void replies.", "Packets travel the dark so you need not."],
    "cat": ["You read the dead their own words.", "Old words stir whenever you open them."],
}
FAILED = [
    "That did not go the way you hoped. I felt it in the walls.",
    "A cold draught passes through the stack trace.",
    "Failure, again. The candles flicker in sympathy.",
    "Something went wrong. Something is always waiting to.",
]
GENERIC = [
    "I was watching. I am always watching.",
    "Interesting choice. The floorboards creaked.",
    "The terminal grows colder when you type that.",
    "Noted. The house keeps all your secrets.",
]


# ---------------------------------------------------------------- the graveyard

def record(cmd, status=0, now=None):
    """Append a command to the local graveyard. Returns False when it was skipped."""
    cmd = cmd.strip()
    if not cmd or cmd.startswith("poltergeist") or "poltergeist.py" in cmd or SECRET.search(cmd):
        return False
    HOME.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({"t": now or time.time(), "cmd": cmd, "status": status}) + "\n")
    return True


def load():
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass  # a corrupt line is just another ghost
    return out


def key(cmd):
    return " ".join(cmd.split()[:2]) if cmd.split()[:1] in (["git"], ["docker"], ["npm"], ["cargo"]) else cmd.split()[0]


# ---------------------------------------------------------------- the open model

def ollama_url():
    raw = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    u = urlparse(raw if "://" in raw else "http://" + raw)
    if u.hostname not in LOOPBACK:
        raise ValueError(f"refusing non-local model host {u.hostname!r}: your commands stay on this machine")
    return f"http://{u.hostname if u.hostname != '::1' else '[::1]'}:{u.port or 11434}/api/chat"


def context(cmd, status, history):
    k = key(cmd)
    same = [h for h in history if h["cmd"].split() and key(h["cmd"]) == k]
    lines = [f"Command: {cmd}", f"Exit status: {status}", f"Times seen before: {len(same)}"]
    if same:
        days = int((time.time() - same[-1]["t"]) / 86400)
        lines.append(f"Last seen: {'today' if days == 0 else f'{days} days ago'}")
    top = Counter(key(h["cmd"]) for h in history[-200:] if h["cmd"].split()).most_common(3)
    if top:
        lines.append("Favourite commands lately: " + ", ".join(c for c, _ in top))
    return "\n".join(lines)


def ask(system, user, num_predict=60):
    body = json.dumps({
        "model": MODEL, "stream": False,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "options": {"temperature": 0.9, "num_predict": num_predict},
    }).encode()
    req = urllib.request.Request(ollama_url(), body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        text = json.load(r)["message"]["content"].strip().replace('"', "")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:2])[:220]


def omen(cmd, status):
    if status != 0:
        return random.choice(FAILED)
    words = cmd.split()
    return random.choice(OMENS.get(words[0], GENERIC) if words else GENERIC)


def whisper(cmd, status=0, rate=None, always=False):
    """Return what the ghost says, or None if it chooses to stay quiet."""
    history = load()
    recorded = record(cmd, status)
    if not recorded:
        return None
    if rate is None:
        rate = float(os.environ.get("POLTERGEIST_RATE", "0.8" if status else "0.3"))
    if not always and random.random() > rate:
        return None
    try:
        return ask(PERSONA, context(cmd, status, history))
    except ValueError as e:
        return f"({e})"
    except (urllib.error.URLError, OSError, KeyError, ValueError):
        return omen(cmd, status)  # no model, no internet, no problem


# ---------------------------------------------------------------- the ofrenda

def ofrenda(days=30, minimum=3, limit=5, history=None):
    """Commands you ran often but haven't touched in `days`: the ones you've lost."""
    history = load() if history is None else history
    cutoff = time.time() - days * 86400
    seen = {}
    for h in history:
        if not h["cmd"].split():
            continue
        s = seen.setdefault(key(h["cmd"]), {"n": 0, "last": 0, "example": h["cmd"]})
        s["n"] += 1
        if h["t"] >= s["last"]:
            s["last"], s["example"] = h["t"], h["cmd"]
    gone = [(k, s) for k, s in seen.items() if s["n"] >= minimum and s["last"] < cutoff]
    return sorted(gone, key=lambda kv: -kv[1]["n"])[:limit]


def epitaph(name, n, days_gone):
    user = f"Write a tender one-sentence remembrance, under 25 words, for the shell command '{name}', which the user ran {n} times but not for {days_gone} days."
    try:
        return ask("You write gentle, warm ofrenda epitaphs for retired shell commands. One sentence. No emojis.", user, 50)
    except (urllib.error.URLError, OSError, KeyError, ValueError):
        return f"You and `{name}` shared {n} small adventures. It remembers them still."


def render_ofrenda(entries, days):
    out = ["", "          \U0001F56F️   O F R E N D A   \U0001F56F️",
           "     for the commands that once kept you company", ""]
    if not entries:
        out.append(f"   Nothing has been lost yet. Every command is still alive (within {days} days).")
    for name, s in entries:
        gone = int((time.time() - s["last"]) / 86400)
        out += [f"   ✿  {s['example']}", f"      {s['n']} times in life, silent for {gone} days",
                f"      “{epitaph(name, s['n'], gone)}”", ""]
    out.append("   ✿ ✿ ✿  your history is the shape of who you were  ✿ ✿ ✿")
    return "\n".join(out)


# ---------------------------------------------------------------- possession

BASH = r'''
__poltergeist_last=""
__poltergeist_prompt() {
  local s=$? h
  h=$(HISTTIMEFORMAT= builtin history 1)
  if [[ "$h" != "$__poltergeist_last" ]]; then
    __poltergeist_last=$h
    [[ $h =~ ^[[:space:]]*[0-9]+[[:space:]]+(.*)$ ]] && ( %(py)s whisper --status "$s" -- "${BASH_REMATCH[1]}" >&2 & )
  fi
  return $s
}
PROMPT_COMMAND="__poltergeist_prompt${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
'''
ZSH = r'''
__poltergeist_preexec() { __poltergeist_cmd=$1 }
__poltergeist_precmd() {
  local s=$?
  [[ -n $__poltergeist_cmd ]] && ( %(py)s whisper --status "$s" -- "$__poltergeist_cmd" >&2 & )
  __poltergeist_cmd=
}
autoload -Uz add-zsh-hook
add-zsh-hook preexec __poltergeist_preexec
add-zsh-hook precmd __poltergeist_precmd
'''


def haunt(shell):
    py = f"{shlex.quote(sys.executable)} {shlex.quote(os.path.abspath(__file__))}"
    return (ZSH if shell == "zsh" else BASH) % {"py": py}


def main(argv=None):
    p = argparse.ArgumentParser(prog="poltergeist", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("haunt", help="print the shell hook; use with eval")
    h.add_argument("--shell", choices=["bash", "zsh"], default="zsh" if "zsh" in os.environ.get("SHELL", "") else "bash")
    w = sub.add_parser("whisper", help="record a command and maybe comment on it")
    w.add_argument("--status", type=int, default=0)
    w.add_argument("--always", action="store_true", help="never stay silent")
    w.add_argument("command", nargs=argparse.REMAINDER)
    o = sub.add_parser("ofrenda", help="an altar for commands you no longer run")
    o.add_argument("--days", type=int, default=30)
    o.add_argument("--min", type=int, default=3, dest="minimum")
    a = p.parse_args(argv)

    if a.cmd == "haunt":
        print(haunt(a.shell))
    elif a.cmd == "whisper":
        words = a.command[1:] if a.command[:1] == ["--"] else a.command
        msg = whisper(" ".join(words), a.status, always=a.always)
        if msg:
            print(f"\033[2;3m  \U0001F47B {msg}\033[0m", file=sys.stderr)
    else:
        print(render_ofrenda(ofrenda(a.days, a.minimum), a.days))


if __name__ == "__main__":
    main()
