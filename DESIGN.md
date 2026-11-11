# DESIGN.md: Intern Radar

Status: direction chosen by Claude on 10 Nov 2026 under Uzair's brief ("make the front-end exceptionally good");
not yet reviewed by him. Pages: `/`, `/role/[slug]`, `/employers`, `/market`, `/method`, the 404, the icon and
the share image.

## What it is

A board of student roles at UAE employers, read from the employers' own career systems every hour. The thing a
visitor came for is the list. Everything else on the page exists to make the list faster to read or easier to
trust.

## Who opens it, and what they do in the first 20 seconds

A student in the UAE with ten minutes between classes, usually on a phone, often coming back for the second or
tenth time. They want three answers at once: what is new since I last looked, can I apply to it (many roles are
for UAE nationals only), and when does it start. A recruiter or engineer following a link from Uzair's CV wants
to see that it is live and that it shows its working.

So the first screen is the list itself, newest first, with the age of each role in a fixed column and the facts
on the row. No hero, no explainer above the fold.

## Source material

1. **The posting's own sentence.** Every fact on the site was read from one sentence, and the site holds that
   sentence with the deciding words marked. This is the product's one unusual object.
2. **A notice board with dates.** Roles arrive and leave; each has a first-seen time.
3. **The employer's filing.** Kind, place, department: plain labels, not decoration.
4. **The run log.** Which boards were read, when, and which failed.

## The idea

**The posting, read for you, with the receipt.** Each role is a line of plain facts; open it and each fact sits
beside the sentence it came from, with the deciding words underlined. The page looks like a well-set timetable:
a time column, strong titles, quiet facts. The only colour is the signal that something is new.

Directions considered and dropped: a literal radar (sweep, rings, green on black: a costume, and green tint is
ruled out); a card grid of roles (hides the time order, wastes the phone's width); a dashboard of counts first
(the count is not what a student came for).

## Type

Three self-hosted variable families, none of them a framework default:

- **Bricolage Grotesque** for role titles and page headings. It has width and optical-size axes, so a title can
  be tight and heavy at 22 px and a page heading wide at 44 px from one file. Its slightly irregular shapes keep
  a list of forty titles from looking like a table.
- **Hanken Grotesk** for everything read at length: facts, sentences, body copy.
- **Spline Sans Mono** for time, counts and system names: the timetable column.

Scale (px): 12 mono labels, 14 facts, 16 body, 19 row title on phone, 22 row title on desktop, 32 and 44
headings. Line height 1.5 for prose, 1.2 for titles. Numbers are tabular everywhere.

## Colour

Neutral greys in both themes; no tint. One hue, used only to mean "new or live".

| Role | Light | Dark | Used for |
|---|---|---|---|
| page | `#fafafa` | `#111111` | page ground |
| surface | `#ffffff` | `#191919` | the open row, inputs |
| wash | `#f0f0f0` | `#222222` | hover, pressed, evidence block |
| rule | `#e2e2e2` | `#2c2c2c` | row lines |
| rule-2 | `#c9c9c9` | `#444444` | input borders, strong lines |
| ink | `#141414` | `#ededed` | titles, facts |
| ink-2 | `#474747` | `#bdbdbd` | secondary text |
| ink-3 | `#6b6b6b` | `#929292` | labels, time |
| signal | `#c2410c` | `#ff8a4c` | new, live dot, the mark under deciding words |

Restriction ("UAE nationals only") is not a colour: it is ink text in a ruled box with a lock glyph, so it reads
in greyscale and for colour-blind readers. Closed roles are ink-3 with a line through the title. Contrast for
every text pair is computed and tested in `site/src/lib/tokens.test.ts` (4.5:1 for text, 3:1 for the dot and
borders that carry meaning).

## Layout

- One column of content, 1120 px at most, 20 px side gutters on a phone.
- A row is a grid: `time | body | action`. Time is a fixed 76 px mono column on desktop and sits above the title
  on a phone. Rows are separated by a single rule; there are no cards, shadows or rounded containers.
- Roles are grouped by when they were posted: Today, Yesterday, This week, Earlier this month, Older. Group
  headings stick while scrolling.
- Filters are one line of text controls above the list (kind, field, place, eligibility, age) and a search box.
  On a phone they collapse behind one "Filter" control that shows how many are active.
- Radius: 4 px on inputs and buttons only. No pill chips.

## Motion

Only where it carries information: a row that arrived in a refresh slides in and holds a signal edge for a few
seconds; the open row expands in 160 ms; the live dot pulses once when a check lands. `prefers-reduced-motion`
turns all of it off.

## Behaviour that counts as design

- "New since your last visit" is remembered in the browser and marked on the row.
- The list refreshes itself when a newer snapshot exists and says how many roles arrived.
- Keyboard: `/` focuses search, `j` and `k` move between rows, `Enter` opens, `Esc` closes.
- Filter state lives in the address, so a filtered list can be shared.
- Every fact that the posting does not state says "not stated", never a guess.

## Voice

Plain and exact. "Posted 2 hours ago", "UAE nationals only", "not stated". No exclamation marks, no "discover",
no "opportunities await". Errors say what happened and what still works.
