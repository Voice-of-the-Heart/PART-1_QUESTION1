---
title: "Building GIS Capability in the Counterpart Department"
subtitle: "A capability development response, not a training plan"
date: "31 July 2026"
geometry: margin=2.1cm
fontsize: 10.5pt
---

*Body: 6 pages (this page limit). Annexes A–C follow, excluded from the limit per the brief.*

A team that loses delivery capacity to two resignations is a team where knowledge was never
written down. The counterpart department has the same fault line: its lowest measured
competency is documenting a reproducible workflow, which means the work lives in individuals,
not in the organisation. I am treating capability-building and documentation as one task, not
two, and I am making that call as the person who will own the outcome, not just deliver the
week — every design choice below moves knowledge out of people and into procedures the
department keeps when someone leaves.

## 1. What the evidence actually tells me

Three findings, and three decisions that follow directly from them — this is the difference
between a training plan and a capability plan: the second treats evidence as a constraint on
design, not as background colour.

| Finding | What it rules out | What it requires |
|---|---|---|
| Self-rating vs. tested score correlation = 0.11 (no relationship); mean score 36–57% depending on measure | Using stated demand or confidence to decide content — people cannot report what they don't know they lack | Content set by measured gaps only; every topic opens with a task people attempt cold, so belief meets ability early and privately |
| Confident staff meeting a task they can't do tend to disengage to protect face | A conventional Day-1 pre-test read aloud, scored publicly | Day 1 opens as private, no-scores-aloud calibration, framed as closing a *shared* gap, not exposing individuals |
| 0 of 21 staff have QGIS/ArcGIS access | Running the course as scheduled if software isn't installed and tested first | Software installation becomes a **precondition**, not a parallel administrative task (Section 6) |

The decision I want to be explicit about, because it is the one a training coordinator would not
make and a capability coordinator must: **if software access slips, I recommend delaying the
course rather than spending the budget.** Skills not practised within days of learning decay
fast; a five-day course into a zero-software environment produces a certificate and nothing the
department can use. That is a resourcing call I would take to whoever owns the budget before
Day 1, not a caveat buried in a risk log — a senior coordinator's job is to make that trade-off
visible and defend it, not to let the course run and let the failure surface quietly at 90 days.

**Why this is a coordination problem, not a training problem.** A department where competence
lives in two or three individuals has a bus-factor problem it does not know it has — the 0.11
correlation above means management cannot even rely on staff to flag who those individuals are.
Treating this as a training gap fixes the wrong layer: it improves individuals without changing
the organisation's exposure. Everything from here — the level-4 "Steward" tier, the
peer-reproduction exercise, the workflow-log requirement on every real assignment — is aimed
at the organisational layer, on the assumption that I am accountable for departmental continuity,
not for a course-completion count.

## 2. Competency framework

Generic beginner/intermediate/advanced labels are useless here precisely because self-labels
don't predict ability. Each level below is defined by behaviour a supervisor can observe and
verify — not by time served, and not by self-report.

| Level | Behaviour a supervisor can observe |
|---|---|
| **1 · Assisted** | Follows a written procedure with guidance; imports data, logs actions, asks for help at the right points |
| **2 · Supported** | Cleans data and runs a basic join unaided; applies documented workflows consistently; spots obvious errors |
| **3 · Independent** | Chooses the right method, validates results, writes metadata, produces work another officer can repeat |
| **4 · Steward** | Writes/updates SOPs, reviews colleagues' work, mentors, sets quality standards — strengthens the *department's* capability, not just their own |

Six domains (data acquisition, data management/documentation, analysis, cartography, QA/
governance, knowledge sharing) are scored against this ladder; the full matrix is Annex A.
Progression requires evidence from **three separate pieces of work**, not one good day — this
is a governance choice as much as a pedagogical one: it stops a single strong submission from
inflating a competency record that a manager will later rely on for a staffing decision.

## 3. The five-day course

One rule: build competence before complexity. A baseline of 36/100 means the job is to make
people solid on the core workflow, not to expose them to techniques they cannot yet support in
production. Hands-on-to-instruction ratio is **70:30** — adults build technical skill by doing the
task and getting immediate correction, not by watching slides, and every hour of instruction I
authorise has to justify itself against that ratio.

