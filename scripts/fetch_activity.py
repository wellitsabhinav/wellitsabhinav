"""Fetch a public profile snapshot with GitHub's GraphQL and REST APIs (stdlib only)."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MILESTONES = [
    ('parallaxsw/OpenSTA', 538, 'Reject unsupported wired nets'),
    ('The-OpenROAD-Project/OpenSTA', 420, 'Preserve Verilog input aliases'),
    ('parallaxsw/OpenSTA', 540, 'Upstream alias serialization repair'),
    ('The-OpenROAD-Project/OpenROAD', 11624, 'Preserve local port connectivity'),
    ('NTU-LaDS-II/FAN_ATPG', 4, 'Fault reporting and scan identities'),
    ('mwsoli/OpenROAD', 1, 'DFT scan-pin receiver fix (fork target)'),
    ('mwsoli/OpenROAD', 2, 'DFT endpoint and metadata fix (fork target)'),
]


def request(url, token, body=None):
    """Bound retries; never report headers, tokens, or response bodies on failure."""
    payload = None if body is None else json.dumps(body).encode()
    for attempt in range(4):
        req = urllib.request.Request(url, data=payload, headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
            'User-Agent': 'wellitsabhinav-profile-activity',
            'X-GitHub-Api-Version': '2022-11-28',
        })
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.load(response)
            if isinstance(result, dict) and result.get('errors'):
                raise RuntimeError('GraphQL returned errors; snapshot not published. Check token visibility and query schema.')
            return result
        except urllib.error.HTTPError as exc:
            if exc.code not in (403, 429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f'GitHub API HTTP {exc.code}; previous assets retained. Check permissions/rate limits.') from None
            delay = min(60, max(2 ** attempt, int(exc.headers.get('Retry-After', '0'))))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise RuntimeError('GitHub API connection failed after four attempts; previous assets retained.') from None
            delay = 2 ** attempt
        time.sleep(delay)


def graphql(query, variables, token):
    return request('https://api.github.com/graphql', token, {'query': query, 'variables': variables})['data']


def periods(start, end):
    cursor = start
    while cursor <= end:
        following = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield cursor, min(end, following - timedelta(days=1))
        cursor = following


def stamp(day, last=False):
    return day.isoformat() + ('T23:59:59Z' if last else 'T00:00:00Z')


def fetch(login, end, token):
    start = end - timedelta(days=364)
    fields = 'totalCommitContributions totalPullRequestContributions totalIssueContributions totalPullRequestReviewContributions'
    aliases = []
    windows = list(periods(start, end))
    for i, (a, b) in enumerate(windows):
        aliases.append(f'm{i}: contributionsCollection(from:"{stamp(a)}",to:"{stamp(b, True)}") {{ {fields} }}')
    query = '''query($login:String!,$from:DateTime!,$to:DateTime!) {
      user(login:$login) {
        login
        contributionsCollection(from:$from,to:$to) {
          totalCommitContributions totalPullRequestContributions
          totalIssueContributions totalPullRequestReviewContributions
          restrictedContributionsCount hasAnyRestrictedContributions
          contributionCalendar { totalContributions weeks { contributionDays {
            date contributionCount contributionLevel
          } } }
        }
        MONTHS
      }
      rateLimit { remaining }
    }'''.replace('MONTHS', '\n'.join(aliases))
    data = graphql(query, {'login': login, 'from': stamp(start), 'to': stamp(end, True)}, token)
    user = data['user']
    if not user:
        raise RuntimeError('Target GitHub account was not found.')
    collection = user['contributionsCollection']
    levels = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2, 'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
    days = sorted([{'date': d['date'], 'count': d['contributionCount'], 'level': levels[d['contributionLevel']]}
                   for week in collection['contributionCalendar']['weeks'] for d in week['contributionDays']
                   if start.isoformat() <= d['date'] <= end.isoformat()], key=lambda d: d['date'])
    monthly = []
    for i, (a, b) in enumerate(windows):
        c = user[f'm{i}']
        monthly.append({'start': a.isoformat(), 'end': b.isoformat(), 'commits': c['totalCommitContributions'],
                        'prs': c['totalPullRequestContributions'], 'issues': c['totalIssueContributions'],
                        'reviews': c['totalPullRequestReviewContributions']})
    repos = []
    for page in range(1, 101):
        batch = request(f'https://api.github.com/users/{login}/repos?type=owner&per_page=100&page={page}', token)
        repos.extend(r for r in batch if not r['private'])
        if len(batch) < 100:
            break
    else:
        raise RuntimeError('Repository pagination limit exceeded; refusing a partial snapshot.')
    # is:public prevents a future broader personal token from leaking private search counts.
    queries = {
        'prs_opened': f'author:{login} is:pr is:public created:{start}..{end}',
        'prs_merged': f'author:{login} is:pr is:public is:merged merged:{start}..{end}',
        'external_prs_opened': f'author:{login} is:pr is:public -user:{login} created:{start}..{end}',
    }
    counts = {}
    for key, q in queries.items():
        counts[key] = graphql('query($q:String!){search(query:$q,type:ISSUE,first:1){issueCount}}', {'q': q}, token)['search']['issueCount']
    milestones = []
    for repo, number, label in MILESTONES:
        pr = request(f'https://api.github.com/repos/{repo}/pulls/{number}', token)
        if pr['user']['login'].lower() != login.lower():
            raise RuntimeError(f'Unexpected PR author for {repo}#{number}.')
        milestones.append({'repo': repo, 'number': number, 'label': label, 'url': pr['html_url'],
                           'status': 'merged' if pr['merged_at'] else pr['state'],
                           'date': (pr['merged_at'] or pr['created_at'])[:10]})
    return {
        'schema_version': 1, 'login': login, 'start': start.isoformat(), 'end': end.isoformat(),
        'source': 'GitHub GraphQL contributionsCollection + public REST repositories/PRs + public GraphQL search',
        'scope': 'API-visible contribution counts; calendar may include anonymous restricted aggregates. No private repository details.',
        'restricted_count': collection['restrictedContributionsCount'],
        'calendar_total': collection['contributionCalendar']['totalContributions'], 'days': days, 'monthly': monthly,
        'stats': {'public_repositories': len(repos), 'original_repository_stars': sum(r['stargazers_count'] for r in repos if not r['fork']),
                  'visible_commit_contributions': collection['totalCommitContributions'], **counts},
        'milestones': sorted(milestones, key=lambda m: (m['status'] != 'merged', m['date'], m['repo'], m['number'])),
    }


def validate(data):
    assert data['schema_version'] == 1, 'Unsupported activity snapshot schema'
    start, end = date.fromisoformat(data['start']), date.fromisoformat(data['end'])
    assert (end - start).days == 364, 'Expected exactly 365 completed UTC days'
    expected = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    assert [d['date'] for d in data['days']] == expected, 'Missing, duplicate, or unordered contribution dates'
    assert all(type(d['count']) is int and d['count'] >= 0 and d['level'] in range(5) for d in data['days'])
    assert all((d['count'] == 0) == (d['level'] == 0) for d in data['days']), 'Count/intensity inconsistency'
    assert sum(d['count'] for d in data['days']) == data['calendar_total'], 'Calendar total mismatch'
    assert all(type(v) is int and v >= 0 for v in data['stats'].values())
    assert data['monthly'][0]['start'] == data['start'] and data['monthly'][-1]['end'] == data['end']
    cursor = start
    for m in data['monthly']:
        assert m['start'] == cursor.isoformat(), 'Noncontiguous monthly windows'
        assert all(type(m[k]) is int and m[k] >= 0 for k in ('commits', 'prs', 'issues', 'reviews'))
        cursor = date.fromisoformat(m['end']) + timedelta(days=1)
    assert sum(m['commits'] for m in data['monthly']) == data['stats']['visible_commit_contributions']
    for milestone in data['milestones']:
        assert milestone['status'] in ('open', 'closed', 'merged')
        assert milestone['url'] == f"https://github.com/{milestone['repo']}/pull/{milestone['number']}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--login', default='wellitsabhinav')
    parser.add_argument('--end', type=date.fromisoformat, default=datetime.now(timezone.utc).date() - timedelta(days=1))
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/activity/activity.json')
    args = parser.parse_args()
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('Set GH_TOKEN or GITHUB_TOKEN. No synthetic or stale-data fallback is published.')
    snapshot = fetch(args.login, args.end, token)
    validate(snapshot)
    serialized = json.dumps(snapshot, indent=2, ensure_ascii=False) + '\n'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Only replace a complete, validated snapshot. No wall-clock timestamp churn.
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(serialized, encoding='utf-8', newline='\n')
    temporary.replace(args.output)
    print(f'Validated {len(snapshot["days"])} calendar days through {snapshot["end"]}; no credentials stored.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, AssertionError, KeyError, ValueError) as exc:
        print(f'Activity refresh failed: {exc}', file=sys.stderr)
        sys.exit(1)
