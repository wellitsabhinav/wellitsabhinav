"""Render deterministic, self-contained light/dark activity SVGs from a validated snapshot."""
import argparse
from datetime import date, timedelta
from html import escape
import json
from pathlib import Path

from fetch_activity import ROOT, validate

PALETTES = {
    'dark': {'bg': '#0D1117', 'panel': '#101C2C', 'fg': '#F0F6FC', 'muted': '#A9B5C4', 'grid': '#304052',
             'accent': '#00D4FF', 'violet': '#C0A5FF', 'green': '#72E0B4', 'amber': '#FFC479',
             'levels': ['#1D2B3A', '#174C67', '#147395', '#00A5C7', '#00D4FF']},
    'light': {'bg': '#FFFFFF', 'panel': '#F3F7FB', 'fg': '#101C2C', 'muted': '#4B5E73', 'grid': '#CBD5E1',
              'accent': '#006B87', 'violet': '#7042B6', 'green': '#15734F', 'amber': '#8E5700',
              'levels': ['#E6EDF3', '#B8E7F0', '#67BFD3', '#1383A0', '#00566F']},
}


class SVG:
    def __init__(self, width, height, title, description, palette):
        self.p = palette
        self.items = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" role="img" aria-labelledby="title desc">',
                      f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
                      f'<rect width="{width}" height="{height}" rx="12" fill="{palette["bg"]}"/>',
                      '<g font-family="Arial, Helvetica, sans-serif">']

    def text(self, x, y, text, size=15, color=None, **attrs):
        extras = ' '.join(f'{k.replace("_", "-")}="{escape(str(v))}"' for k, v in attrs.items())
        self.items.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color or self.p["fg"]}" {extras}>{escape(str(text))}</text>')

    def line(self, x1, y1, x2, y2, color=None, **attrs):
        extras = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        self.items.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color or self.p["grid"]}" {extras}/>')

    def finish(self):
        return '\n'.join(self.items + ['</g></svg>']) + '\n'


def footer(s, data, y, size=13):
    s.text(24, y, f'GitHub API · through {data["end"]} UTC', size, s.p['muted'])


def calendar(data, p, mobile=False):
    start = date.fromisoformat(data['start'])
    sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    total_weeks = (date.fromisoformat(data['end']) - sunday).days // 7 + 1
    width, cell, pitch = (480, 23, 28) if mobile else (960, 12, 16)
    chunk = 14 if mobile else total_weeks
    panels = (total_weeks + chunk - 1) // chunk
    panel_h = 257 if mobile else 160
    height = 106 + panels * panel_h + 72
    title = 'Contribution activity monitor'
    s = SVG(width, height, title, f'{data["calendar_total"]} GitHub-visible contributions from {data["start"]} to {data["end"]}. Dates and intensity levels are supplied by GitHub. Private aggregates may be included if enabled; this is not a commit count.', p)
    s.text(24, 34, 'CONTRIBUTION ACTIVITY', 19 if mobile else 18, p['accent'], font_weight=700, letter_spacing=1)
    s.text(24, 62, f'{data["calendar_total"]:,} contributions · 365 days', 21, font_weight=700)
    s.text(24, 86, f'{data["start"]} — {data["end"]}', 15, p['muted'])
    for panel in range(panels):
        y0 = 132 + panel * panel_h
        months_seen = set()
        last_month_x = -100
        for d in data['days']:
            day = date.fromisoformat(d['date'])
            offset = (day - sunday).days
            week, weekday = divmod(offset, 7)
            if week // chunk != panel:
                continue
            x, y = 57 + (week % chunk) * pitch, y0 + weekday * pitch
            month = day.strftime('%b')
            month_key = day.strftime('%Y-%m')
            if month_key not in months_seen and (day.day == 1 or week % chunk == 0) and x - last_month_x >= (56 if mobile else 35):
                s.text(x, y0 - 14, month, 16 if mobile else 13, p['muted'])
                months_seen.add(month_key)
                last_month_x = x
            s.items.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{p["levels"][d["level"]]}" stroke="{p["grid"]}" stroke-width=".5" data-date="{d["date"]}" data-count="{d["count"]}" data-level="{d["level"]}"><title>{d["date"]}: {d["count"]} contributions; GitHub intensity {d["level"]}/4</title></rect>')
        for weekday, label in [(1, 'M'), (3, 'W'), (5, 'F')]:
            s.text(26, y0 + weekday * pitch + cell - 1, label, 16 if mobile else 13, p['muted'])
    legend_y = height - 54
    s.text(24, legend_y + 12, 'Less', 15, p['muted'])
    for i, color in enumerate(p['levels']):
        s.items.append(f'<rect x="{67 + i * 23}" y="{legend_y}" width="18" height="18" rx="2" fill="{color}" stroke="{p["grid"]}"/>')
    s.text(192, legend_y + 13, 'More · GitHub levels 0–4', 15, p['muted'])
    footer(s, data, height - 14, 14 if mobile else 13)
    return s.finish()


