# Maintenance

Python 3.12 and its standard library are sufficient. No package installation, paid service or personal token is needed in CI.

## Update content

Start a feature branch and verify metrics at committed source revisions. Distinguish logic, routed timing/DRC/LVS and silicon measurements. Edit the concise README entry and direct evidence links. Publication status requires independent evidence. Check `merged_at` before describing any PR as merged. The selected milestone list lives in `scripts/fetch_activity.py`. Run the offline checks, inspect the branch README on GitHub and open a PR.

```bash
python scripts/validate_profile.py
python -m unittest discover -s tests -v
```

## Refresh data

After merge, **Actions → Refresh activity → Run workflow → main** fetches real data and publishes changed, validated files under `assets/activity/`. Scheduling runs approximately daily at 03:23 UTC / 08:53 IST, subject to GitHub delays. Scheduled workflows run only from the default branch.

The feature branch is temporarily included in push triggers to test live generation before merge. Remove `codex/profile-activity-redesign` from both workflows' branch lists in a later maintenance edit. It has no effect after that branch is retired.

Locally, supply a token scoped to this public repository through `GH_TOKEN` or `GITHUB_TOKEN` without putting it in files or command history:

```bash
python scripts/fetch_activity.py
python scripts/generate_activity_svg.py
python scripts/validate_profile.py
```

Do not substitute a broader personal token; see [visibility limits](ACTIVITY_DATA.md). For offline rendering use only the last two commands. The committed snapshot is reused as the data cache. The renderer makes no API calls and produces byte-identical output. The publisher uses a normal fast-forward bot commit after `git diff --cached --quiet`; unchanged output produces no commit.

## Failed refreshes

Inspect the failing Actions step. HTTP 403/429 can indicate rate limiting/token policy; network/5xx errors retry four times. Diagnose schema or data mismatches before publishing. A non-fast-forward push means concurrent branch changes; rerun against the latest branch. Branch protection may prevent bot pushes; retain the valid assets and adopt an output branch or reviewed asset PRs if needed. Do not weaken protection for a graph update.

Fetch, render, validation and behavior tests must succeed before publication. Failed refreshes leave the last committed graphics available, with visible coverage dates. GitHub may disable schedules after extended repository inactivity; re-enable them in Actions when needed. Periodically check freshness and token-free diagnostics.

Update action pins after verifying the official release and full SHA. Validation is read-only; only the trusted publisher needs content writes. Do not add PR triggers to publishing or use `pull_request_target`.

Use an actual GitHub-associated author address for future work. Automation uses `github-actions[bot]`, so its asset commits are not attributed to you. Diagnose missing commits with GitHub's eligibility rules. No history rewriting, empty commits, backdating or calendar filling is part of this system.
