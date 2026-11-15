---
name: Farmer Joe
description: Financial advice to steady a farm's income, printed like a seed sack in green and red on white tag stock.
colors:
  green-700: "#17603a"
  green-800: "#114a2c"
  green-600: "#1f7446"
  green-500: "#3d8a5f"
  green-300: "#5a9c76"
  wash: "#e8f3eb"
  red: "#c6321d"
  red-deep: "#a32715"
  ink: "#0d3320"
  ink-2: "#3c5547"
  ink-3: "#5b7164"
  black: "#000000"
  tag: "#fbfcf9"
  tag-2: "#eef3ee"
  rule: "#d5ddd6"
  rule-strong: "#9fb0a5"
  white: "#ffffff"
  on-green-2: "#d3e6d8"
  on-green-3: "#b6d6c0"
  yes-tint: "#dcebdf"
  no-tint: "#f8dfd9"
  no-ink: "#8a2112"
typography:
  display:
    fontFamily: "Big Shoulders, Arial Narrow, sans-serif"
    fontSize: "clamp(72px, min(31cqi, 38vh), 360px)"
    fontWeight: 900
    lineHeight: 0.82
    letterSpacing: "-0.005em"
  headline:
    fontFamily: "Big Shoulders, Arial Narrow, sans-serif"
    fontSize: "clamp(40px, 4.4vw, 60px)"
    fontWeight: 900
    lineHeight: 1.06
  action:
    fontFamily: "Big Shoulders, Arial Narrow, sans-serif"
    fontSize: "clamp(64px, 6.4vw, 96px)"
    fontWeight: 900
    lineHeight: 0.9
  name:
    fontFamily: "Big Shoulders, Arial Narrow, sans-serif"
    fontSize: "30px"
    fontWeight: 800
    lineHeight: 1
  figure:
    fontFamily: "Big Shoulders, Arial Narrow, sans-serif"
    fontSize: "40px"
    fontWeight: 800
    lineHeight: 0.95
  stamp:
    fontFamily: "Big Shoulders, Arial Narrow, sans-serif"
    fontSize: "21px"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "0.02em"
  promise:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(20px, 2.1vw, 30px)"
    fontWeight: 600
    lineHeight: 1.3
  lede:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.4
  title:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: 1.45
  body:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "14.5px"
    fontWeight: 650
    lineHeight: 1.35
  note:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.45
rounded:
  stamp: "2px"
  tag: "3px"
  round: "50%"
spacing:
  pad: "28px"
  pad-narrow: "14px"
  sack: "48px"
  tag-inset: "22px"
  row-y: "10px"
  gap-sm: "8px"
  gap-md: "12px"
  gap-lg: "20px"
  gap-xl: "32px"
