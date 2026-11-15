---
version: 1
slug: "frontend-index-html"
primary_target: "frontend/index.html"
related_targets: []
---

# Farmer Joe, three screens (frontend/index.html)

Scope: the whole frontend, one file, three screens in order: intro, farm form, plan. Visitor mode: the intro is Persuade; the form and the plan are Operate.

Audience and job: a farmer who wants to know which weather contracts would steady this season's income. They press Start, describe the farm (location on a map, crop, acres, normal yield, expected price, worries, budget, stability versus cost), then read the advice, choose contracts and amounts, and review the order.

Content: the questions and worked example in `../input form.png`; three sample July markets at the station nearest the farm; live open markets read from the Kalshi demo API. Forecasts and July prices are sample data and are labelled so.

Constraints: static HTML/CSS/JS that opens from disk; the user's three-screen order; the pin drop on the map is animated; Farmer Joe is a name, not a speaking character; no real money and no API key in the browser.

Unresolved: order placement needs the team's server; how distance to the station reduces the hedge is a sample assumption.

## Direction contract

THESIS: Farmer Joe is a brand printed on a seed sack. The intro is the sack's front, the farmer fills in the tag, and the plan reads like the bag's analysis tag. It refuses the white onboarding wizard of progress bar and rounded cards.

OWN-WORLD: Green and white (the user's palette, 2026-11-14; a yellow version was tried and dropped). Sack green is the ground of every screen. White tag stock carries the intro panel, the tags, the map and the Start tag. Tag red is kept for the pin, the stamps, No and warnings. Whatever is active or chosen is shown by white on green or a pale green wash, never by a third colour. The Start tag carries a plain black arrow, no circle. Big Shoulders in heavy condensed capitals for the name, screen titles and key figures; Archivo for everything read or operated. Tags are white rectangles, and data sits in ruled rows with the label left and the value right. Wording is short: only what the farmer needs.

STORY: The farmer meets the name and one promise, presses Start, fills in the tag while the map answers (the pin drops, the nearest station links up), then reads the plan, ticks contracts, sets amounts inside the budget and reviews the order.

FIRST VIEWPORT: 1440 x 900 on a green field. A white panel fills the left 62 percent from top edge to bottom edge, carrying FARMER JOE in sack green in two stacked lines of capitals about 200px tall with one short promise under it. On the green at the right: three short lines on how it works, the Start tag (white, eyelet, large label, plain black arrow), and the fine print.

FORM: Seed sack print, position 5 of 7 on the grounded list; seed:4cda982d6f6b5972. Signature interaction: the red pin drops on the white map and the tag's first row is stamped with the place and its nearest station. Motion grammar: things land and press (a drop with a short settle, a stamp pressing in), screens change like pulling the next tag, each move under 300ms on one ease-out curve. Raises: the active step takes a wash and heavier rules across its whole row (bebop title card); spot inks only, green and red on white stock (risograph); every chart sits on one ruled grid (oscilloscope bench); one form at several sizes, the ruled tag row (Emigre specimen); steps are numbered because the order is real, and a finished answer stays visible but quiet (build-instruction book).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
