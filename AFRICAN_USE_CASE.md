# African Use Case — why getdebug-edge, why here

*Backing document for the `african_alpha_claim` in `metadata.json` and the
Best African Use Case consideration.*

> **How to use the citation slots.** Every specific statistic below is marked
> `⟦CITE: what to find │ suggested source⟧`. Replace each with a real, sourced
> figure and a footnote before submitting — or delete the sentence. **Do not
> ship an unsourced number.** A technical judge distrusts a fabricated
> statistic instantly, and this whole project's credibility rests on honesty.
> Every qualitative claim (unmarked) is defensible as written.

---

## 1. The problem: critical software, built by the excluded

Across Africa, the systems people depend on — health, education, agriculture,
finance, government services — increasingly run on software. Mobile money alone
moves an enormous share of Sub-Saharan Africa's economy
⟦CITE: annual mobile-money transaction value in Sub-Saharan Africa │ GSMA "State
of the Industry Report on Mobile Money"⟧, and much of the software behind these
services is written not by large firms but by **small teams and solo
developers** — the group least able to afford the tooling that keeps code safe.

Poor-quality and insecure software is not a cosmetic problem. The global cost of
software defects runs to the trillions
⟦CITE: cost of poor software quality │ CISQ "The Cost of Poor Software Quality"⟧,
and a single data breach in finance or healthcare carries a heavy price
⟦CITE: average cost of a data breach, ideally finance/health or regional │
IBM/Ponemon "Cost of a Data Breach Report"⟧. Injection flaws — the exact class
getdebug-edge is tuned to catch — have remained among the most common and
damaging vulnerabilities for over a decade
⟦CITE: injection prevalence/ranking │ OWASP Top 10⟧.

The developers building Africa's critical software know this. What they lack is
a way to check their code that fits their reality.

## 2. The stakes, made concrete

Consider a small team building a clinical decision-support tool — say, software
that helps flag patients for cancer screening. The developer has no budget for a
code-security service, unreliable internet, and a legal duty not to send patient
data abroad. So the code ships with **no security or correctness review at all.**

Two outcomes follow, both bad. Either the team, aware of the risk, never ships —
and a useful tool doesn't reach the clinic that needed it. Or it ships with the
kind of bug a first pass would have caught — in software where the stakes are
human. Software this consequential deserves review. The teams building it often
can't get any.

*(Honest calibration: getdebug-edge is a first-pass triage that catches obvious,
dangerous mistakes and points a human at the code worth a closer look — not a
guarantee of correctness and not a substitute for a professional audit. Its
value is that it exists for developers who otherwise have nothing.)*

## 3. Why the tools that exist don't reach them — three walls

Every cloud code-review tool (CodeRabbit, Snyk, hosted SAST) assumes three
things that fail for most African developers:

- **Cost.** Per-seat pricing in US dollars, against revenue in cedis, naira, or
  shillings. A subscription can be a meaningful fraction of a junior
  developer's salary. And internet access itself is disproportionately
  expensive here ⟦CITE: cost of 1GB mobile data as % of average income in
  Africa │ A4AI / ITU affordability data⟧.
- **Connectivity.** Cloud-gated review assumes a fast, always-on connection.
  Intermittent power and metered data make "always online" aspirational.
- **Data residency.** Financial and health data is regulated. Sending the
  source that handles it to a foreign cloud is, under laws like Ghana's Data
  Protection Act, Nigeria's NDPR, and Kenya's Data Protection Act, somewhere
  between "needs legal review they can't afford" and "prohibited."

So the software in the highest-stakes sectors ships with the least review.

## 4. What getdebug-edge changes

On the laptop a developer already owns — an 8 GB, integrated-graphics machine,
the ADTC Standard Laptop profile — getdebug-edge is a pre-commit safety net:

- Point it at a project; minutes later a findings report flags the injection,
  the unvalidated input, the missing guard, the hardcoded secret — each with a
  suggested fix, and, when the developer supplies a `SPEC.md`, business-logic
  bugs checked against intended behavior.
- It runs **during** an outage. It costs **nothing** after a one-time ~1.7 GB
  download. The code **never leaves the room**, so the data-residency question
  never arises.
- Findings appear in VS Code's Problems panel — inside the tools teams already
  use.

The two `test_prompts` in `metadata.json` are not hypotheticals: a Ghanaian
mobile-money fee calculation that crashes on empty batches, and a school-fees
payment webhook with an injection flaw. They are the daily texture of this work.

## 5. Built small on purpose — accessibility as a design goal

getdebug-edge ships as a **3-bit quantized 3B model (~1.7 GB, ~2.6 GB RAM)**,
chosen over a larger quant after a measured sweep specifically because smaller
serves this user:

- **A smaller download** matters where data is metered and expensive — every
  gigabyte is real money.
- **Lower RAM** means it runs comfortably on 8 GB machines, and the model is
  small enough to run on a **modern smartphone** (6 GB+ RAM) via on-device LLM
  apps — putting the reviewer, quite literally, in a developer's pocket. *(The
  full agent is a desktop tool today; a mobile app is on the roadmap — the
  model already fits.)*
- **Power is the binding African constraint.** Where the grid is unreliable,
  laptops run on battery and heat matters — in rooms without air conditioning,
  on machines with tired fans. getdebug-edge's headline optimization (threads
  = physical cores) was chosen because it is simultaneously faster **and**
  cooler than the naive setting: strictly fewer joules per token, and no
  thermal throttling. Efficiency here isn't a benchmark flex; it's what lets
  the tool run at all.

## 6. Who this serves

The same three walls bind health-tech teams handling patient records in
Nairobi, govtech contractors in Kigali, fintech startups in Lagos, agri-tech
builders digitising smallholder supply chains, and students learning to code on
shared, metered bandwidth everywhere. The addressable user is not "developers
who prefer offline tools" — it is the **majority of the continent's
developers**, for whom offline-capable is the difference between having a
reviewer and having none.

Cloud AI review assumes the infrastructure Africa is still building.
getdebug-edge assumes only the laptop already on the desk — and soon, the phone
already in the pocket.

---

### Citation checklist (fill before submitting)

- [ ] Mobile-money scale (§1) — GSMA State of the Industry: Mobile Money
- [ ] Cost of poor software quality (§1) — CISQ report
- [ ] Cost of a data breach (§1) — IBM/Ponemon
- [ ] Injection prevalence (§1) — OWASP Top 10
- [ ] Mobile-data affordability (§3) — A4AI / ITU
- [ ] (Optional) A real African fintech/health breach or outage as a concrete
      opening anecdote — strengthens §2 more than any statistic

Each becomes a numbered footnote or an inline link. Keep them few and real.
