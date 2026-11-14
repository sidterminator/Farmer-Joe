---
name: bizfax
description: Weather hedging for farms, a blue jacket stitched in corn gold.
colors:
  blue-900: "#0a1d45"
  blue-800: "#0f2a5f"
  blue-700: "#183a7a"
  blue-600: "#24509f"
  blue-500: "#3d5a96"
  edge-on-blue: "#7b94cc"
  rib: "#4b7ad6"
  rib-hover: "#7fa3ec"
  on-blue: "#ffffff"
  on-blue-2: "#c9d6f2"
  on-blue-3: "#9fb4e0"
  paper: "#f4f7fc"
  paper-2: "#e6ecf7"
  line: "#d3dcec"
  line-strong: "#aebbd6"
  ink: "#0f2a5f"
  ink-2: "#44557a"
  ink-3: "#5a6b8f"
  gold: "#f2c230"
  gold-hover: "#ffd75c"
  yes: "#1f7a3d"
  yes-deep: "#17622f"
  yes-tint: "#dff3e4"
  yes-ink: "#0b5c2a"
  no: "#b3372f"
  no-deep: "#962a23"
  no-tint: "#fbe3e0"
  no-ink: "#8f1f1a"
typography:
  headline:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "21px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.012em"
  figure:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "21px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.01em"
  brand:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "19px"
    fontWeight: 750
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  section:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 650
  body:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.45
  support:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.35
  control:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "13.5px"
    fontWeight: 550
  data:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    fontFeature: "tnum"
  label:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "12.5px"
    fontWeight: 550
rounded:
  swatch: "3px"
  chip: "6px"
  control: "8px"
  card: "10px"
  panel: "12px"
spacing:
  tight: "8px"
  row: "12px"
  stack: "16px"
  panel-x: "22px"
  pad: "28px"
  column-gap: "30px"
  ribbon-gutter: "46px"
components:
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "34px"
  button-quiet-hover:
    backgroundColor: "{colors.paper-2}"
  button-quiet-pressed:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  button-on-blue:
    backgroundColor: "transparent"
    textColor: "{colors.on-blue}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "34px"
  button-on-blue-hover:
    backgroundColor: "{colors.blue-700}"
  saved-toggle-on:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.blue-800}"
    rounded: "{rounded.control}"
  tab:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    padding: "11px 12px 12px"
  tab-selected:
    textColor: "{colors.ink}"
  panel:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "10px 22px 20px"
  plot:
    backgroundColor: "{colors.blue-800}"
    textColor: "{colors.on-blue-3}"
    rounded: "{rounded.control}"
  tooltip:
    backgroundColor: "{colors.blue-900}"
    textColor: "{colors.on-blue}"
    typography: "{typography.label}"
    padding: "9px 11px 10px"
  market-card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "8px 8px 8px 0"
  side-yes:
    backgroundColor: "{colors.yes-tint}"
    textColor: "{colors.yes-ink}"
    typography: "{typography.figure}"
    rounded: "{rounded.control}"
    width: "74px"
    height: "72px"
  side-yes-pressed:
    backgroundColor: "{colors.yes}"
    textColor: "{colors.on-blue}"
  side-no:
    backgroundColor: "{colors.no-tint}"
    textColor: "{colors.no-ink}"
    typography: "{typography.figure}"
    rounded: "{rounded.control}"
    width: "74px"
    height: "72px"
  side-no-pressed:
    backgroundColor: "{colors.no}"
    textColor: "{colors.on-blue}"
  verdict:
    backgroundColor: "{colors.paper-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.chip}"
    padding: "2px 9px 2px 7px"
  upload-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.panel}"
    padding: "5px 5px 5px 14px"
    height: "48px"
  send:
    backgroundColor: "{colors.blue-600}"
    textColor: "{colors.on-blue}"
    rounded: "{rounded.control}"
    width: "40px"
    height: "38px"
  send-ready:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.blue-800}"
---

# Design System: bizfax

