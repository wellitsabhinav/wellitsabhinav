"""Offline integrity checks for Markdown, SVGs, and reproducible generated assets."""
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from fetch_activity import ROOT, validate
from generate_activity_svg import generate


def check():
    problems = []
    checked_links = 0
    for path in list(ROOT.rglob('*.md')):
        if '.git' in path.parts:
            continue
        text = path.read_text(encoding='utf-8')
        targets = re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text)
        targets += re.findall(r'(?:src|srcset|href)="([^"]+)"', text)
        for target in targets:
            parts = urlsplit(target)
            if parts.scheme or not parts.path:
                continue
            checked_links += 1
            resolved = (path.parent / unquote(parts.path)).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                problems.append(f'{path.relative_to(ROOT)}: missing/unsafe local link {target}')
        if path.name == 'README.md' and path.parent == ROOT:
            if not re.search(r'^# Abhinav Choudhary', text, re.M):
                # The pre-redesign baseline is allowed only during the initial workflow bootstrap.
                if (ROOT / 'docs/DESIGN.md').exists():
                    problems.append('README: missing selectable identity heading')
            for image in re.findall(r'<img\b[^>]*>', text):
                if not re.search(r'alt="[^"]+"', image):
                    problems.append('README: image has no useful alt text')
    svgs = list((ROOT / 'assets').rglob('*.svg'))
    for path in svgs:
        tree = ET.parse(path)
        svg = tree.getroot()
        if 'viewBox' not in svg.attrib:
            problems.append(f'{path.name}: missing responsive viewBox')
        ns = {'s': 'http://www.w3.org/2000/svg'}
        # The licensed MOTIF waveform is preserved byte-for-byte; the README supplies its alt text.
        if path.name == 'motif-lin-interruption.svg' and hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '5f060759fb5ca73b59eba163e6abbc5cc856b90525a3ceba97cccbbd6bce4bd3':
            problems.append('Licensed MOTIF waveform changed; verify attribution and provenance')
        if path.name != 'motif-lin-interruption.svg' and (not svg.findtext('s:title', namespaces=ns) or not svg.findtext('s:desc', namespaces=ns)):
            problems.append(f'{path.name}: missing accessible title/description')
        for node in svg.iter():
            if node.tag.split('}')[-1] in ('script', 'foreignObject', 'animate', 'animateTransform'):
                problems.append(f'{path.name}: unsupported active/animated SVG element')
            if any(k.lower().startswith('on') for k in node.attrib):
                problems.append(f'{path.name}: event handler')
    snapshot = ROOT / 'assets/activity/activity.json'
    if snapshot.exists():
        data = json.loads(snapshot.read_text(encoding='utf-8'))
        validate(data)
        with tempfile.TemporaryDirectory() as temporary:
            for name, content in generate(data, Path(temporary)).items():
                actual = snapshot.parent / name
                if not actual.exists() or actual.read_bytes() != content.encode():
                    problems.append(f'{name}: stale or nondeterministic output')
        for theme in ('dark', 'light'):
            for variant in ('calendar', 'calendar-mobile'):
                tree = ET.parse(snapshot.parent / f'{variant}-{theme}.svg')
                days = [e for e in tree.iter() if 'data-date' in e.attrib]
                observed = [(d.attrib['data-date'], int(d.attrib['data-count']), int(d.attrib['data-level'])) for d in days]
                expected = [(d['date'], d['count'], d['level']) for d in data['days']]
                if observed != expected:
                    problems.append(f'{variant}-{theme}: calendar disagrees with API snapshot')
    for workflow in (ROOT / '.github/workflows').glob('*.yml'):
        text = workflow.read_text(encoding='utf-8')
        if re.search(r'uses:\s+[^\s]+@(?![0-9a-f]{40}(?:\s|$))', text):
            problems.append(f'{workflow.name}: action is not pinned to an immutable SHA')
        if 'pull_request_target' in text:
            problems.append(f'{workflow.name}: unsafe privileged PR trigger')
    if problems:
        raise RuntimeError('\n'.join(problems))
    print(f'PASS: {checked_links} local links, {len(svgs)} accessible SVGs, immutable action pins, snapshot/calendar agreement and deterministic regeneration.')


if __name__ == '__main__':
    try:
        check()
    except (RuntimeError, AssertionError, ET.ParseError, KeyError, ValueError) as exc:
        print(f'Profile validation failed: {exc}', file=sys.stderr)
        sys.exit(1)
