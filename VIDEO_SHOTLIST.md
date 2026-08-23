# getdebug-edge — 2-minute video shot list (record-and-follow)

Turnkey plan for **narrating + screen-recording yourself**. Target length **≤ 2:00**
(hard cap). The v3 script text lives in `SUBMISSION.md` (§"2-minute video script");
this file maps each line to an exact on-screen action + command + timing, using
only demo beats that are **proven to work reliably on the shipping Q3 model**.

---

## Pre-flight checklist (do this once, before recording)

- [ ] **Terminal font large** (18–22pt) and a wide window — judges watch on laptops/phones.
- [ ] **Warm the cache** so on-camera runs are fast: run each demo command once now.
      The result cache means the second (recorded) run returns findings in seconds
      instead of ~30–60s of inference. Warm-up commands:
      ```bash
      python3 agent/agent.py --target demo --out demo/findings.json --diagnostics --no-lint
      python3 agent/agent.py --prompt "Review this Express webhook for security bugs:

      app.post('/webhook/payment', (req, res) => {
        const { studentId, amount } = req.body;
        const q = \`UPDATE fees SET paid = paid + \${amount} WHERE student_id = '\${studentId}'\`;
        db.query(q);
        res.send('ok');
      });"
      ```
- [ ] **VS Code open** on the `getdebug-edge` folder, `demo/momo_payment.py` visible,
      Problems panel cleared (View → Problems, or `Cmd+Shift+M`).
- [ ] **Airplane mode ON** (or Wi-Fi visibly off) — this is the whole thesis; show it.
- [ ] Close Slack/email/other apps (clean screen + lower RAM = cooler run).
- [ ] Have `submission_q3.json` open in a tab for the proof shot (RAM / accuracy / no-throttle).
- [ ] The demo file's `sk_live_...` key is **fake** — safe to show on camera.

---

## Beat-by-beat (script line → screen → action)

### 0:00–0:18 · Problem  (talking head, or a budget laptop on the desk)
- **Narrate:** *"Cloud AI code reviewers are excellent — if you have fast internet, a
  company card, and permission to send your code abroad. Most African developers have
  none of those. getdebug-edge is security-first code review that runs entirely on the
  laptops we actually have: free, offline, private."*
- **On screen:** you (or the laptop). No terminal yet.
- **Tip:** end this beat by turning **airplane mode ON** on camera — visual proof of "offline."

### 0:18–1:05 · Live demo  (screen capture)  ← the core; two reliable beats

**Beat A — the deterministic hybrid (Problems panel):**
- **Action:** In VS Code, `Cmd+Shift+P` → **Run Task** → **"getdebug-edge: review demo"**
  (this task is pre-wired in `.vscode/tasks.json`).
- **On screen:** the **Problems panel fills with three real issues**, each clickable to the line:
  - `error` · **Hardcoded secret in source (Stripe live secret key)** · line 6
  - `error` · **Weak hash (MD5) used** · line 11
  - `warning` · **Sensitive data written to logs** · line 22
- **Narrate:** *"This is a budget laptop with no internet. I point it at a fintech
  project and a 3-billion-parameter model running locally reviews it — while
  deterministic detectors instantly catch a hardcoded live payment key, MD5 password
  hashing, and a PIN written to logs. They land in VS Code's Problems panel, clickable
  straight to the line."*
- **Why this beat:** these three are **deterministic** — identical every take, correct labels.

**Beat B — the model reasoning (SQL injection):**
- **Action:** in the terminal, run the `--prompt` webhook command (the warm-up one above,
  or point at `demo/momo_payment.py`).
- **On screen:** the model **explains the SQL injection in plain English and shows the
  parameterized-query fix.**
- **Narrate:** *"And the model itself reasons about the code — here it catches the SQL
  injection in the payment handler and writes the corrected, parameterized query."*
- **Tip:** let ~5–8 seconds of output stream, then cut. Don't wait for the full response.

### 1:05–1:40 · Engineering  (cutaways to charts / terminal)
- **Narrate:** *"Everything is tuned to an 8-gigabyte, CPU-only budget. I benchmarked
  six open models, ship a 3-bit quantization, and found that using physical cores
  instead of hyperthreads made it 25% faster AND 27 degrees cooler — an energy win
  where the grid is the constraint. The contest's own profiler confirms it: just 1.8
  gigabytes of RAM, no crash, no throttling."*
- **On screen (pick 2–3):**
  - `submission_q3.json` — highlight `memory.peak_rss_mb: 1840`, `cpu_thermal.throttled: false`,
    `accuracy … 0.80`.
  - `BAKEOFF.md` table (six models) or `REPORT.md` quant-sweep table.
  - Optional: the physical-core vs all-threads numbers from `SCOPE.md` (14.7 t/s @ 98.7°C
    vs 18.2 t/s @ 68.8°C).

### 1:40–2:00 · Honesty + impact
- **Narrate:** *"I measured the tool honestly — on my own benchmark it catches around 86%
  of seeded bugs, and I report its false-positive rate too, because a security tool
  should. It's a first-pass safety net with no cloud bill and no data leaving the
  machine. Free and open-source, built for the hardware Africa actually has."*
- **On screen:** `REPORT.md` recall table (82% model / 86% tool), then the GitHub repo page.
- **⚠️ Do NOT** conflate the 86% (our code-review recall) with the profiler's 0.80
  (arc_easy). If you show a number, show the 86%/82% and call it *our benchmark*.

---

## Proof shots to capture (stills, for the Devpost gallery)
1. **Problems panel** with the three findings (Beat A).
2. **`submission_q3.json`** — RAM 1.84 GB, throttled=false, accuracy 0.80.
3. **Airplane-mode toggle** mid-review (offline proof).
4. **The model's SQLi explanation + fix** (Beat B prose).
5. Terminal line: `Scanned 1 files … 1 chunk(s) flagged.` after the demo run.

## Timing sanity
Script ≈ 260 words. At a natural ~140 wpm that's **~1:51** — under the 2:00 cap with
room for pauses. If you run long, trim the engineering beat to two charts.

## Recording notes
- Screen-record at 1080p; keep the terminal/VS Code at high contrast (light theme reads
  best when compressed).
- One take per beat is fine — stitch in your editor. The demo beats are fast because the
  cache is warm.
- Add burned-in captions if you can (accessibility + judges often watch muted).