## Overview

**Creative North Star: "The Stitched Jacket"**

The screen is a blue corduroy jacket with gold stitching: FFA-jacket blue covers the whole shell, cool near-white panels sit on it as work surfaces, and corn gold is thread, used only where something belongs to the farmer. No emblem is drawn anywhere; the jacket is carried by the colour pair, the ribbed plot and the dashed gold line alone.

It is a working screen for one job, read at a glance and operated with a few controls: income spread on the left, markets on the right, the farmer's data along the bottom. Density is moderate. Numbers are the content, so they are bold, right-aligned and aligned by digit; prose is short and sits in a quieter ink. Motion is brief and only ever reports a state change.

The system does not look like a white fintech dashboard of grey cards with green and red tickers. Blue is the ground, not an accent, and green and red are confined to the two prices a farmer chooses between.

**Key Characteristics:**
- A deep blue ground across the shell, with light panels as the only work surfaces.
- Corn gold means "the farmer's own" and nothing else.
- One chart form: fine vertical ribs on a blue plot field, with a dashed gold outline for the hedge.
- Green and red only on Yes and No prices.
- One typeface, Public Sans, with tabular right-aligned figures.
- Flat surfaces; depth comes from the blue and paper tones.
- Sample and assumed numbers are labelled on screen, in the header and the status line.

## Colors

Two voices, blue and corn gold, on cool paper neutrals; green and red are a closed pair used for one decision.

### Primary
- **Jacket Blue** (`blue-800`): the shell ground and every plot field. Also the ink colour on paper (`ink` is the same value), so text and ground are one blue.
- **Night Blue** (`blue-900`): the chart tooltip surface, one step below the plot field.
- **Field Blue** (`blue-700`, `blue-600`): hover and pressed fills for controls on the blue ground; `blue-600` is also the slider fill, the send button at rest, the Saved count pill and the focus ring on paper.
- **Rule Blue** (`blue-500`, `edge-on-blue`): `blue-500` rules the chart baseline and the tooltip edge; `edge-on-blue` is the border of controls and the dashed empty-state frame on the blue ground.
- **Rib Blue** (`rib`, `rib-hover`): the bars of the distribution. `rib-hover` is the one rib under the pointer.

### Secondary
- **Corn Gold** (`gold`, `gold-hover`): the farmer's own. It appears as the dashed outline around the selected market card, the dashed hedged-income line, the ribs for seasons where the held contract pays, the filled bookmark of a saved market, the Saved toggle when it is filtering, the dot before "Using your data", the send arrow once the field holds something, and the text selection colour. Text on gold is `blue-800`.

### Tertiary
- **Yes Green** (`yes`, `yes-deep`, `yes-tint`, `yes-ink`): the Yes price button. Tint with dark green text at rest; solid green with white text when that side is held; `yes-deep` on hover of the held side.
- **No Red** (`no`, `no-deep`, `no-tint`, `no-ink`): the No price button, same four-step pattern.

### Neutral
- **Cool Paper** (`paper`): the main panel, market cards and the upload field.
- **Paper Shade** (`paper-2`): hover fill for quiet buttons, the sticky table header and the verdict chip.
- **Hairline** (`line`, `line-strong`): `line` divides table rows, rules the tab strip and is the empty part of the slider track; `line-strong` borders quiet buttons.
- **Ink** (`ink`, `ink-2`, `ink-3`): headings and figures; supporting prose and row labels; column heads, meta lines and placeholders.
- **On Blue** (`on-blue`, `on-blue-2`, `on-blue-3`): primary text on the blue ground; secondary text and status lines; axis labels, the markets note and the fine print.

### Named Rules
**The Farmer's Gold Rule.** Gold marks what is the farmer's own: the selected market, the hedged income, the held side's payout, saved markets, uploaded data, and the send arrow once there is something to send. A gold mark anywhere else is a mistake.