def trend(data, p):
    # Small multiples share exact counts, never a misleading dual axis or a stacked total.
    s = SVG(480, 648, 'Monthly development activity', 'Four separate linear time series: API-visible eligible commit contributions, pull requests, issues, and pull request reviews. Partial boundary months are included. Values are in the linked JSON and Markdown table.', p)
    s.text(24, 34, 'DEVELOPMENT ACTIVITY', 19, p['accent'], font_weight=700, letter_spacing=1)
    s.text(24, 59, 'Monthly counts · partial boundary months', 16, p['muted'])
    series = [('commits', 'Eligible commit contributions', p['accent']), ('prs', 'Pull request contributions', p['violet']),
              ('issues', 'Issue contributions', p['green']), ('reviews', 'Pull request review contributions', p['amber'])]
    n = len(data['monthly'])
    for index, (key, label, color) in enumerate(series):
        top = 92 + index * 132
        values = [m[key] for m in data['monthly']]
        ceiling = max(1, max(values))
        s.text(24, top, label, 17, color, font_weight=700)
        s.text(450, top, f'Σ {sum(values):,}', 16, p['muted'], text_anchor='end')
        for fraction in (0, .5, 1):
            y = top + 76 - fraction * 58
            s.line(61, y, 450, y, stroke_dasharray='3 4')
            s.text(52, y + 5, f'{ceiling * fraction:g}', 13, p['muted'], text_anchor='end')
        points = []
        for i, (value, month) in enumerate(zip(values, data['monthly'])):
            x = 61 + i * 389 / max(1, n - 1)
            y = top + 76 - value / ceiling * 58
            points.append(f'{x:.2f},{y:.2f}')
            s.items.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"><title>{month["start"]} to {month["end"]}: {value} {escape(label)}</title></circle>')
        s.items.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
        for i in range(n):
            if i in {0, n // 3, 2 * n // 3, n - 1}:
                d = date.fromisoformat(data['monthly'][i]['start'])
                s.text(61 + i * 389 / max(1, n - 1), top + 101, d.strftime('%b %y'), 12, p['muted'], text_anchor='middle')
    footer(s, data, 638, 14)
    return s.finish()


def stats(data, p):
    s = SVG(480, 424, 'Verified GitHub activity statistics', f'Public repository inventory at refresh, activity from {data["start"]} to {data["end"]}. Merged PRs count merge dates, opened PRs count creation dates.', p)
    s.text(24, 34, 'VERIFIABLE ACTIVITY', 19, p['accent'], font_weight=700, letter_spacing=1)
    s.text(24, 60, f'{data["start"]} — {data["end"]}', 16, p['muted'])
    labels = [('public_repositories', 'Public repositories · current inventory'),
              ('original_repository_stars', 'Stars on owned original repositories'),
              ('visible_commit_contributions', 'API-visible eligible commit contributions'),
              ('prs_opened', 'Public pull requests opened in period'),
              ('prs_merged', 'Public authored PRs merged in period'),
              ('external_prs_opened', 'Public PRs opened outside owned repos')]
    for i, (key, label) in enumerate(labels):
        y = 102 + i * 48
        s.text(24, y, label, 15, p['muted'])
        s.text(452, y + 3, f'{data["stats"][key]:,}', 23, font_weight=700, text_anchor='end')
        s.line(24, y + 16, 454, y + 16)
    s.text(24, 393, 'Sources: public REST + GraphQL; see data notes.', 14, p['muted'])
    footer(s, data, 414, 14)
    return s.finish()


def timeline(data, p):
    height = 104 + len(data['milestones']) * 94
    s = SVG(480, height, 'Evidence-linked open-source contributions', 'Merged contributions and open proposals shown separately. Each item is also linked in ordinary Markdown. The two mwsoli/OpenROAD proposals target a maintainer fork.', p)
    s.text(24, 34, 'OPEN-SOURCE EVIDENCE', 19, p['accent'], font_weight=700, letter_spacing=1)
    s.text(24, 60, 'Merge dates for merged PRs; opening dates otherwise', 14, p['muted'])
    s.line(32, 94, 32, height - 62)
    for i, m in enumerate(data['milestones']):
        y = 96 + i * 94
        color = p['green'] if m['status'] == 'merged' else p['amber']
        s.items.append(f'<circle cx="32" cy="{y}" r="5" fill="{color}"/>')
        s.text(50, y + 5, f'{m["date"]} · {m["status"].upper()}', 14, color, font_weight=700)
        s.text(50, y + 30, f'{m["repo"]} #{m["number"]}', 15)
        s.text(50, y + 53, m['label'], 14, p['muted'])
    footer(s, data, height - 12, 14)
    return s.finish()


def summary(data):
    lines = ['# Activity data in text', '', f'Period: **{data["start"]}–{data["end"]} UTC**. Last successful data coverage: **{data["end"]}**.', '',
             f'GitHub-visible calendar: **{data["calendar_total"]:,} contributions**. This includes eligible contribution types and may include anonymous private aggregates; it is not a commit count.', '',
             '[Definitions and visibility limits](../../docs/ACTIVITY_DATA.md) · [Machine-readable daily data](activity.json)', '',
             '| Metric | Count |', '|---|---:|']
    for key, value in data['stats'].items():
        lines.append(f'| {key.replace("_", " ")} | {value:,} |')
    lines += ['', '## Monthly activity', '', '| UTC window | Eligible commits | PR contributions | Issues | PR reviews |', '|---|---:|---:|---:|---:|']
    for m in data['monthly']:
        lines.append(f'| {m["start"]}–{m["end"]} | {m["commits"]} | {m["prs"]} | {m["issues"]} | {m["reviews"]} |')
    lines += ['', '## Upstream evidence', '']
    for m in data['milestones']:
        lines.append(f'- **{m["status"].upper()}** · {m["date"]} · [{m["repo"]} #{m["number"]}]({m["url"]}) — {m["label"]}.')
    return '\n'.join(lines) + '\n'


def generate(data, output):
    validate(data)
    output.mkdir(parents=True, exist_ok=True)
    files = {'SUMMARY.md': summary(data)}
    for theme, palette in PALETTES.items():
        files[f'calendar-{theme}.svg'] = calendar(data, palette)
        files[f'calendar-mobile-{theme}.svg'] = calendar(data, palette, mobile=True)
        files[f'trend-{theme}.svg'] = trend(data, palette)
        files[f'stats-{theme}.svg'] = stats(data, palette)
        files[f'timeline-{theme}.svg'] = timeline(data, palette)
    for name, content in files.items():
        (output / name).write_text(content, encoding='utf-8', newline='\n')
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'assets/activity/activity.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/activity')
    args = parser.parse_args()
    rendered = generate(json.loads(args.input.read_text(encoding='utf-8')), args.output)
    print(f'Generated {len(rendered)} deterministic assets from validated GitHub data.')
