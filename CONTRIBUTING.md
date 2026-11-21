# Contributing

Thanks for helping out! The README is generated from `data/2026.yaml`, so adding a deal means adding a few lines there. Please don't edit `README.md` directly, because your changes would be overwritten.

No URL shorteners, affiliate links, or marketplaces. 

Inclusion is at the maintainer’s discretion. VPNs, lifetime deals, and anything scammy won’t be merged.

## Adding a deal

There are two ways to add a deal.

**The deal form (recommended).** [Open the deal form](https://github.com/ps-lo/InfoSec-and-Tech-Black-Friday/issues/new?template=deal.yml), fill in the fields, and submit. No YAML, no fork. Here's what happens next:

1. I check the deal against the vendor's own page.
2. If it checks out, I approve it, and a bot turns it into a pull request and validates it.
3. I review that pull request and merge it. The deal shows up on the list within a few minutes.

If the automatic check finds a problem, the bot comments on your issue with what to fix.

**A pull request.** If you prefer editing the data directly, add your deal to `data/<year>.yaml` using the format below and open a PR. The build validates it and tells you what to fix. Don't edit `README.md`; it's generated, and PRs that touch it will be closed.

Either way, the same rules apply:

- Link to the vendor's own deal or product page. No Amazon, open marketplaces, link shorteners, affiliate links, tracking parameters or direct payment site links.
- The deal must be public and live, or have an announced start date.
- Every deal needs an end date as published by the vendor. Year-round programs are added by hand, so open a regular discussion or mention it in your submission's notes.
- Submitting your own product is fine. Say so in the form, or mention it in your PR description.
- Use spaces in YAML, not tabs.

## Fields

| Field | Required | What it is |
|---|---|---|
| `vendor` | yes | Company or product name |
| `url` | yes | Plain link to the deal page. No affiliate, referral, or tracking parameters, and no Amazon links |
| `deal` | yes | Short description, e.g. `40% off all courses` |
| `code` | no | Discount code in quotes. For more than one: `["CODE1", "CODE2"]` |
| `starts` | no | Start date if it hasn't started yet, `YYYY-MM-DD` |
| `ends` | no | End date, `YYYY-MM-DD`. Please include it when the vendor lists one |
| `ends_note` | no | Extra timing detail, e.g. `midnight PST` |
| `evergreen` | no | Added for cases like Antisyphon Training |
| `focus` | no | `Red`, `Blue`, `Red / Blue`, `Dev`, `Cloud`, `Networking`, `General`, etc. |
| `notes` | no | Anything else worth knowing. Markdown links are fine |
| `via` | no | Your GitHub username, e.g. `"@octocat"`. Shows as *via @octocat* next to the deal so you get credit and adds you to the credits list |

`taken` (💖) and `used` (✨) are the maintainer's personal picks, so please leave them off.

## YAML gotchas

- **Always quote codes.** YAML silently turns `NO`, `YES`, and `ON` into true/false, and `0042` into `42`. The check will catch it, but quoting avoids it.
- **Indent with spaces, not tabs**, and line up with the entries around yours.
- **Quote text that contains `: `** (colon followed by a space), e.g. `vendor: "Book: Second Edition"`.

## Previewing locally (optional)

```sh
pip install -r requirements.txt
python scripts/generate.py --validate            # check for problems
python scripts/generate.py                       # rebuild README.md and archive/
python scripts/generate.py --today 2026-12-02    # preview what expires by a given date
```

## Starting a new year (maintainer)

Copy `data/2026.yaml` to `data/2027.yaml`, update `meta.year`, `meta.title`, and `meta.intro`, and empty each section's `deals:` back to `[]`. The newest year becomes the README automatically, and older years move to `archive/`.
