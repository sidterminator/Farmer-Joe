---
name: Farmer Joe
description: Weather protection for a farm's season, printed like a seed sack in three inks on white tag stock.
colors:
  green-700: "#17603a"
  green-800: "#114a2c"
  green-600: "#1f7446"
  green-500: "#3d8a5f"
  green-300: "#5a9c76"
  yellow: "#f6cf2e"
  yellow-light: "#ffe066"
  red: "#c6321d"
  red-deep: "#a32715"
  ink: "#0d3320"
  ink-2: "#3c5547"
  ink-3: "#5b7164"
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
    backgroundColor: "{colors.yellow}"
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
    backgroundColor: "{colors.yellow}"
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
    backgroundColor: "{colors.yellow}"
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
  chip:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tag}"
    padding: "0 12px 0 9px"
    height: "36px"
  chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
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
    backgroundColor: "{colors.yellow}"
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

Farmer Joe is a brand printed on a seed sack. The intro is the front of the sack: a corn-yellow panel that runs edge to edge with the name in capitals as tall as the panel allows. The farm form is the sack's tag, filled in one ruled row at a time while a yellow map answers. The plan reads like the analysis tag sewn to a bag: a title that states the result, ruled figures, and contracts as tickets. Farmer Joe is the product's name only; nothing on screen speaks as a character.

Everything is flat print. There are three inks (sack green, corn yellow, tag red) and one stock (white tag card). Green is the ground of every screen, so the white tags are objects sitting on it, never a page behind them. Density is that of a filled-in form: 15px reading text, 10px row padding, rules instead of boxes. The system refuses the white onboarding wizard of progress bar and rounded cards.

Motion is things landing and pressing. The pin drops onto the map (260ms) and a red ring spreads from the landing point, a line runs out to the nearest station (280ms), and the place name is stamped onto the tag's first row (180ms, scaling down from 1.16 at its 2 degree tilt). Screens rise in 18px over 240ms. Every move shares one curve, `cubic-bezier(0.23, 1, 0.32, 1)`; state changes on controls take 120 to 200ms. The one longer piece is the landing ring, which fades over 460ms. Under reduced motion the pin and stamp fade in place, screens cross-fade in 160ms, and transitions are cut to nothing.

The finish review left four ideas open that are not in the build and are not part of this system yet: seam or lot devices on the sack front, eyelets and perforations on the plan's tags, a tag-pull screen change, and ruled rows under the map.

**Key Characteristics:**
- Sack green is the ground of all three screens; white appears only as tag stock and as type on green.
- Corn yellow marks one thing per region: the panel, the current step, the row being answered, the contract that is in the plan.
- Heavy condensed capitals for the name, screen titles and key figures; a plain grotesque for everything read or operated.
- Data sits in ruled rows, label left and value right, opened by a 2px ink rule and separated by 1px hairlines.
- One chart form: two distributions stacked on a shared ruled grid, in two greens.
- Sample and demo data is stamped in red, tilted 2 degrees.

## Colors

Three spot inks on white tag stock, with the neutrals all drawn from the green.