components:
  start-tag:
    backgroundColor: "{colors.tag}"
    textColor: "{colors.ink}"
    typography: "{typography.action}"
    padding: "18px 30px 18px 26px"
    height: "132px"
  start-tag-hover:
    backgroundColor: "{colors.wash}"
    textColor: "{colors.ink}"
  button-primary:
    backgroundColor: "{colors.green-700}"
    textColor: "{colors.white}"
    rounded: "{rounded.tag}"
    padding: "0 20px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.green-800}"
    textColor: "{colors.white}"
  button-primary-disabled:
    backgroundColor: "{colors.tag-2}"
    textColor: "{colors.ink-3}"
  button-quiet:
    backgroundColor: "{colors.tag}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    padding: "0 14px"
    height: "38px"
  button-quiet-hover:
    backgroundColor: "{colors.tag-2}"
    textColor: "{colors.ink}"
  button-quiet-pressed:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.tag}"
  step:
    backgroundColor: "{colors.green-700}"
    textColor: "{colors.on-green-2}"
    rounded: "{rounded.tag}"
    padding: "6px 12px 6px 8px"
  step-current:
    backgroundColor: "{colors.tag}"
    textColor: "{colors.ink}"
  tag:
    backgroundColor: "{colors.tag}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    padding: "16px 20px 18px"
  row:
    backgroundColor: "{colors.tag}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    padding: "10px 22px"
  row-active:
    backgroundColor: "{colors.wash}"
    textColor: "{colors.ink}"
  field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    padding: "4px 10px"
    height: "40px"
  segment-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
    rounded: "{rounded.stamp}"
    height: "32px"
  stamp:
    textColor: "{colors.red}"
    typography: "{typography.stamp}"
    rounded: "{rounded.stamp}"
    padding: "1px 9px 2px"
  ticket:
    backgroundColor: "{colors.tag}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    padding: "12px 16px 14px"
  ticket-pick:
    backgroundColor: "{colors.tag-2}"
    width: "52px"
  ticket-pick-on:
    backgroundColor: "{colors.green-800}"
    width: "52px"
  side-yes:
    backgroundColor: "{colors.yes-tint}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    width: "68px"
    height: "50px"
  side-yes-pressed:
    backgroundColor: "{colors.green-700}"
    textColor: "{colors.white}"
  side-no:
    backgroundColor: "{colors.no-tint}"
    textColor: "{colors.no-ink}"
    rounded: "{rounded.tag}"
    width: "68px"
    height: "50px"
  side-no-pressed:
    backgroundColor: "{colors.red}"
    textColor: "{colors.white}"
  verdict:
    backgroundColor: "{colors.tag-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    padding: "1px 8px 1px 6px"
  tooltip:
    backgroundColor: "{colors.tag}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    padding: "8px 11px 9px"
---

# Design System: Farmer Joe

## Overview

**Creative North Star: "The Seed Sack"**

Farmer Joe is a brand printed on a seed sack. The intro is the front of the sack: a white panel that runs edge to edge with the name in sack-green capitals as tall as the panel allows. The farm form is the sack's tag, filled in one ruled row at a time while a white map answers. The advice screen reads like the analysis tag sewn to a bag: a title that states the hedge, ruled figures, and hedges as tickets. Farmer Joe is the product's name only; nothing on screen speaks as a character.

Everything is flat print. There are two inks (sack green and tag red) and one stock (white tag card). Green is the ground of every screen, so the white panel, tags and map are objects sitting on it, never a page behind them. Density is that of a filled-in form: 15px reading text, 10px row padding, rules instead of boxes. Wording is as short as the form allows: labels of one to three words, one line per ticket, a title that is the number. The system refuses the white onboarding wizard of progress bar and rounded cards.

Motion is things landing and pressing. The pin drops onto the map (260ms) and a red ring spreads from the landing point (280ms), and a line runs out to the nearest station (280ms). Screens rise in 18px over 240ms. Every move shares one curve, `cubic-bezier(0.23, 1, 0.32, 1)`, and none runs longer than 280ms; state changes on controls take 120 to 200ms. Under reduced motion the pin fades in place, screens cross-fade in 160ms, and transitions are cut to nothing.

The finish review left four ideas open that are not in the build and are not part of this system yet: seam or lot devices on the sack front, eyelets and perforations on the plan's tags, a tag-pull screen change, and ruled rows under the map.

**Key Characteristics:**
- Sack green is the ground of all three screens; white is the intro panel, the tags, the map and type on green.
- Active or chosen is shown without a third colour: a white pill for the current step, a pale green wash with 2px green rules for the row being answered, a deep green stub for a ticket that is in the plan.
- Heavy condensed capitals for the name, screen titles and key figures; a plain grotesque for everything read or operated.
- Data sits in ruled rows, label left and value right, opened by a 2px ink rule and separated by 1px hairlines.
- One chart form: one plot of revenue by harvest, a light green line for the farm without the hedge and a heavier ink line over it for the farm with the plan.
- Sample and demo data is stamped in red, tilted 2 degrees.
- Short copy everywhere: one to three words per label, one line per ticket.

## Colors

Two spot inks, green and red, on white tag stock, with the neutrals all drawn from the green.

