# African Use Case — why this tool, why here, why offline

*Backing document for the `african_alpha_claim` in `metadata.json`.*

## The user

Kwame runs a three-person software team in Accra. Their product moves school
fees over mobile money: parents pay through MTN MoMo and Telecel Cash, the
system reconciles payments against student accounts, and a webhook from the
payment provider updates balances. Their stack is Node.js and Python. Their
customers are schools; their regulator is the Bank of Ghana.

Kwame's team has no code reviewer. Every AI review tool they have evaluated
fails on one of three walls:

1. **Cost** — per-seat SaaS priced in dollars, against revenue in cedis. A
   $30/seat/month reviewer is a meaningful fraction of a junior developer's
   salary.
2. **Connectivity** — their office internet fails often enough that a
   cloud-gated CI step becomes a work stoppage. Load-shedding and data caps
   make "always-online" tooling aspirational.
3. **Data residency** — fee records are financial data about children.
   Sending the codebase that handles them to a US-hosted LLM is somewhere
   between "requires legal review they can't afford" and "prohibited."

So the code that moves school fees for thousands of families ships with no
security review at all. That is the actual, common state of software built
by small teams across the continent — in exactly the sectors (payments,
health records, government services) where the cost of a SQL injection is
highest.

## What getdebug-edge changes

On the laptop Kwame already owns (an 8 GB, integrated-graphics machine — the
ADTC Standard Laptop profile is his machine), getdebug-edge gives his team a
pre-commit safety net:

- `python3 agent/agent.py --target ./fees-service` before each release —
  minutes later, a findings report flagging the injection, the unvalidated
  webhook input, the missing empty-batch guard, each with a suggested fix.
- It runs **during** the outage. It costs **nothing** after a one-time 2 GB
  download. The code **never leaves the room**, so the data-residency
  question doesn't arise.
- Findings surface in VS Code's Problems panel — inside the tool his team
  already uses.

The two `test_prompts` in `metadata.json` are not hypotheticals: a
mobile-money fee calculation that crashes on the first empty batch after
midnight, and a school-fees payment webhook with an injection flaw. They are
the daily texture of this codebase.

## Why the engineering choices are African choices

- **Power is the binding constraint.** Where the grid is unreliable,
  laptops run on battery and heat matters (rooms without air conditioning,
  machines with tired fans). Our headline optimization — threads = physical
  cores — was chosen because it is simultaneously ~25% faster **and** ~27°C
  cooler than the naive setting: strictly fewer joules per token. The
  inter-chunk pacing option exists for the same reason.
- **Storage and bandwidth respect.** One 2.1 GB download, once. No
  telemetry, no update checks, no phone-home.
- **Zero-dependency install.** The agent is Python standard library only —
  nothing to `pip install` on a machine that may not reach PyPI today.
- **Language reach, honestly stated.** `--lang` lets the model explain
  findings in the user's language (code and severity tags stay in English).
  We measured rather than claimed: at this model size, Swahili is partially
  served and Ghanaian languages are not yet — so the African Language
  multiplier is *not* claimed, and the roadmap (SCOPE.md §7b) names the
  honest path: offline translation models and GhanaNLP/Khaya integration as
  an opt-in online mode, post-contest.

## Who else this serves

The same three walls — cost, connectivity, residency — bind health-tech
teams handling patient records in Nairobi, govtech contractors in Kigali,
fintech startups in Lagos, and university students learning to code on
shared bandwidth everywhere. The addressable user is not "developers who
prefer offline tools"; it is the majority of the continent's developers,
for whom offline-capable is the difference between having a reviewer and
not having one.

Cloud AI review assumes infrastructure Africa is still building. This tool
assumes only the laptop that is already on the desk.
