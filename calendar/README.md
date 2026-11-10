# UoM English iPhone Calendar

This folder contains an English formatting proxy for the personal University of Manchester Scientia timetable. The scheduled GitHub Actions workflow fetches the **current** official calendar, retains the source event UIDs and time values, reformats display text, then deploys an `.ics` subscription feed to GitHub Pages.

## One-time activation (repository owner)

1. Open [Actions Secrets](https://github.com/OnlyOswaldWang/UoM-Robot/settings/secrets/actions) → **New repository secret**. Name: `UPSTREAM_ICS_URL`. Value: your full personal Scientia URL. Keep it secret because it grants access to your timetable.
2. Open [Pages settings](https://github.com/OnlyOswaldWang/UoM-Robot/settings/pages) and choose **GitHub Actions** as the build/deploy source.
3. Open [Publish UoM English timetable](https://github.com/OnlyOswaldWang/UoM-Robot/actions/workflows/uom-calendar.yml), click **Run workflow**, then verify successful completion.
4. Subscribe on iPhone to: `https://onlyoswaldwang.github.io/UoM-Robot/timetable.ics`. This URL becomes valid **only after the Pages deployment succeeds**. Hide the original university subscription to avoid duplicate events.

## Sync and privacy

Automatic builds are scheduled hourly at minute 17 UTC and can be delayed by GitHub. iPhone subscribed calendar refresh is also controlled by the phone. This is **eventually updated**, not instant synchronization. University emails and the official timetable remain authoritative for last-minute changes.

GitHub Pages from this public repository creates a **publicly readable calendar feed**. Do not use it if you need classmates or strangers with the URL to be unable to view your class schedule. Do not publish the upstream URL or contents of the downloaded personal `.ics` file in this repository.

You can change `UPSTREAM_ICS_URL` later without changing the iPhone subscription address. The official event `UID`, `DTSTART`, `DTEND`, `LAST-MODIFIED`, and `SEQUENCE` are preserved.

## Local run
Set environment variable `UPSTREAM_ICS_URL`, then run `python3 calendar/format_calendar.py`.