| Day | Focus | Outcome | Exercise |
|---|---|---|---|
| 1 | Foundations & data quality | Apply validation rules; correct attribute errors | Clean a flawed facility register |
| 2 | **Reproducible workflows** (weakest skill) | Document a full cleaning procedure; peer-reproduce it | Swap files, reproduce a colleague's result |
| 3 | Spatial analysis for decisions | Apply joins; interpret result for service delivery | Find wards under-served by facilities |
| 4 | Cartography & QA | Design a readable map; evaluate against a checklist | Produce and peer-review a coverage map |
| 5 | End-to-end departmental case | Work a real request unaided; write an evidence note | Raw data → map → one-page finding, assessed |

Day 2 carries the most weight deliberately: workflow documentation is both the weakest
measured skill and the one that determines whether the department survives staff turnover.
Day 4 is placed *after* data work on purpose — a polished map built on uncleaned data is worse
than no map, and staff need to internalise that ordering before they're trusted with cartography
they already over-value relative to its inputs.

## 4. What I am deliberately not teaching

| Left out | Reason |
|---|---|
| Spatial statistics | Meaningless without reliable data and interpretation skill first |
| Remote sensing | Needs stronger fundamentals and software the department doesn't have |
| Python / automation | Automating a workflow you can't yet do by hand only automates the mistakes |
| Web GIS / dashboards | Sequenced after desktop competence and clean data are established |
| Machine learning, drone mapping | Outside the department's routine work; not a current need |

The same discipline I apply to *stated* demand applies here: depth in what the department
actually uses beats a thin, impressive-looking tour of what it cannot yet sustain. Cutting this
list is itself a coordinator decision — every one of these is something a stakeholder may ask
for by name, and part of the role is holding the line on sequencing against that pressure.

## 5. Assessment: measuring capability, not confidence

Because confidence doesn't predict ability here, both pre- and post-course sittings use the
identical six-task practical instrument (100 marks: import/CRS 10, clean/validate 25, log &
metadata 20, analysis 20, cartography 15, interpretation note 10), scored 0–5 per task against a
fixed rubric. The post-test uses a matched dataset — same size, same error categories, same
difficulty, different values — so a gain reflects learning, not memorised answers. Full item
wording and rubric: **Annex C**; a ready-to-deliver 90-minute session on the weakest domain
(reproducible cleaning), designed so a colleague can run it without me in the room, is **Annex
B**.

One design choice I want to flag as coordinator-level rather than trainer-level: **results are
reported as a distribution (lowest/median/highest), never a single mean.** An average hides
exactly the people a capability programme exists to catch. If I am accountable for whether this
department can function without external support, I need to know who is still below the
independent-work threshold at Day 5, not that the cohort average looks acceptable.

## 6. The 90 days after the course — where capability actually gets decided

The course is the smaller half of this plan. Capability counts once people do real departmental
work to standard, unsupervised. Four things run in parallel, and I hold a specific owner
accountable for each rather than leaving them as shared aspirations:

- **Fix the software constraint first (before Day 1, non-negotiable).** QGIS LTR — free, no
  licensing barrier — installed and tested on every workstation, a named IT contact, a shared
  data folder. If this slips, the course slips; I would rather move the start date than run the
  course into an environment that guarantees the skill decays within a week.
- **Days 1–30 — real work, not more exercises.** Each officer completes ≥2 genuine
  departmental assignments using the standard templates; every submission arrives with its
  workflow log, metadata, QA check and supervisor sign-off. This is what converts a taught
  skill into a departmental habit rather than a course memory.
- **Days 31–60 — structured transfer.** Fortnightly mentoring pairs, a monthly problem clinic,
  peer review against the same QA checklist used in training.
- **Days 61–90 — independent delivery + feedback loop.** A short lessons-learned session
  updates the SOPs — the department's documentation improves *because* the course ran, not
  just the people.

| Measure | Baseline | 90-day target |
|---|---:|---:|
| Staff with working GIS software | 0 / 21 | 21 / 21 |
| Documentation competency | 1.5 / 5 | ≥ 4 / 5 |
| Demonstrated capability (re-test) | 36 / 100 | ≥ 75 / 100 |
| Real assignments delivered to standard | 0 | 2 per officer |
| Outputs passing QA on first submission | not yet tracked | ≥ 80% |
| Staff able to mentor a colleague | 0 | ≥ 4 / 21 |