**The Yes and No Rule.** Green and red appear only on Yes and No price buttons. Gains, losses, errors and verdicts are not coloured: the Change column is plain ink, an error is white text with an alert icon, and "Cheap" or "Expensive" is a neutral chip with an icon.

**The One Emphasis Series Rule.** Gold is deliberately much lighter than Rib Blue and sits outside the lightness band a categorical chart palette would keep. That is intended: a plot has one blue series and at most one gold emphasis series. Colour-blind separation and contrast against the plot field hold. Do not add a third series colour.

## Typography

**Display Font:** Public Sans (with system-ui, -apple-system, Segoe UI, sans-serif)
**Body Font:** Public Sans (same stack)

**Character:** One plain, sturdy sans in a variable weight, embedded with the page so it survives being opened from disk. Hierarchy comes from weight and ink tone more than size; the whole ramp sits between 12.5px and 21px.

### Hierarchy
- **Headline** (700, 21px, 1.2, -0.012em): the panel title, one per view, balanced across lines. 19px at 640px and below.
- **Figure** (700, 20 to 21px, 1.1, -0.01em): the Yes and No prices and the hedge-size readout.
- **Brand** (750, 19px, -0.01em): the product name in the header, lower case, set as text.
- **Title** (700, 18px, 1.2, -0.01em): a market's name on its card.
- **Section** (650, 16px): the "Markets" heading on the blue ground.
- **Body** (400, 15px, 1.45): the base size, the upload field and the Import button.
- **Support** (400, 13.5 to 14px, 1.35 to 1.45): the lede under the headline, market questions, notes and status lines, in `ink-2` or `on-blue-2`. Explanatory prose is capped at 62ch, status lines at 70ch.
- **Control** (550, 13.5px; tabs 14.5px): button and tab labels, never wrapped.
- **Data** (600, 14px, tabular): table cells. Row labels are 500 in `ink-2`.
- **Label** (550 to 600, 12 to 12.5px): column heads, the Yes and No words, settle lines, axis ticks, chart direct labels, tooltip text and the fine print.

### Named Rules
**The Right-Aligned Figures Rule.** Figures in tables are right-aligned with tabular numerals, so digits stack by place; the first column holds the row label, left-aligned. Axis ticks and tooltip values are tabular too.

**The Sentence Case Rule.** Labels are sentence case at normal tracking. Nothing in the build is set in tracked capitals; "YES" and "NO" are capitalised only where prose names the contract side.

## Layout

A full-height shell of three rows: a header strip, the work area, and a dock pinned to the bottom. The work area and the dock share one two-column grid (about 1.72 to 1, the right column never under 340px, 30px between columns), so Import lines up under the main panel and the upload field under the market cards. Outer padding is 28px.

The left column is one light panel: an underline tab strip with a "Table view" toggle, then a headline with the chart key beside it, the plot (at least 260px tall, growing to fill), and below it a two-part row with the comparison table and the hedge controls. The right column lists market cards 16px apart on the blue ground. Each card keeps a 46px gutter on its right where its bookmark hangs, and the dock's right side keeps the same gutter so the upload field ends flush with the cards.

Inside a card the furniture is fixed: name, question and settle line on the left; two 74px price buttons on the right; the bookmark outside the right edge.

At 1080px and below the two columns stack: panel, markets, then the dock in one column. At 640px and below the outer padding drops to 14px and the gutter to 40px, the sample-data notice moves under the farm line, the row under the plot becomes one column, and each card puts its two price buttons in a full-width row under the text. Table cells may wrap at that width; they never wrap above it.

Rhythm is built from 8, 12 and 16px gaps, with 22px inside the panel and 28px at the page edge.

## Elevation & Depth

Flat. Depth is tonal: paper surfaces on the blue ground, the blue plot field set into the paper panel, and the darker tooltip over the plot. Surfaces have no borders or shadows at rest; cards and the panel separate from the ground by tone alone.

