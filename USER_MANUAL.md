# getdebug-edge — User Manual

A step-by-step guide to setting up and running getdebug-edge, written so that
someone who has never used a terminal-based AI tool can follow it. getdebug-edge
reviews your code for bugs and security problems **entirely on your own laptop**
— nothing is uploaded anywhere, no account, no API key, no internet needed after
the one-time setup.

---

## What you need

- A laptop with **8 GB of RAM or more** (the tool itself stays under 4 GB)
- **Ubuntu 22.04** (or newer), macOS, or another Linux
- About **3 GB of free disk space**
- An internet connection **for setup only** — after that, everything is offline

---

## Step 1 — Install the build tools (one time)

Open a terminal (on Ubuntu: press `Ctrl+Alt+T`) and paste:

```bash
sudo apt update && sudo apt install -y build-essential cmake git python3 curl
```

On macOS, install [Homebrew](https://brew.sh) instead, then run
`brew install llama.cpp` and skip to Step 3.

## Step 2 — Install llama.cpp (the engine that runs the AI model)

Paste these four commands one at a time:

```bash
git clone https://github.com/ggml-org/llama.cpp
cmake -S llama.cpp -B llama.cpp/build -DGGML_NATIVE=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build --config Release -j
sudo cp llama.cpp/build/bin/llama-server llama.cpp/build/bin/llama-bench /usr/local/bin/
```

The third command compiles the engine for **your exact CPU**, which makes it
noticeably faster than a generic download. It can take 5–15 minutes — that is
normal.

Check it worked:

```bash
llama-server --version
```

You should see a version number, not "command not found".

## Step 3 — Get getdebug-edge and the AI model

```bash
git clone https://github.com/YOUR_GITHUB/getdebug-edge   # or unzip the release
cd getdebug-edge
bash download_model.sh
```

The model is about **2.1 GB** — on a slow connection this is the long step.
It only ever happens once. After this, you can disconnect from the internet
entirely and everything still works.

## Step 4 — Review your first project

```bash
python3 agent/agent.py --target /path/to/your/project --out findings.json
```

Replace `/path/to/your/project` with the folder of code you want reviewed
(for example `~/school-portal`). The tool will:

1. Start the AI model on your laptop (takes a few seconds)
2. Read your code files one piece at a time
3. Write everything it finds into `findings.json`

Each finding looks like:

```
- [high] SQL query built by string concatenation — fix: use parameterized queries
```

`high` means fix it before you ship. `medium` means fix it soon. `low` is a
suggestion.

### Ask a one-off question instead

```bash
python3 agent/agent.py --prompt "Why does this crash? def average(xs): return sum(xs)/len(xs)"
```

### Get explanations in another language

```bash
python3 agent/agent.py --target ~/my-project --lang French --out findings.json
```

The explanations switch language; the code itself and the severity tags stay in
English. **This is experimental and best-effort on a 3B model:** output quality
varies, and on the shipping model it frequently falls back to English —
African-language output in particular is unreliable (measured word-salad on
Swahili; see `BAKEOFF.md`). Don't depend on it; proper local-language support is
a roadmap item (see `SCOPE.md` §7b).

### Catch business-logic bugs by describing how the app should work

Some bugs aren't about syntax or security — they're about the code doing the
*wrong thing*. A discount that accidentally increases a balance, or a "reserve"
that lets you take more stock than exists, looks perfectly valid to any tool
that doesn't know what the code is *supposed* to do.

Tell it. Write a short plain-language description of intended behavior in a file
called **`SPEC.md`** at the root of the project you're reviewing (or pass
`--spec path/to/spec.md`):

```text
apply_discount reduces a balance by a percentage between 0 and 100.
A discount must never increase the balance.

reserve() must never let the reserved quantity exceed available stock.

A user may only retrieve their own orders.
```

The reviewer then checks your code **against your rules** and flags where they're
violated. In our testing this surfaced business-logic bugs that were otherwise
missed — for example, it caught a discount function that mishandled negative
percentages and a stock check that allowed overselling. It's most effective
when the spec is specific about limits, ownership, and what must never happen.

*Honest note:* this depends on the quality of your spec, and it's a first-pass
aid — confirm each finding. It doesn't guarantee every logic bug is caught.

---

## Getting the best results (important!)

1. **Plug the laptop in.** On battery, the CPU slows itself down and reviews
   take much longer.
2. **Close heavy apps** (browser with many tabs, video calls) — the tool wants
   your CPU and ~4 GB of RAM to itself.
3. **Don't touch the thread setting.** The tool automatically uses your
   *physical* CPU cores, which we measured to be both the fastest AND coolest
   setting. Forcing more threads makes it slower and hotter.
4. **Put the laptop on a hard surface**, not a blanket or your lap — airflow
   keeps the CPU from throttling on long reviews.
5. **Review one project at a time.** Pointing it at your whole home directory
   will work, but will take hours.
6. **Install a linter for even better results** (optional):
   `pip install ruff` — the tool automatically feeds linter hints to the AI,
   which improves what it catches. It works fine without this.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `llama-server not found` | Step 2 didn't finish — rerun the `sudo cp ...` command |
| `Model not found at model/...` | Run `bash download_model.sh` from inside the getdebug-edge folder |
| Review is very slow | Plug in the power cable; close other apps; make sure you didn't pass a huge `--threads` value |
| Laptop gets hot / fans loud | Normal during a review, but it should NOT throttle — we measured 71°C peak on an 8-core machine. Hard surface + power cable helps |
| `findings.json` is empty / no issues | Either your code is clean, or the files aren't in a supported language (`.py .js .ts .go .rs .java .rb .php .c .cpp .cs .sql` and more) |
| Something else | Run again with `--verbose` and read what the model actually said |

## Using it with VS Code

Three levels, pick what suits you:

**1. Just use the built-in terminal.** `` Ctrl+` `` opens VS Code's terminal —
every command in this manual works there as-is.

**2. One-keystroke reviews with findings in the Problems panel.** Create
`.vscode/tasks.json` in your project:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "getdebug-edge: review project",
      "type": "shell",
      "command": "python3 /path/to/getdebug-edge/agent/agent.py --target ${workspaceFolder} --out ${workspaceFolder}/findings.json --diagnostics",
      "problemMatcher": {
        "owner": "getdebug-edge",
        "fileLocation": "absolute",
        "pattern": {
          "regexp": "^(.+):(\\d+): (error|warning|info): (.*)$",
          "file": 1, "line": 2, "severity": 3, "message": 4
        }
      }
    }
  ]
}
```

Then `Ctrl+Shift+P` → "Run Task" → "getdebug-edge: review project". Findings
appear in the **Problems** tab, clickable straight to the flagged line. (Line
numbers are the model's best estimate, so they may be a line or two off.)

**3. Chat with the model inside the editor.** `llama-server` speaks the
OpenAI-compatible API, so extensions like Continue or Cline can use your local
model. Start the server yourself:

```bash
llama-server -m /path/to/getdebug-edge/model/getdebug-edge-3b-q4_k_m.gguf \
  --ctx-size 3072 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 \
  --n-gpu-layers 0 --port 8080
```

then point the extension at `http://127.0.0.1:8080/v1` (API key: anything,
model name: anything). Fully offline, same model, now with an editor chat UI.

## What this tool is (and isn't)

getdebug-edge is a **code reviewer / static analysis assistant**: it reads your
code and flags bugs, vulnerabilities, and correctness issues with suggested
fixes, and it can answer one-off debugging questions with `--prompt`. It is not
a step-through debugger (no breakpoints, no variable inspection) and it does
not edit your files — you stay in control of every change.
