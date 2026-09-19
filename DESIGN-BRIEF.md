# Hampy — design brief

Paste this whole file into a design tool. It describes what exists today, what
it is for, and where it falls short. Everything below is drawn from the running
code, not from intent documents.

---

## 1. What this is

**Hampy** is a phone-first tool for **food-bank volunteers**. A warehouse robot
fetches grocery items from shelves; this app is how a volunteer keeps the shelf
inventory current and tells the robot what to bring.

Two jobs, in priority order:

1. **Keep inventory accurate** — browse shelves, add and remove items. This is
   the primary, everyday work.
2. **Ask the robot for an item** — describe a need in plain language ("something
   vegetarian", "a gluten-free dinner option"); an LLM picks one real item from
   the live shelves and dispatches the robot to fetch it.

The tone should read as *capable and dependable*, closer to a work tool than a
consumer shopping app. Volunteers may be older, in a hurry, standing in a
warehouse, possibly wearing gloves.

---

## 2. What exists today

### Screen A — Shelves (home, `/`)

Vertically scrolling, pull-to-refresh. In order:

- **Header** — kicker `HAMPY · INVENTORY`, title *"Good morning, volunteer."*,
  subtitle *"Keep shelves current so the robot can help quickly."*, and a round
  apple icon badge on the right.
- **"Ask Hampy" entry card** — a full-width tappable row with a robot icon in a
  green circle, title, one-line description, and a right arrow. Navigates to
  Screen B.
- **Section heading** "Shelves", then a **search field** filtering by item name.
- **Shelf cards** — one per shelf: eyebrow `SHELF {n}`, a count ("3 items"), a
  chevron, and the item names. Duplicate items are grouped with a count.
- Tapping a card opens the **shelf bottom sheet**: the item list with a remove
  control per item, plus an add-item field.

### Screen B — Ask (`/ask`)

- Back link to Shelves, kicker `ASK HAMPY`, title *"What should the robot
  bring?"*
- **Request card** — a multiline textarea (700 char max) with a helper line and
  a round **microphone button**. Recording turns it red with a stop icon. Speech
  is transcribed server-side and dropped into the same textarea, so voice is an
  input method for the text field, not a separate path.
- **Primary button** "Ask Hampy".
- **Result card** — green check, kicker `ROBOT TARGET READY`, *"Success! The
  robot will now retrieve the object."*, then `Shelf {n} · {item}`, then a
  **robot camera panel**.

### Shared states already handled

Loading skeletons, empty inventory, no-search-match, request error, and an
in-flight "Choosing the best item…" card. Errors use a soft red panel with an
alert icon. These are announced with `accessibilityLiveRegion`.

---

## 3. Data and API

Base URL is discovered from the Expo dev host. All routes are under `/api`.

| Method | Path | Body / returns |
| --- | --- | --- |
| GET | `/api/shelves` | `{ shelves: [{ shelf_number, items[] }] }` |
| GET | `/api/shelves/{n}` | one shelf |
| POST | `/api/shelves/{n}/items` | `{ item }` → updated shelf (201) |
| DELETE | `/api/shelves/{n}/items/{item}` | updated shelf |
| POST | `/api/recommendations/app` | `{ user_input }` → `{ shelf_number, item, source }`, also dispatches the robot |
| POST | `/api/recommendations/robot` | same, but does **not** dispatch |
| POST | `/api/transcriptions` | multipart `audio` → `{ text }` |
| GET | `/health` | `{ status }` |

**Quantity is implicit.** A shelf is a flat list of strings, so two bananas are
the literal list `["banana", "banana"]`. The UI groups and counts them at render
time. There is no quantity field, no categories, no expiry, no item IDs.

Live data is tiny: shelf 1 = mushroom, peas, banana; shelf 2 = pasta, rice.
**Design for 2–20 shelves and up to ~50 items per shelf**, not for two.

The LLM is instructed to respect dietary needs and to only ever return an item
that is actually on a shelf.

---

## 4. Current visual language (keep unless there's a reason)

| Role | Value |
| --- | --- |
| background | `#F7F9F5` |
| surface | `#FFFFFF` |
| surface-muted | `#EAF1E8` |
| action | `#1D5C3B` (deep green) |
| action-pressed | `#16462D` |
| ink | `#16231A` |
| muted | `#5B6A5D` |
| line | `#D5E0D4` |
| danger | `#A43D2E` |
| danger-soft | `#F9E9E6` |

Radius: card 16, field 12, pill 999. Spacing: page 20, gap 12, section 24,
min touch target 48. Type: title 30/36 extrabold, section 21, card 17, body
16/23, label 13-14. Platform sans (SF Pro / Roboto). Content is capped at 680 px
wide and centred so it stays readable on tablet and web.

Existing guardrails: green with white text only; no gradients; no purple/blue
"AI" styling; no second bright accent; no decorative food photography; no dense
tables; no unlabeled icon buttons; motion limited to 160–220 ms opacity and
transform, disabled under reduced-motion.

---

## 5. Problems worth solving

These are real gaps in the build, roughly in order of impact.

1. **No dark mode.** The palette is a flat light-only JSON with no dark variant
   anywhere in the app. A warehouse at 6am is a bad place for a white screen.
2. **The dispatch is a dead end.** After "the robot will now retrieve the
   object" nothing further happens — no progress, no arrival, no failure, no way
   to cancel. The single most valuable thing to design is *what the volunteer
   sees for the next 60 seconds.*
3. **The robot camera is a placeholder.** It renders "Camera will go here"
   unless an env var supplies a stream URL. A live MJPEG feed does exist on the
   robot, so design the real panel: connecting, live, stalled, and unavailable.
4. **Inventory editing is buried.** Add and remove live inside a bottom sheet,
   two taps from anywhere, with no bulk entry — yet this is the primary daily
   job. Restocking a shelf means repeating add-one-item many times.
5. **Search only filters whole shelves.** Searching "rice" shows the entire
   shelf containing rice rather than pointing at the item, which gets worse as
   shelves grow.
6. **The greeting is fixed.** "Good morning, volunteer." shows at any hour.
7. **No quantity affordance.** Because repetition encodes count, adding five
   bananas is five separate actions and correcting an over-count is fiddly.
8. **Voice is hidden.** The microphone lives in the corner of the Ask textarea,
   though speaking is plainly the better input for someone holding a crate.
9. **Only two screens and no persistent navigation.** There is no history of
   past requests, no robot status surface, and no settings.

---

## 6. Constraints the design must respect

- **React Native via Expo** (SDK 57), routed by expo-router. It must run on iOS
  and Android phones; the same code also renders on web, hence the 680 px cap.
- **Styling is currently duplicated** — most components carry *both* NativeWind
  utility classes and a `StyleSheet.create` block expressing the same rules, and
  the two have already drifted apart. Pick one system and say which.
- **Icons** are `@expo/vector-icons` (MaterialCommunityIcons). Assume that set.
- **Accessibility is already decent and must not regress**: every control has a
  role and label, async results announce via live regions, targets are 48 px.
  Assume screen-reader use and keep contrast at WCAG AA or better.
- **No authentication, no accounts, no per-user state.** Anyone holding the
  phone is a volunteer. Do not design a login.
- Fonts must be system defaults; custom font loading is not set up.

---

## 7. What to produce

A redesign of both screens plus the shelf-editing surface, covering:

- The **default, loading, empty, error and success** state of every surface.
- A designed answer to problem 2 — **robot progress after dispatch** — including
  what happens when the robot fails or the item turns out not to be there.
- A **dark theme** for the full token set.
- **Phone first**, with a note on how each layout should behave at tablet width.

Keep the deep-green, calm, utilitarian character. This is equipment for people
doing unglamorous work quickly, not a lifestyle app.