### Shadow Vocabulary
- **Tooltip lift** (`box-shadow: 0 8px 20px rgba(3, 10, 28, 0.5)`): the chart tooltip, the only floating element.
- **Thumb lift** (`box-shadow: 0 1px 4px rgba(15, 42, 95, 0.4)`): the slider thumb, so it reads as the thing to grab.

### Named Rules
**The Tone Before Shadow Rule.** A surface is separated by its tone against the ground. Shadow is kept for the two things that sit above a surface: the tooltip and the slider thumb.

## Shapes

Softly rounded rectangles on a short scale: 12px for the panel and the upload field, 10px for market cards and the empty-state frame, 8px for controls, price buttons and the plot field, 6px for small chips and the verdict, 3px for legend swatches. The only circles are the slider thumb, the Saved count pill and the status dot.

Lines are 1px hairlines; borders appear only on controls (quiet buttons, on-blue buttons) and on the scrolling table frame. Dashes mean thread: gold lines are always dashed (the hedge outline at 8 on, 5 off; the selection outline around a card, 2px, offset 4px so it sits on the blue ground). The one non-gold dash is the empty-state frame.

Ribs are thin vertical bars with a 2px gap and rounded tops. The bookmark is a swallow-tailed flag drawn in outline, filled when saved. Icons are 1.75px round-capped line drawings at 16 to 20px.

## Components

### Buttons
Plain, compact and outlined; they change fill, never size.
- **Shape:** gently rounded (8px), at least 34px tall, 12px side padding, 13.5px label at weight 550.
- **Quiet (on paper):** transparent with a `line-strong` border and `ink` label. Hover fills `paper-2`, active fills `line`. When it is a toggle and on, it inverts to `ink` with a `paper` label. Disabled drops to `ink-3` text and a `line` border.
- **On blue:** transparent with an `edge-on-blue` border and white label. Hover fills `blue-700` and lightens the border; active fills `blue-600`. Import is the larger version: 44px tall, 15px label, 20px icon.
- **Saved toggle:** an on-blue button with a bookmark icon and a count pill (`blue-600`). When filtering to saved markets it turns gold with `blue-800` text, and the pill inverts to `blue-800`.
- **Text link (on blue):** white, underlined with a 3px offset; the underline thickens on hover.
- **Focus:** a 2px outline offset 2px, white on the blue ground and `blue-600` on paper.
- **Motion:** background, border and text colour change over 150ms with the system ease.

### Tabs
Underline tabs on the panel's top rule. Labels are 14.5px at weight 550 in `ink-2`; the selected tab is `ink` with a 2px `ink` bar that sits on the rule. No fill, no pill.

### Cards / Containers
- **Main panel:** `paper`, 12px corners, 10px 22px 20px padding, no border or shadow.
- **Market card:** `paper`, 10px corners, a text block and two price buttons. The text block is itself the control that selects the market; hovering it underlines the name. The selected card gains a 2px dashed gold outline offset 4px.
- **Empty state:** a 1px dashed `edge-on-blue` frame with 10px corners on the blue ground, one sentence that says what to do, and one on-blue button.

### Price Buttons (Yes and No)
The only green and red on the screen. Each is 74px wide and at least 72px tall (full width and 54px on small screens) with 8px corners, a 12.5px word over a 21px price. At rest: tint fill, dark same-hue text. Held: solid fill, white text. Hover deepens whichever state it is in. The word is always present; the colour never carries the meaning alone.

### Bookmark
A swallow-tailed flag hanging off each card's right edge in the gutter, 42 by 30px. Unsaved: a 1.75px outline in `on-blue-3`, brightening to white with a `blue-700` fill on hover. Saved: solid gold, `gold-hover` on hover.

