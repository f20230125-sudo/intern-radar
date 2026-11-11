# Intern Radar

Student roles at UAE employers, read every hour from the employers' own career systems.

Internships, graduate programmes and first jobs are listed newest first. Open a role and each fact (who can
apply, start, length, pay, stage of study, where you work, closing date) sits beside the sentence it was read
from, with the deciding words underlined. A fact the posting does not state is shown as "not stated", never
guessed.

Numbers below are from a run on 11 Nov 2026.

| | |
|---|---|
| Employers read | 80 (82 job boards) |
| Roles they list in the UAE | 672 |
| Student roles open | 58: 35 internships, 11 graduate programmes, 12 first jobs |
| Requests per hourly run | 205 when nothing has changed; about 510 when every posting is re-read |
| Model calls | none |

## How it works

```
data/companies.yaml          the employers watched: system and board id
src/radar/sources/           one adapter per career system (Greenhouse, Lever, Ashby, Workable, Workday, amazon.jobs)
src/radar/place.py           is the posting in the UAE, and in which emirate
src/radar/kind.py            internship, graduate programme, first job, or not a student role
src/radar/facts.py           the seven facts, each with its sentence and the words that decided it
src/radar/skills.py          skills a posting names, from a fixed list
src/radar/state.py           memory across runs: first seen, changed, closed, reopened
src/radar/run.py             one run: read every board, fold into memory, write the snapshot
src/radar/discover.py        find which employers have a readable board with UAE roles
src/radar/eval.py            score the rules against labelled postings
site/                        Next.js site that reads the snapshot
.github/workflows/radar.yml  the hourly run; publishes to the `data` branch
```

A run asks each board for its list (one request), keeps the postings located in the UAE, and fetches a
description only for postings it has not read before. The result is folded into `state.json`, which is what
lets the site say "first seen 2 hours ago" and mark a role closed when it leaves the employer's board.

Sources are limited to feeds the provider documents as public or whose crawler rules allow reading. LinkedIn,
Indeed, Bayt, GulfTalent and Naukrigulf are not read. SmartRecruiters is not read because its API host asks
automated readers to stay away, which leaves out talabat (Delivery Hero), Masdar and Namshi; the site says so.
Requests to any one host are at least a second apart (three for Workable, which blocks bursts for a day).

## How accurate the reading is

On 10 Nov 2026 all 650 UAE postings on the watched boards were checked for kind, and the 50 student roles the
rules had listed were read in full for facts.

| What is read | Applies to | First meeting: precision / recall | After fixes: precision / recall |
|---|---|---|---|
| Is it a student role | 64 | 100% / 89% | 100% / 98% |
| Which kind | 63 | 100% / 100% | 98% / 98% |
| Who can apply | 19 | 100% / 95% | 100% / 100% |
| Start | 16 | 88% / 88% | 100% / 100% |
| Length | 23 | 100% / 74% | 100% / 100% |
| Pay | 19 | 100% / 100% | 100% / 100% |
| Stage of study | 46 | 94% / 94% | 98% / 98% |
| Where you work | 21 | 100% / 100% | 100% / 100% |
| Closing date | 1 | 100% / 100% | 100% / 100% |

Read this table with three cautions:

- **"After fixes" is not an independent test.** The misses in the first column were fixed and the rules were
  scored again on the same postings. The first column is the better guide to new postings.
- **The labels were written by Claude**, the AI assistant that built this project, by reading each posting. No
  person has checked them. Two labels were corrected after the second scoring (listed in `labels.json`).
- **Facts were labelled only on roles the rules had already listed**, so a fact inside a role the rules missed
  is not counted. Seven student roles were missed at first meeting; one is still missed.

The posting texts are not in this repository (they belong to the employers), so `python -m radar.eval` needs
`python tools/pool.py` to be run first.

## Run it

Python 3.12 or later and Node 24.

```
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt pytest ruff      # Windows; use .venv/bin on macOS and Linux
set PYTHONPATH=src                                             # export PYTHONPATH=src elsewhere
python -m radar.run                                            # writes data/snapshot.json
cd site
npm install
npm run dev                                                    # http://127.0.0.1:3150
```

The site reads, in order: `SNAPSHOT_URL` (the published snapshot), `../data/snapshot.json` (a local run), then
the copy bundled in `site/public`.

## Checks

| Check | Command | Result on 11 Nov 2026 |
|---|---|---|
| Collector tests | `python -m pytest` | 247 passed |
| Collector lint | `ruff check src tests tools` | clean |
| Site unit tests | `npm test` (in `site/`) | 36 passed |
| Site lint and types | `npm run lint`, `npm run typecheck` | clean |
| Site build | `npm run build` | clean |
| Browser tests | `npm run e2e` | 31 passed, against the production build |
| Dependencies | `npm audit --omit=dev` | 0 known vulnerabilities |

Collector tests run against small recorded samples of each real feed (`tests/fixtures`), so they need no
network. Browser tests cover the list, filters, keyboard use, the CV match, feeds, security headers,
accessibility (axe, light and dark) and phone layout.

## Not done yet

- The hourly workflow and the `data` branch have not run on GitHub: the repository has not been published.
- Coverage is 80 employers. Many large UAE employers use Oracle or SAP career systems, which are not read yet.
- Remote roles open to UAE residents are not listed.
- The labelled set has not been checked by a person, and there is no unseen test set.

## License

MIT.
