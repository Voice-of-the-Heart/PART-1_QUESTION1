# Question 6 — Building GIS Capability in the Counterpart Department

Written-response deliverable only (no code/data pipeline — this question is a
capability-development design, not a technical analysis).

- `Q6_RESPONSE.pdf` — the submission: body kept to 6 pages per the stated
  limit (currently 4 of 6 used), with Annexes A–C (competency matrix,
  ready-to-deliver 90-minute session, pre/post assessment instrument)
  following, excluded from the page limit as instructed.
- `Q6_RESPONSE.md` — source markdown for the above.
- `style.css` — stylesheet used to render it.

## Rebuilding the PDF

```bash
pandoc Q6_RESPONSE.md -o Q6_RESPONSE.pdf --pdf-engine=wkhtmltopdf \
  --css=style.css --standalone \
  --pdf-engine-opt=--margin-top --pdf-engine-opt=18mm \
  --pdf-engine-opt=--margin-bottom --pdf-engine-opt=16mm \
  --pdf-engine-opt=--margin-left --pdf-engine-opt=20mm \
  --pdf-engine-opt=--margin-right --pdf-engine-opt=20mm
```

Requires `pandoc` and `wkhtmltopdf` on PATH.