### Inputs / Fields
- **Upload field:** a `paper` bar with 12px corners, 48px tall, holding a borderless 15px text input and the send button at its right end. The placeholder is `ink-3` and shows the expected format. Focus anywhere inside draws a 2px white outline around the whole bar.
- **Send:** 40 by 38px, 8px corners, `blue-600` with a white paper-plane icon at rest. Once the field holds text or a staged file it turns gold with a `blue-800` icon.
- **Staged file chip:** replaces the input inside the bar: file icon, name and season count at 14.5px weight 550, truncated with an ellipsis, and a 28px remove button.
- **Slider:** a 6px track, `blue-600` up to the thumb and `line` beyond; an 18px `ink` thumb with a 2px `paper` ring that grows slightly on hover. A small `ink-3` tick under the track marks the steadiest hedge size. The current value is shown above at 20px weight 700.
- **Status line:** a sentence beside or above the field in `on-blue-2`. Success from the farmer's data is prefixed with a gold dot; an error turns white with an alert icon and says what to type. The row keeps its height when empty so a message never moves the layout.

### Tables
No frame and no zebra. Rows are separated by `line` hairlines, 7px by 12px cell padding. Column heads are 12.5px in `ink-3`, row labels 500 in `ink-2`, figures 600 in `ink`, right-aligned. The table view of a chart sits in a bordered, scrolling box with a sticky `paper-2` header.

### Verdict Chip
A neutral `paper-2` chip, 6px corners, with a 15px icon (check, alert or equals) and a short phrase in `ink` at weight 600. It states whether a price is cheap, expensive or about fair without colour.

### Rib Plot (signature)
The one chart form. A `blue-800` field with 8px corners inside the paper panel:
- **Ribs:** the distribution as thin vertical bars in `rib`, 2px apart, tops rounded. Ribs are gold where the held contract pays.
- **Stitch:** the hedged distribution as a 2px dashed gold outline (8 on, 5 off, round caps) with a 6px `blue-800` stroke beneath it so it stays legible across the ribs.
- **Scaffold:** faint horizontal grid lines, a `blue-500` baseline, tabular 12px ticks in `on-blue-3`, and a small axis caption at top left. A threshold is a 1px `on-blue-2` vertical with a white 12.5px label above it.
- **Labels:** series are named directly on the plot in white 12.5px text with a `blue-800` halo and a small key mark; a legend above repeats them using swatches cut from the plot field (ribs, gold ribs, or a dashed gold line).
- **Hover and focus:** the plot is focusable. The rib under the pointer lightens, a 1px crosshair appears, and a `blue-900` tooltip (7px corners, `blue-500` edge) lists each series with a key bar and a bold tabular value.
- **Motion:** ribs resize over 200ms with the system ease when the hedge changes; hover colour changes in 120ms. With reduced motion, transitions are effectively instant.
- **Alternative:** "Table view" swaps the plot for the same data as a table.

## Do's and Don'ts

### Do:
- **Do** keep the shell on `blue-800` and put working content on `paper` surfaces.
- **Do** reserve gold for the farmer's own: selection, hedged income, the held side's payout, saved markets, uploaded data, a ready send arrow.
- **Do** draw every distribution as ribs on a blue plot field, and the hedge as the dashed gold outline over them.
- **Do** set text on gold in `blue-800`.
- **Do** right-align figures in tables and use tabular numerals.
- **Do** pair every colour signal with a word or an icon (the Yes and No words, the verdict icon, the alert icon on errors).
- **Do** keep state changes at 200ms or less, using the system ease `cubic-bezier(0.16, 1, 0.3, 1)`.
- **Do** name chart series directly on the plot and repeat them in the legend with plot-field swatches.
- **Do** keep the sample-data notice in the header and say whose data is in use in the status line.

### Don't:
- **Don't** use green or red outside the Yes and No price buttons, including for gains, losses, errors or verdicts.
- **Don't** use gold as decoration, as a generic primary-button colour, or as text on paper.
- **Don't** add a second chart form or a third series colour.
- **Don't** add borders or shadows to panels and cards; only the tooltip and the slider thumb carry a shadow.
- **Don't** draw an emblem, crest or logo mark; the brand is the lower-case word in the header.
- **Don't** introduce a second typeface or tracked capitals.
- **Don't** animate for decoration; nothing moves unless a value or a state changed.
