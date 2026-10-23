# Activity data and integrity

## Sources and periods

The Python standard-library collector reads GitHub's authenticated GraphQL `user.contributionsCollection` and public REST repository/PR endpoints. The interval is the **365 completed UTC days ending yesterday**. A successful refresh can therefore be almost two days behind a reader's local date. GitHub may also take time to index eligible activity. Each graphic prints the coverage end date; it is a data date, not a claim of instantaneous freshness.

The collector obtains daily `contributionCount` and GitHub's `contributionLevel` without rescaling or inventing intensities. Missing, duplicate, negative or inconsistent records fail validation. Calendar totals include different eligible event types; **contributions are not synonymous with commits**. The source snapshot is [activity.json](../assets/activity/activity.json); the [text summary and monthly table](../assets/activity/SUMMARY.md) provide a selectable alternative.

## What the numbers mean

| Display | Definition |
|---|---|
| Contribution calendar | GitHub-visible calendar counts, dates and intensity levels for the requested interval |
| Commit line | `totalCommitContributions` in each UTC monthly window; GitHub-eligible/API-visible contributions, not every commit on every branch |
| PR / issue / review lines | `totalPullRequestContributions`, `totalIssueContributions`, `totalPullRequestReviewContributions` in those windows; reviews mean submitted PR reviews, not discussion comments |
| Public repositories | Paginated public repositories owned by the account, including forks; inventory at refresh time |
| Stars | Sum of current stars on owned public **non-fork** repositories |
| Public PRs opened | Public search `author:wellitsabhinav is:pr is:public created:START..END` |
| Public authored PRs merged | Public search `author:wellitsabhinav is:pr is:public is:merged merged:START..END`; based on merge date, not opening date |
| External PRs opened | Opened query plus `-user:wellitsabhinav`; includes PRs to third-party forks, not necessarily canonical upstream merges |
| Contribution milestones | Selected REST PR records, author checked; `merged_at` determines MERGED. Closed without merge stays CLOSED. Open proposals are not accepted contributions. |

The first and last calendar months can be partial. Four independent linear panels avoid hiding small PR/issue/review counts under the commit scale. Half-step tick labels may be fractional scale markers; individual event counts remain integers. These API summaries do not sum to the calendar in every case: GitHub also counts repository creation and may include restricted aggregates. No missing type is inferred by subtraction.

## Token visibility and privacy

The workflow uses only the automatically issued repository-scoped `GITHUB_TOKEN`, with `contents: write` for the asset publisher and `contents: read` for validation. No personal token is required. Public search queries explicitly require `is:public`, and repository inventory discards private entries. The calendar can contain anonymous restricted/private aggregates if the account has enabled them; no private repository names, commits or activity details are collected or published, and the calendar is never labeled a complete public commit count. Completeness outside the token's visibility is not asserted.

Do not substitute a broadly privileged personal token: visibility-sensitive aggregate counts could change. A token with only this public profile repository is the intended environment. All live contribution queries must succeed before a replacement snapshot is written. Four bounded retry attempts cover transient network failures, rate limiting and server errors. An API/schema error fails closed; previous committed assets remain served.

## Refresh and integrity

Schedule: approximately daily at **03:23 UTC / 08:53 IST**, plus manual dispatch. Source and workflows live under `scripts/` and `.github/`; generated JSON, Markdown and SVGs live under `assets/activity/`. The committed snapshot is reused for offline rendering and validation. There are no dependencies to cache or external image-widget services. Roughly a dozen API calls per day is small enough that a separate HTTP cache would add more invalidation risk than value.

The output is deterministic: no random IDs, network requests in the renderer, or current-clock timestamps. The publisher compares Git bytes and skips unchanged output. The advancing date window and genuine changed API facts can produce a bot commit. The bot's identity is used; no activity is attributed to Abhinav. Commits refresh evidence and are never created to fill contribution squares. No history is rewritten or backdated.

The first implementation deliberately keeps source and assets in one small repository. This makes branch previews and relative image links reliable. A separate output branch would require cross-branch image URLs and bootstrap coordination. If history growth later matters, move only the generated assets; retain a last valid static fallback and the same integrity checks.

## Official references

- [GitHub contribution types and GraphQL schema](https://docs.github.com/en/graphql/reference/users#contributionscollection)
- [Troubleshooting missing contributions](https://docs.github.com/en/account-and-profile/how-tos/contribution-settings/troubleshooting-missing-contributions)
- [Using the repository GITHUB_TOKEN](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)

Commits generally need an associated author email and an eligible repository/default or `gh-pages` branch; fork-only work and non-default feature-branch commits have different eligibility. A public commit's linked GitHub author is evidence of attribution for that commit, not proof that every historical email is associated. Diagnose specific missing contributions; add a legitimate email association in account settings where appropriate, and merge useful work through normal review. Do not rewrite history to alter the calendar.
