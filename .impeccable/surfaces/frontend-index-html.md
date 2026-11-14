---
version: 1
slug: "frontend-index-html"
primary_target: "frontend/index.html"
related_targets: []
---

# Hedging screen (frontend/index.html)

Scope: the single app screen of the weather-hedging tool. Visitor mode: Operate.

Audience and job: a farmer checking which weather contracts would steady this season's income, then adding their own seasons of data. Task order: read the income spread, pick a market and a side, size the hedge, save markets, upload farm data.

Content: three sample markets (Temp, Yield, Rain) with YES and NO prices, a sample farm, a simulated set of seasons. Everything is sample data and the screen says so.

Constraints: layout follows the user's sketch (main panel left, market cards right with a bookmark on each, Import bottom left, upload field with send arrow bottom right). Static HTML/CSS/JS, opens from disk with no server.

Unresolved: upload file format, whether real markets exist for crop yield, what the icon above the upload field in the sketch means (built as a Saved filter).

## Direction contract

THESIS: A farmer's season income shown as cloth and thread. The spread without a hedge is the fabric; the hedge is stitched over it in gold. It refuses the white fintech dashboard whose whole identity is grey cards and green and red tickers.

OWN-WORLD: Deep blue ground across the shell, cool near-white work surfaces, corn gold only for what is the farmer's own (selected market, hedged income, saved markets, uploaded seasons). Public Sans throughout with tabular right-aligned figures. Plot fields are blue swatches ruled in fine vertical ribs; gold marks are dashed like chain-stitch. Green and red appear only on YES and NO prices.

STORY: The farmer sees the season income spread, picks a market and a side, drags the hedge size, and watches the spread tighten while the cost rises. They save markets and add their own seasons.

FIRST VIEWPORT: 1440 x 900. Blue header strip with the name, the farm line and the sample-data label. Left 62 percent: light panel with Income and Forecast tabs, a blue ribbed plot about 360px tall, a comparison table, and the hedge-size slider. Right: three market cards on the blue ground, each with YES and NO price buttons and a bookmark ribbon hanging off its right edge. Bottom left: Import. Bottom right: the Saved toggle above the upload field with its send arrow.

FORM: FFA-jacket blue and corn gold, no emblem; position 7 of 7 on the grounded list; seed:867457940cae9466. Signature interaction: dragging the hedge size re-stitches the gold outline, the table and the cost together. Motion grammar: state changes land in 200ms or less, ribs resize with an ease-out, nothing decorative. Raises: fixed furniture per card (character goods catalog); one job per colour (terminal wayfinding); one control remaps the page (type specimen); right-aligned running figures (cassette j-card); short stepped state changes (acetate manual).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