### Primary
- **Sack Green** (`green-700`, #17603a): the ground of every screen, the name on the intro panel, the borders between states on the map, the primary button, the filled part of sliders and the budget meter, the pressed Yes side, the rules that mark the row being answered, and the check in a chosen ticket's box. Its neighbours do small jobs: `green-800` is the primary button's hover, the stub of a ticket that is in the plan, and the sticky result strip; `green-600` is the hover behind a step in the bar; `green-500` is the scrollbar thumb; `green-300` is the chart's line for the farm without the hedge, with its dots, its worst-harvest rule and its key.
- **Wash** (`wash`, #e8f3eb): a pale green laid on tag stock to say "here, now". The form row that holds focus, the Start tag under the pointer, a state on the map under the pointer. It is always a response to the farmer, never a resting fill.

### Secondary
- **Tag Red** (`red`, #c6321d): the map pin and its landing ring, the stamps, invalid field borders, the over-budget meter and alert, the pressed No side, and the highlight behind selected text (with white type). `red-deep` is error text on tag stock. `no-ink` on `no-tint` is the unpressed No side and a No price.

### Neutral
- **Ink** (`ink`, #0d3320): the darkest green, used as black. All text on tag stock, 2px opening rules, selected segments, the plan's line and dots in the chart, station dots, city names on the map and the station line. `ink-2` is secondary text on a tag and the chart's axis title, `ink-3` is units, axis ticks, placeholders, the contract count at a ticket's top right, and the name of a ticket that is not in the plan.
- **Black** (`black`, #000000): the arrow on the Start tag and nothing else. It is the one place true black is printed.
- **Tag Stock** (`tag`, #fbfcf9): the intro panel, every tag and ticket, the Start tag, the states on the map, the current step's pill, the halo behind city names on the map and worst-harvest labels in the chart, the ring around every chart dot, and the under-stroke that lifts the plan's line off the line beneath it. `tag-2` is the quiet resting fill: an unpicked ticket's stub, verdict chips, table heads, loading bars, the disabled primary button, and the hover of a quiet button or segment.
- **White** (`white`, #ffffff): type on green, the fill of fields (so an input reads one step brighter than the tag it sits on), and the box in a chosen ticket's stub.
- **Rules** (`rule`, `rule-strong`): `rule` is the 1px hairline between rows, the chart grid and the eyelet ring; `rule-strong` is the 1.5px border of fields and quiet buttons, and the unfilled slider track.
- **On-green greys** (`on-green-2`, `on-green-3`): secondary text on green (hints, fine print, idle steps) and the step that cannot be reached yet.
- **Yes tint** (`yes-tint`): the unpressed Yes side and a Yes price.

### Named Rules
**The Green Ground Rule.** Every screen's background is sack green. White never becomes the page; it is always a panel, a tag, a ticket, the map or a field sitting on the green.

**The No Third Colour Rule.** Whatever is active or chosen is shown with green and white alone. On green, the current thing turns white (the current step is a tag-stock pill). On tag stock, the row being answered takes the wash plus 2px sack-green rules top and bottom, so the state never rests on a faint tint alone. A ticket that is in the plan gets a `green-800` stub with a white box and a green check. No yellow, no blue, no accent brought in to mean "selected".

**The Red Is Pressed On Rule.** Red is for the pin, the stamps, warnings, No, and the text-selection highlight. It never decorates and never becomes a ground, a panel or a tag.

**The Yes And No Rule.** Yes prints in green and No prints in red, tinted at rest and solid when pressed. The word is always printed beside the colour, so the pair never depends on hue alone.

## Typography

**Display Font:** Big Shoulders (with Arial Narrow, sans-serif)
**Body Font:** Archivo (with system-ui, -apple-system, Segoe UI, sans-serif)

**Character:** Stencil-weight condensed capitals from sack printing against a plain, slightly wide grotesque for the working text. Both are variable fonts embedded in `frontend/fonts/fonts.css` as data URIs so they survive opening the page from disk.

### Hierarchy
- **Display** (900, `clamp(72px, min(31cqi, 38vh), 360px)`, line-height 0.82, uppercase): the name on the intro panel, two stacked lines in sack green sized to the panel's width.
- **Headline** (900, `clamp(40px, 4.4vw, 60px)`, line-height 1.06, uppercase, balanced): one screen title per screen, in white on the green. On the advice screen the title is the hedge ("Hedge $14,945").
- **Action** (900, `clamp(64px, 6.4vw, 96px)`, line-height 0.9, uppercase): the word on the Start tag only.
- **Name** (800 to 900, 30px, line-height 0.95 to 1, uppercase): the wordmark in the bar, the Hedges heading, and each ticket's market name.
- **Figure** (800, 34 to 40px, line-height 0.95 to 1): the crop value at the foot of the farm tag and the order total. List numerals on the intro use the same face at 1.9em in white.
- **Stamp** (800, 21px or 15px small, letter-spacing 0.02em, uppercase): red stamps.
- **Promise** (Archivo 600, `clamp(20px, 2.1vw, 30px)`, line-height 1.3, max 24ch): the single sentence under the name ("Your Personal Agroeconomist").
- **Lede** (Archivo 400, 18px, line-height 1.4, max 62ch): the one line under the advice title that says where the money goes ("Suggested: $8,960 in Temp · $5,985 in Rain", or "Your mix: ..." after an edit). The effect line under it is 16px at 650 in white ("18% steadier. Bad harvest +$10,300. Average +$2,000.").
- **Title** (Archivo 700, 16px): the heading of a tag ("Revenue by harvest", "Order").
- **Body** (Archivo 400, 15px, line-height 1.45): default reading text. Field values are 15.5px at 600.
- **Label** (Archivo 650, 14 to 14.5px, line-height 1.35): form labels of one to three words ("Farm", "Acres", "Budget for hedging"), button text, table values.
- **Note** (Archivo 400, 12.5 to 13.5px): hints, units, fine print, axis ticks, the chart key, the station line under the town; capped at 60 to 80ch. City names on the map are 11.5px at 600.

### Named Rules
**The Two Voices Rule.** Big Shoulders is for the name, screen titles, market names, key figures and stamps, always at 800 or 900 and never below 15px. Anything the farmer reads as a sentence or operates as a control is Archivo.

**The Tabular Figures Rule.** Every number that can change or be compared (prices, amounts, table cells, axis ticks, field values) uses tabular numerals.

## Layout

Each screen is a full-height field of green with a two-column split that hands the wider side to the picture and the narrower side to the paper.

- **Intro:** a 62/38 grid. The white panel runs from the top edge to the bottom edge with 48px padding, the name at the top and the promise at the bottom, nothing between them. The green side stacks the three numbered steps at the top and the Start tag with one line of fine print at the bottom.
- **Bar (screens 2 and 3):** wordmark, three numbered steps (Start, Farm, Advice), and the sample-data note pushed to the right; 14px top padding, 28px page padding (`pad`).
- **Farm:** map column at 1.32fr beside the tag at 1fr (minimum 400px), 32px gap. The map column is sticky on wide screens.
- **Advice:** main column at 1.25fr (title, lede, effect line, chart tag, live-markets tag) beside the hedges column at 1fr, minimum 400px (tickets, order tag), 28px column gap and 20px row gap.
- **Inside a tag:** rows bleed to the tag's edges with negative margins so the hairlines and the wash run the full width; the content inset is 22px on the farm tag and 20px on the advice screen's tags. A form row is a two-column grid, label at 0.78fr and control at 1.22fr.

Responsive steps are fixed breakpoints, not fluid padding: at 1100px the advice screen stacks to one column and a sticky strip in `green-800` carries the effect line above the tickets; at 900px the farm stacks and the map is capped at 42dvh; at 820px the intro stacks and the Start tag moves directly under the panel; at 560px page padding drops to 14px (`pad-narrow`), form rows stack label over control, the ticket stub narrows to 44px, and the Yes and No sides split the ticket's width.

## Elevation & Depth

Flat. Depth comes from stock on ground: white tags on green, a white panel beside green, a white field on a tag. Nothing at rest casts a shadow, and there are no gradients, blurs or overlays.

### Shadow Vocabulary
- **Tooltip lift** (`box-shadow: 0 8px 18px rgba(9, 36, 22, 0.28)`): the chart tooltip only, the one element that floats over other content.
- **Thumb lift** (`box-shadow: 0 1px 4px rgba(13, 51, 32, 0.45)`): the slider thumb, so it reads as the grabbable part of the track.
- **Eyelet ring** (`box-shadow: 0 0 0 4px` in `rule`): a hard ring, not a shadow; the reinforcement around a tag's punched hole.

### Named Rules
**The Printed Flat Rule.** Surfaces are separated by ink and stock, never by shadow. A shadow is allowed only on something that floats above the print (the tooltip) or is physically grabbed (the slider thumb).

## Shapes

Rectangles with barely eased corners (3px on tags, tickets, fields, buttons and steps; 2px on stamps, the meter and the inside of the segmented control). Circles are reserved for things that are round in the world: eyelets, step numerals, station dots, chart dots, slider thumbs, the live dot.

Two tags have cut corners made with a clip path: the Start tag is clipped at both left corners (26px) so it points like a luggage tag, and the farm tag has both top corners cut (18px) with an eyelet centred 12px below the top edge. The eyelet is a 14px green hole with a 4px ring (20px with a 5px ring on the Start tag). The advice screen's tags are plain rectangles without eyelets.

Borders carry meaning by weight: 2px ink opens a group of rows or closes it into a total, 2px sack green brackets the row being answered, 1px `rule` separates rows, 1.5px `rule-strong` outlines a control, 2px red outlines a stamp. Stamps are tilted 2 degrees anticlockwise.

Icons are 18px line drawings (1.75px stroke, round caps and joins, no fill) from one inline sprite: arrow, info, check, alert, equal, retry. The Start arrow is the same drawing at 52px with a 2.25px stroke, with no disc behind it.

## Components

### Buttons
Plain and pressable; they shrink slightly when pressed (scale 0.97).
- **Shape:** 3px corners, 1.5px border, 14px Archivo at 650, 38px tall with 14px side padding.
- **Primary:** solid sack green with white text, 48px tall, 16px text, 20px side padding ("See my plan", "Send to Kalshi demo"). Hover darkens to `green-800`. Disabled is `tag-2` with `ink-3` text and a `rule` border.
- **Quiet:** `rule-strong` outline on tag stock with ink text ("Table", "Add", "Retry"). Hover fills `tag-2`; a pressed toggle fills ink with tag-stock text.
- **Text link:** inherits colour, 650 weight, underlined with a 3px offset; the underline thickens to 2px on hover.
- **Focus:** a 2px outline offset 2px, white on green and ink on tag stock (the intro panel, tags and tickets alike). On a chosen ticket's deep green stub the ring around the box turns white.

### Start tag
A white tag on the green side of the intro. A tag-stock face at least 132px tall (104px once the intro stacks), cut at both left corners, holding an eyelet, the word START in the Action size, and a plain 52px black arrow with no disc behind it. Hover lays the wash over the face (160ms); on a real pointer the arrow also slides 8px right (180ms). Press scales the tag to 0.98. Focus is a 3px white outline offset 4px, drawn on the link so the clipped face does not cut it.

### Steps
Three numbered links in the bar: Start, Farm, Advice. Each has a 22px outlined circle with its number and a 14px label at 600 in `on-green-2`. Hover fills `green-600` and turns the text white. The current step is a tag-stock pill with ink text. A step that cannot be reached yet is `on-green-3` and inert.

### Tags
- **Corner Style:** 3px, or cut corners on the farm tag.
- **Background:** tag stock, ink text.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** none; the edge is the change from green to white.
- **Internal Padding:** 16px 20px 18px on the advice screen's tags; 40px 22px 22px on the farm tag to clear the eyelet.
- **Head:** a 16px/700 title on the left, with a stamp or a quiet button on the right.

### Ruled rows
The system's one data form, used at every size: form rows, the analysis table, order lines, live-market rows. Label left, value right, 1px hairline between rows, a 2px ink rule above the first row and above a total. In the form, the row that holds focus takes the wash edge to edge with a 2px sack-green rule inside its top and bottom edges (150ms). Notes and errors sit under the control in the value column.

### Inputs / Fields
- **Style:** white fill, 1.5px `rule-strong` border, 3px corners, 40px tall. The unit sits inside the field: a leading "$" in ink at 600, a trailing unit ("acres", "bu/acre", "/bu") in `ink-3`.
- **Focus:** the border turns ink and a 2px ink outline appears 1px out; the row behind it takes the wash and its green rules.
- **Error:** the border turns red and a `red-deep` message at 13.5px/600 with an alert icon appears under the control.
- **Slider:** a 6px track, sack green up to the value and `rule-strong` after it, with a 20px ink thumb ringed in white. Number fields that have a range are paired with a slider on the same row.

### Segmented control
- **Segmented (one of three):** a white box with a 1.5px ink border and 3px padding; the chosen segment is solid ink with white text, others fill `tag-2` on hover. Focus on the chosen segment is a white ring drawn inside it.

### Stamps
Red Big Shoulders capitals in a 2px red outline with 2px corners, tilted 2 degrees, with no fill on a tag and a tag-stock fill on green. Used for "Sample" and "Demo only" marks beside headings (15px, 1.5px outline). The farm tag carries no stamp: the user found red text under the town distracting.

### Map
The lower 48 states in tag stock with 1px sack-green borders on the green ground, crosshair cursor; a state takes the wash under a real pointer. Every city with a Kalshi weather station is an ink dot with its name beside it (11.5px/600 ink, haloed in tag stock); names are placed so they never sit on each other, a dot or the pin, and a name with no free spot is left off (the full list sits in a disclosure under the map key, its summary in white at 650). Below 420px wide only the nearest city is named. The nearest city gets a white ring, a 2px ink line from the pin, and a heavier 13.5px/800 name that is always shown. The pin is red with a white outline and a white eye; its landing ring is a 2px red circle that spreads and fades over 280ms.

### Hedge tickets
A tag-stock ticket with a 52px stub down its left edge holding a 24px checkbox. Each ticket is one hedge the model can put money into.
- **In the plan:** the stub is `green-800`, the box is white with a sack-green check, and the market name prints in ink. The body carries the market name in the Name size with the contract count at 13.5px in `ink-3` on the right ("22,400 contracts"), one short line saying what the market is in `ink-2`, then the Yes and No sides (68 by 50px each: the word at 12px over the price at 18px) beside a dollar field (38px tall, a leading "$") and its slider, then the model's chance in `ink-2` ("Model 45%") followed by a verdict chip. The amount is set in dollars; the contract count follows it.
- **Not in the plan:** the stub is `tag-2` with an empty ink-outlined box, the name drops to `ink-3`, the top right reads "Not in plan", and the body shows the two prices as tinted chips beside a quiet Add button.
- **Verdict chip:** `tag-2`, 13px/650, a 14px icon and two or three words ("Cheap by 5", "Pricey by 6", "Fair price").
- **Flag:** a caveat or warning is one 13.5px ink line led by a 16px info or alert icon ("May not exist on Kalshi.").

### Revenue by harvest chart
One plot on a ruled grid: harvests 1 to 20 along the bottom over the axis title "Harvest" (12.5px/600 in `ink-2`), dollars up the left. Two lines cross it. The farm without the hedge is a 2px line in `green-300`; the farm with the plan is a 2.5px ink line drawn on top, lifted off the other by a 6px tag-stock under-stroke. Every harvest is an 8px dot in its line's colour with a 2px tag-stock ring. When no hedge is ticked there is no ink line. The line without the hedge sets the dollar range and holds still while the plan's line moves. Horizontal grid lines are 1px `rule`, the bottom line is a 1px ink baseline, and axis ticks are 12px `ink-3`; harvest numbers thin to every second where they would crowd.

A 1px rule in each line's colour marks that line's worst harvest, so the gap between the two bad years reads straight off the plot. On plots 520px or wider the rules run into a right-hand margin and are labelled there at 12px/650 in ink, haloed in tag stock ("Worst $216.9K"). On narrower plots the rules stay and the table under the plot carries the figures.

A key above the plot in HTML names the lines with two 16 by 3px swatches and 13px `ink-2` text: "Without Farmer Joe" and "With Farmer Joe". The second entry hides when nothing is ticked.

Hover shows a 1px `ink-2` crosshair, grows that harvest's dots to 11px (120ms), and opens a tooltip on tag stock (1.5px ink border, a 12 by 3px line key beside each figure); arrow keys move it when the plot has focus. A quiet toggle swaps the plot for a scrolling table of the same harvests. Under the plot, the analysis is ruled rows in three figure columns (Without, With plan, Change).

### Order
A tag with a 10px budget meter (sack green fill on `rule`, turning red when over the limit), a budget line, order lines as ruled rows, a total closed by a 2px ink rule with the amount in the Figure size, and a full-width primary button.

## Do's and Don'ts

### Do:
- **Do** put every screen on sack green (`green-700`) and keep white for the panel, tags, tickets, the map, fields and type on green.
- **Do** show the current or chosen thing with green and white alone: a white pill on green, the wash plus 2px green rules on tag stock, a `green-800` stub with a white box on a ticket.
- **Do** keep the wash (`wash`) for responses to the farmer (the focused row, a hover) and `tag-2` for quiet resting fills.
- **Do** set data as ruled rows, label left and value right, with a 2px ink rule opening the group and 1px `rule` hairlines between rows.
- **Do** use Big Shoulders at 800 or 900 in capitals for the name, screen titles, market names, key figures and stamps, and Archivo for everything else.
- **Do** print Yes in green and No in red with the word beside the colour, tinted at rest and solid when pressed.
- **Do** stamp sample and demo data in red beside its heading, and keep the stamp's 2 degree tilt.
- **Do** draw the comparison as one plot of two lines: `green-300` at 2px for the farm without the hedge and ink at 2.5px with a 6px tag-stock under-stroke for the farm with the plan, a ringed dot on every harvest, each line named in the key above the plot.
- **Do** keep copy short: one to three words for a label, one line for a ticket, the number itself for a title.
- **Do** keep moves on `cubic-bezier(0.23, 1, 0.32, 1)` at 120 to 280ms, and give each one a fade-only fallback under reduced motion.
- **Do** use tabular numerals for every price, amount and table figure.

### Don't:
- **Don't** make white the page background or lay tags out as a white wizard with a progress bar and rounded cards.
- **Don't** bring in a third colour to mean active, chosen or new. Yellow was tried and dropped; the palette is green and white with red.
- **Don't** use red for decoration or as a ground, a panel or a tag; it is the pin, the stamps, warnings, No and selected text.
- **Don't** print true black anywhere but the Start arrow. Text and rules on tag stock are `ink`.
- **Don't** put the Start arrow back in a disc; it is a bare black arrow on the tag.
- **Don't** split the comparison across stacked charts or bring in a third line colour; the two lines share one plot in `green-300` and ink.
- **Don't** add shadows to tags, tickets or buttons; only the chart tooltip and the slider thumb have one.
- **Don't** round corners past 3px; circles are for eyelets, step numerals, dots and thumbs.
- **Don't** write as Farmer Joe. It is the product's name, not a speaking character.
- **Don't** show a sample or assumed number without its label.
