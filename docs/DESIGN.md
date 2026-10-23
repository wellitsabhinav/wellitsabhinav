# Design system

The first screen identifies Abhinav Choudhary and his engineering disciplines in selectable text. Four project entries follow: problem, approach, result, tools, status, and direct reproduction/report links. Merged upstream work is separated from dated open proposals. Industry, education and tools stay concise. Activity follows the principal engineering content.

Semantic Markdown headings, descriptive links and GitHub-compatible `<picture>` / `<img>` markup keep the page parsable. There are no critical collapsed details, custom JavaScript/CSS, remote fonts, image-only achievements, badge walls or third-party statistics widgets. Existing project reports remain authoritative. Experimental source, measurements and research conclusions are unchanged.

| Role | Dark | Light |
|---|---|---|
| Canvas | `#0D1117` graphite | `#FFFFFF` |
| Architectural panel | `#101C2C` navy | `#F3F7FB` |
| Main text | `#F0F6FC` | `#101C2C` |
| Secondary text | `#A9B5C4` | `#4B5E73` |
| Cyan accent | `#00D4FF` | `#006B87` |
| Supporting accent | Emerald / violet | Deep emerald / violet |

The requested slate `#8B949E` informs secondary colors; brighter dark-theme secondary text improves readability. Cyan is darkened on white for contrast. SVG typography uses system Arial/Helvetica, alongside GitHub's normal Markdown typography.

Branding combines a memory array, logic floorplan and timing trace as abstract identity geometry, not a project measurement. `assets/header.svg` remains as historical branding for existing links. The licensed MOTIF trace remains unchanged with exact source, license and notice; it is linked, not recolored.

Generated SVGs carry a `viewBox`, title/description and README alternative text. The calendar preserves API-provided intensities. Narrow screens receive four larger-cell calendar panels. Trend/statistics use 480-unit layouts. The timeline stays an optional link because seven tall milestones would repeat the prominent text contribution section.

The upstream evidence list uses normal paragraphs/bullets so its status text remains visible on narrow screens. Picture media queries follow the browser/system color preference; a manually overridden GitHub theme can show a dark panel on a light page (or the reverse). Each panel has its own high-contrast canvas and remains readable. Both explicit SVG variants are kept for direct inspection.

[Platane/snk](https://github.com/Platane/snk) was evaluated. It animates real contribution squares, but motion and another action dependency do not add engineering evidence here. The static calendar and analytical trends better serve this design; no animation is installed.

Run `python scripts/validate_profile.py` and `python -m unittest discover -s tests -v`. Inspect the actual GitHub branch README at desktop/mobile widths and check picture sources and normal text. A local preview alone cannot establish GitHub sanitization behavior. See [maintenance](MAINTENANCE.md).