### Primary
- **Sack Green** (`green-700`, #17603a): the ground of every screen, the primary button, the filled part of sliders and the budget meter, the pressed Yes side, and the "with your plan" columns in the chart. Its neighbours do small jobs: `green-800` is the primary button's hover and the sticky result strip, `green-600` is the hover behind a step in the bar, `green-500` is the scrollbar thumb, and `green-300` is the "without protection" columns in the chart.

### Secondary
- **Corn Yellow** (`yellow`, #f6cf2e): panels and whatever is active or chosen. The intro panel, the map's states, the current step, the form row that holds focus, the pick strip of a ticket that is in the plan, the numerals of the how-it-works list, text selection, and the Start tag's hover. `yellow-light` is only the hover of a state on the map.

### Tertiary
- **Tag Red** (`red`, #c6321d): the map pin and its landing ring, the stamps, invalid field borders, the over-budget meter and alert, and the pressed No side. `red-deep` is error text on tag stock. `no-ink` on `no-tint` is the unpressed No side and a No price.

### Neutral
- **Ink** (`ink`, #0d3320): the darkest green, used as black. All text on tag stock and on yellow, 2px opening rules, selected segments and chips, checked boxes, station dots. `ink-2` is secondary text on a tag, `ink-3` is units, axis labels and placeholders.
- **Tag Stock** (`tag`, #fbfcf9): the surface of every tag, ticket and the Start tag. `tag-2` is the quiet fill: an unpicked ticket's strip, verdict chips, table heads, loading bars, the disabled primary button.
- **White** (`white`, #ffffff): type on green, and the fill of fields, so an input reads one step brighter than the tag it sits on.
- **Rules** (`rule`, `rule-strong`): `rule` is the 1px hairline between rows and the chart grid; `rule-strong` is the 1.5px border of fields, chips and quiet buttons, and the unfilled slider track.
- **On-green greys** (`on-green-2`, `on-green-3`): secondary text on green (hints, fine print, idle steps) and the step that cannot be reached yet.
- **Yes tint** (`yes-tint`): the unpressed Yes side and a Yes price.

### Named Rules
**The Green Ground Rule.** Every screen's background is sack green. White never becomes the page; it is always a tag, a ticket or a field sitting on the green.

**The Yellow Means Chosen Rule.** Yellow is a flood, never a tint or an outline, and outside the intro panel and the map it marks exactly one current thing per region: the step you are on, the row you are answering, the contract you have picked. Yellow is never text on tag stock and is not used in the chart, because it cannot hold contrast there.

**The Red Is Pressed On Rule.** Red is for the pin, the stamps, warnings, and No. It never decorates and never fills a surface larger than a button.

**The Yes And No Rule.** Yes prints in green and No prints in red, tinted at rest and solid when pressed. The word is always printed beside the colour, so the pair never depends on hue alone.

## Typography

**Display Font:** Big Shoulders (with Arial Narrow, sans-serif)
**Body Font:** Archivo (with system-ui, -apple-system, Segoe UI, sans-serif)

**Character:** Stencil-weight condensed capitals from sack printing against a plain, slightly wide grotesque for the working text. Both are variable fonts embedded in `frontend/fonts/fonts.css` as data URIs so they survive opening the page from disk.

### Hierarchy
- **Display** (900, `clamp(72px, min(31cqi, 38vh), 360px)`, line-height 0.82, uppercase): the name on the intro panel, two stacked lines sized to the panel's width.
- **Headline** (900, `clamp(40px, 4.4vw, 60px)`, line-height 1.06, uppercase, balanced): one screen title per screen. On the plan the title states the result ("Your plan: $14,945 across 2 markets").
- **Action** (900, `clamp(64px, 6.4vw, 96px)`, line-height 0.9, uppercase): the word on the Start tag only.
- **Name** (800 to 900, 30px, line-height 0.95 to 1, uppercase): the wordmark in the bar, the Contracts heading, and each ticket's market name.
- **Figure** (800, 34 to 40px, line-height 0.95 to 1): the crop value at the foot of the farm tag and the order total. List numerals on the intro use the same face at 1.9em in yellow.
- **Stamp** (800, 21px or 15px small, letter-spacing 0.02em, uppercase): red stamps.
- **Promise** (Archivo 600, `clamp(20px, 2.1vw, 30px)`, line-height 1.3, max 24ch): the single sentence under the name.
- **Lede** (Archivo 400, 18px, line-height 1.4, max 62ch): the sentence under the plan title.
- **Title** (Archivo 700, 16px): the heading of a tag ("Season income", "Your order").
- **Body** (Archivo 400, 15px, line-height 1.45): default reading text. Field values are 15.5px at 600.
- **Label** (Archivo 650, 14 to 14.5px, line-height 1.35): form questions, button text, table values.
- **Note** (Archivo 400, 12.5 to 13.5px): hints, units, fine print, axis labels; capped at 60 to 80ch.

### Named Rules
**The Two Voices Rule.** Big Shoulders is for the name, screen titles, market names, key figures and stamps, always at 800 or 900 and never below 15px. Anything the farmer reads as a sentence or operates as a control is Archivo.

**The Tabular Figures Rule.** Every number that can change or be compared (prices, amounts, table cells, axis ticks, field values) uses tabular numerals.

## Layout

Each screen is a full-height field of green with a two-column split that hands the wider side to the picture and the narrower side to the paper.

- **Intro:** a 62/38 grid. The yellow panel runs from the top edge to the bottom edge with 48px padding, name at the top and the promise with its three ruled spec rows at the bottom. The green side stacks the numbered how-it-works list at the top and the Start tag with fine print at the bottom.
- **Bar (screens 2 and 3):** wordmark, three numbered steps, and the sample-data note pushed to the right; 14px top padding, 28px page padding (`pad`).
- **Farm:** map column at 1.32fr beside the tag at 1fr (minimum 400px), 32px gap. The map column is sticky on wide screens.
- **Plan:** main column at 1.25fr (title, lede, chart tag, live-markets tag) beside the contracts column at 1fr (tickets, order tag), 28px column gap and 20px row gap.
- **Inside a tag:** rows bleed to the tag's edges with negative margins so the hairlines and the yellow flood run the full width; the content inset is 22px on the farm tag and 20px on plan tags. A form row is a two-column grid, question at 0.78fr and control at 1.22fr.

Responsive steps are fixed breakpoints, not fluid padding: at 1100px the plan stacks to one column and a sticky strip in `green-800` carries the plan's result above the tickets; at 900px the farm stacks and the map is capped at 42dvh; at 820px the intro stacks and the Start tag moves directly under the panel; at 560px page padding drops to 14px (`pad-narrow`), form rows stack label over control, and the Yes and No sides split the ticket's width.

## Elevation & Depth

Flat. Depth comes from stock on ground: white tags on green, a yellow panel beside green, a white field on a tag. Nothing at rest casts a shadow, and there are no gradients, blurs or overlays.

### Shadow Vocabulary
- **Tooltip lift** (`box-shadow: 0 8px 18px rgba(9, 36, 22, 0.28)`): the chart tooltip only, the one element that floats over other content.
- **Thumb lift** (`box-shadow: 0 1px 4px rgba(13, 51, 32, 0.45)`): the slider thumb, so it reads as the grabbable part of the track.
- **Eyelet ring** (`box-shadow: 0 0 0 4px` in `rule`): a hard ring, not a shadow; the reinforcement around a tag's punched hole.

### Named Rules
**The Printed Flat Rule.** Surfaces are separated by ink and stock, never by shadow. A shadow is allowed only on something that floats above the print (the tooltip) or is physically grabbed (the slider thumb).

## Shapes

Rectangles with barely eased corners (3px on tags, tickets, fields, buttons, chips and steps; 2px on stamps, the meter and the inside of the segmented control). Circles are reserved for things that are round in the world: eyelets, step numerals, station dots, slider thumbs, the live dot.

Two tags have cut corners made with a clip path: the Start tag is clipped at both left corners (26px) so it points like a luggage tag, and the farm tag has both top corners cut (18px) with an eyelet centred 12px below the top edge. The eyelet is a 14px green hole with a 4px ring (20px with a 5px ring on the Start tag). The plan's tags are plain rectangles without eyelets.

Borders carry meaning by weight: 2px ink opens a group of rows or closes it into a total, 1px `rule` separates rows, 1.5px `rule-strong` outlines a control, 2px red outlines a stamp. Stamps are tilted 2 degrees anticlockwise.

Icons are 18px line drawings (1.75px stroke, round caps and joins, no fill) from one inline sprite: arrow, back, import, info, check, alert, equal, retry.

## Components

### Buttons
Plain and pressable; they shrink slightly when pressed (scale 0.97).
- **Shape:** 3px corners, 1.5px border, 14px Archivo at 650, 38px tall with 14px side padding.
- **Primary:** solid sack green with white text, 48px tall, 16px text, 20px side padding ("See my plan", "Send to Kalshi demo"). Hover darkens to `green-800`. Disabled is `tag-2` with `ink-3` text and a `rule` border.
- **Quiet:** `rule-strong` outline on tag stock with ink text ("Import history", "Table view", "Add to plan", "Check again"). Hover fills `tag-2`; a pressed toggle fills ink with tag-stock text.
- **Text link:** inherits colour, 650 weight, underlined with a 3px offset; the underline thickens to 2px on hover.
- **Focus:** a 2px outline offset 2px, white on green and ink on tags and on yellow.

### Start tag
The one white object on the intro. A tag-stock face at least 132px tall, cut at both left corners, holding an eyelet, the word START in the Action size and a 52px arrow. Hover floods the face yellow and slides the arrow 8px right; press scales it to 0.98; focus is a 3px yellow outline offset 4px (drawn on the link, outside the clipped face).

### Steps
Three numbered links in the bar. Each has a 22px outlined circle with its number and a 14px label at 600 in `on-green-2`. Hover fills `green-600`. The current step floods yellow with ink text. A step that cannot be reached yet is `on-green-3` and inert.

### Tags
- **Corner Style:** 3px, or cut corners on the farm tag.
- **Background:** tag stock, ink text.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** none; the edge is the change from green to white.
- **Internal Padding:** 16px 20px 18px on plan tags; 40px 22px 22px on the farm tag to clear the eyelet.
- **Head:** a 16px/700 title on the left, with a stamp or a quiet button on the right.

### Ruled rows
The system's one data form, used at every size: the spec list on the intro panel, form rows, the analysis table, order lines, live-market rows. Label left, value right, 1px hairline between rows, a 2px ink rule above the first row and above a total. In the form, the row that holds focus floods yellow edge to edge (150ms). Notes and errors sit under the control in the value column.

### Inputs / Fields
- **Style:** white fill, 1.5px `rule-strong` border, 3px corners, 40px tall. The unit sits inside the field: a leading "$" in ink at 600, a trailing unit ("acres", "bu/acre", "per bushel") in `ink-3`.
- **Focus:** the border turns ink and a 2px ink outline appears 1px out; the row behind it floods yellow.
- **Error:** the border turns red and a `red-deep` message at 13.5px/600 with an alert icon appears under the control.
- **Slider:** a 6px track, sack green up to the value and `rule-strong` after it, with a 20px ink thumb ringed in white. Number fields that have a range are paired with a slider on the same row.

### Segmented control and chips
- **Segmented (one of three):** a white box with a 1.5px ink border and 3px padding; the chosen segment is solid ink with white text, others fill `tag-2` on hover.
- **Chips (any of three):** white with a 1.5px `rule-strong` border and a faint check icon; chosen chips turn solid ink with white text and a full-strength check.

### Stamps
Red Big Shoulders capitals in a 2px red outline with 2px corners, tilted 2 degrees, with no fill on a tag and a tag-stock fill on green. Used for the place name on the farm tag (21px) and for "Sample" and "Demo only" marks beside headings (15px, 1.5px outline). When the place is set, the stamp presses in after the pin lands.

### Map
The lower 48 states in yellow with 1px green borders on the green ground, crosshair cursor, states lighten to `yellow-light` on hover. Weather stations are ink dots; the nearest one gets a white ring, a 2px ink line from the pin, and a 13.5px/700 ink label haloed in yellow. The pin is red with a white outline and a white eye.

### Contract tickets
A tag-stock ticket with a 52px pick strip down its left edge holding a 24px checkbox. In the plan, the strip floods yellow, the box fills ink with a white check, and the market name and cost print in ink; out of the plan, the strip is `tag-2` and the name and cost drop to `ink-3`. The body carries the market name in the Name size with its cost at 17px/700 on the right, the question in `ink-2`, then the Yes and No sides (68 by 50px each: the word at 12px over the price at 18px) beside an amount field and slider, then one line on why, ending in a verdict chip (`tag-2`, 13px/650, with a small icon).

### Season income chart
Two distributions stacked on one ruled grid with a shared money axis: "Without protection" above in `green-300`, "With your plan" below in sack green. Columns have a 2px gap, each band sits on a 1px ink baseline, vertical and horizontal grid lines are 1px `rule`, and axis ticks are 12px `ink-3`. Each band has a 1.5px ink marker for the 1-in-20 season with a 12.5px/650 label haloed in tag stock. Hover darkens the column and shows a crosshair with a bordered tooltip; a quiet toggle swaps the plot for a scrolling table of the same bins. Columns move to new heights in 200ms. Under it, the analysis is ruled rows in three figure columns.

### Order
A tag with a 10px budget meter (sack green fill on `rule`, turning red when over the limit), a budget line, order lines as ruled rows, a total closed by a 2px ink rule with the amount in the Figure size, and a full-width primary button.

## Do's and Don'ts

### Do:
- **Do** put every screen on sack green (`green-700`) and keep white for tags, tickets, fields and type on green.
- **Do** flood with yellow to show the one current or chosen thing in a region: the step, the focused row, the picked ticket.
- **Do** set data as ruled rows, label left and value right, with a 2px ink rule opening the group and 1px `rule` hairlines between rows.
- **Do** use Big Shoulders at 800 or 900 in capitals for the name, screen titles, market names, key figures and stamps, and Archivo for everything else.
- **Do** print Yes in green and No in red with the word beside the colour, tinted at rest and solid when pressed.
- **Do** stamp sample and demo data in red beside its heading, and keep the stamp's 2 degree tilt.
- **Do** draw charts as two stacked bands on one shared ruled grid, `green-300` without protection and `green-700` with the plan.
- **Do** keep moves on `cubic-bezier(0.23, 1, 0.32, 1)` at 120 to 280ms, and give each one a fade-only fallback under reduced motion.
- **Do** use tabular numerals for every price, amount and table figure.

### Don't:
- **Don't** make white the page background or lay tags out as a white wizard with a progress bar and rounded cards.
- **Don't** use yellow in the chart or as text on tag stock; it cannot hold contrast there.
- **Don't** use red for decoration or for any surface larger than a button; it is the pin, the stamps, warnings and No.
- **Don't** add a fourth ink. Neutrals come from the green (`ink`, `ink-2`, `ink-3`, `rule`, `rule-strong`, `tag-2`).
- **Don't** add shadows to tags, tickets or buttons; only the chart tooltip and the slider thumb have one.
- **Don't** round corners past 3px; circles are for eyelets, step numerals, dots and thumbs.
- **Don't** write as Farmer Joe. It is the product's name, not a speaking character.
- **Don't** show a sample or assumed number without its label.