**Risk ownership, stated plainly rather than left generic:** the three failure modes that quietly
kill programmes like this are software slipping, management not protecting practice time, and
staff drifting back to undocumented habits once the facilitator leaves. Each has a named
counter built into the design above, not a mitigation note appended afterward: install-before-
train removes the first; getting management to ring-fence practice time *before* the course
starts (a conversation I would have at the budget-approval stage, not after Day 5) removes the
second; making documented workflow and sign-off the *normal* way work is submitted — not an
optional extra reviewed later — removes the third.

**Accountability, named rather than shared.** A plan with no named owner per line item is a
wish list; I would not present this to my own management as one.

| Risk / dependency | Owner | Escalation trigger |
|---|---|---|
| Software not installed/tested | Department IT contact, confirmed by me | Any workstation untested 5 working days before Day 1 → I escalate to the department head directly |
| Practice time not ring-fenced | Line supervisors, agreed before Day 1 | An officer misses their Day-30 assignment count → raised at the fortnightly mentoring check, not left to the 90-day review |
| Workflow log/sign-off skipped on real work | Supervisor sign-off, spot-checked by me | Any submission without a log is returned unsubmitted, no exception |
| Cohort member still below Level 2 at Day 90 | Named mentor pair | Individual coaching plan, not folded into the average and forgotten |

## Closing

**Beyond 90 days.** The 90-day plan closes with an SOP update, not a handover to nobody — the
Level-4 Stewards identified during the course become the standing owners of those SOPs, and
the department's own QA checklist (not an external consultant) becomes the mechanism that
keeps standards from drifting once this engagement ends. That is the actual exit criterion: not
that I have delivered a course, but that the department no longer needs me to keep its own
workflow alive.

The department's real problem is not that people cannot make maps. It is that the work is
undocumented and lives in individuals, which is exactly what makes a team fragile when
someone leaves — the same fragility a two-resignation crisis exposes anywhere. Every part of
this design pushes one direction: get the tools in place first, teach the core workflow well,
write everything down in a form someone else can repeat, and prove the skill on real work
within ninety days. That last test — not the certificate, not the course-week satisfaction score
— is the only one I would stand behind in front of the department's own management.

<div style="page-break-before: always;"></div>

# Annex A: Competency framework in full

Six domains, each scored against the four-level ladder in Section 2. Moving up a level requires
evidence from at least three separate pieces of work.

| Domain | Covers | Why it matters |
|---|---|---|
| Data acquisition & validation | Collecting and checking spatial/attribute data | Reliable inputs — everything downstream depends on it |
| Data management & documentation | Cleaning, organising, versioning, documenting | Reproducibility and institutional memory |
| GIS analysis | Applying the right spatial method | Turns data into evidence for decisions |
| Cartography & communication | Clear, accurate maps and findings | Makes the work usable by managers |
| QA and governance | QA/QC, metadata standards, SOPs | Consistency, transparency, auditability |
| Collaboration & knowledge sharing | Documenting, reviewing, mentoring | Resilience — reduces dependence on individuals |

| Domain | L1 Assisted | L2 Supported | L3 Independent | L4 Steward |
|---|---|---|---|---|
| Data acquisition | Imports via SOP | Validates unaided | Designs the checks | Sets dept. standards |
| Data cleaning | Cleans with guidance | Cleans independently | Optimises the workflow | Improves org. workflow |
| Analysis | Runs a guided analysis | Picks the right tool | Produces decision-ready analysis | Reviews others' methods |
| Cartography | Produces a basic map | Produces a finished map | Advises on visualisation | Sets mapping standards |
| QA and metadata | Completes a checklist | Applies QA consistently | Reviews others' work | Updates QA standards |
| Knowledge sharing | Documents own work | Shares workflows | Mentors colleagues | Leads the practice group |

# Annex B: Ninety-minute session, ready for someone else to deliver

**Session:** Building a reproducible data-cleaning workflow · **Duration:** 90 min · **Domain:**
Data management and documentation · **Target:** Level 2, Supported Practitioner

The baseline found documentation the weakest skill (1.5/5). This session fixes the department's
highest organisational risk — cleaning work nobody else can repeat. By the end, a participant
has both cleaned a dataset and documented it well enough for a colleague to reproduce the exact
result from the write-up alone.

**Learning outcomes:** explain in one sentence why a repeatable workflow matters more than a
fast one; clean a health-facility dataset using an agreed sequence; record every step in the
standard workflow log and metadata sheet; reproduce a colleague's result from their
documentation alone and give QA feedback.

**Materials:** per participant — laptop with QGIS, exercise dataset, workflow log template,
metadata template, QA checklist, USB backup. Facilitator — projector, demonstration machine,
this guide.

**Dataset:** "District Health Facilities" — 250 facility records, 18 ward boundaries, 460 road
segments, 1,200 settlement points, EPSG:4326. Planted defects mirror real partner-supplied
data: duplicate facility IDs, spelling variants of the same facility, missing coordinates, null
attributes, invalid facility types, inconsistent capitalisation, a few wrong ward codes.

| Time | Stage | Facilitator action |
|---|---|---|
| 0–10 min | Why we're here | Ask: "If another officer had to update this in six months, could they, without you?" Documentation is organisational memory, not paperwork. |
| 10–20 min | Demonstration | One cycle only — open data, spot an error, fix it, log it immediately. Do not clean the whole file for them. |
| 20–60 min | They do it | Participants clean and log as they go. Circulate constantly; help only when stuck; never take the keyboard. Prompt with "how did you decide that?", not "that's wrong." |
| 60–75 min | Peer reproduction | Swap machines; reproduce a colleague's output from documentation alone; note exactly where it breaks. |
| 75–90 min | Debrief | Which errors needed judgement; where documentation fell short; capture recurring errors for later coaching. |

**Exercise brief to participants:** "The M&E unit has received a facility dataset combined from
several implementing partners. Before it can be used for quarterly reporting it must be cleaned,
validated and documented so the result can be reproduced. Import the data into QGIS; work on a
copy, never the original; find and fix the data-quality problems; remove duplicates;
standardise facility names; fill missing values where you reliably can; save the cleaned layer;
complete the workflow log and metadata sheet as you go. You have 40 minutes."

**Model answer:** import and confirm CRS; make a working copy before editing; remove
duplicate facility IDs; standardise spelling/capitalisation against an agreed name list; correct
invalid facility types; fill missing ward codes from the boundary layer where possible and flag
the rest; validate coordinates against ward boundaries; log each action with a short reason; complete
metadata. Order can vary — marks are for a reproducible result, not one fixed sequence.

| Error expected | Facilitator response |
|---|---|
| Editing the original file directly | Stop; show how to make a working copy first; explain why the source stays untouched |
| Cleaning everything, then writing up at the end | Redirect to logging each step as it happens |
| Metadata left half-empty | Point back to the checklist; ask for the missing fields |
| Deleting duplicates with no reason recorded | Ask them to justify each removal in the log — "looked wrong" is not a reason |
| Inconsistent naming decisions | Introduce the standard name list |

**Scoring (100):** identifies errors 20 · cleans accurately 20 · workflow log complete 20 ·
metadata complete 15 · result reproducible by a peer 20 · takes part in peer review 5.

# Annex C: Pre- and post-course instrument

Both sittings are identical in structure, marked with the same rubric. The post-test uses matched
dataset "B" (same record count, error categories and difficulty as "A", different values) so
gains reflect learning, not memory. Re-run at 90 days to test whether capability held once
people were back on real work.

| Item | Task | Marks |
|---|---|---:|
| 1 | Import three layers and confirm the coordinate system | 10 |
| 2 | Identify and correct duplicates, nulls, inconsistent names, wrong categories; save the cleaned layer | 25 |
| 3 | Complete the workflow log, metadata sheet and QA checklist | 20 |
| 4 | Determine which facilities fall outside a stated service distance (distance and source given, not asserted) | 20 |
| 5 | Produce a finished map — title, legend, scale, north arrow, sensible symbology | 15 |
| 6 | Write a one-page interpretation of the result for a manager | 10 |

**Rubric per item (0–5), then weighted to the marks above:**

| Score | Meaning |
|---:|---|
| 0 | Not demonstrated / incomplete |
| 1 | Major errors, needs substantial help |
| 2 | Partial, correct only with significant guidance |
| 3 | Correct with minor errors |
| 4 | Correct and independent |
| 5 | Correct, independent, well documented and quality-assured |

Results are reported as a distribution (lowest, median, highest, share reaching each band) across
the 21 staff, never a single mean, so weak performers stay visible.

| Score | Interpretation |
|---:|---|
| 0–39 | Needs close supervision |
| 40–59 | Handles routine work with help |
| 60–79 | Works independently |
| 80–100 | Can mentor others |
