---
name: seek
description: Search Pocket conversations for a date range or topic and organize them into an Excel workbook with topic, date, tags, a two-sentence summary, action items and owners. Use when the user says "seek", "run Seek", or asks to collect, list, or table their meetings or recordings. Its JSON output feeds the follow-up and weekly-summary prompts.
---

# Seek

Seek turns Pocket recordings into an Excel table you can filter and share. It also saves
a JSON file that the follow-up and weekly-summary prompts read, so those prompts don't
have to search Pocket again.

## Inputs

Parse these from the request. If one is missing, use the default; don't ask.

| Input | Default | Examples |
|---|---|---|
| Date range | Last 7 days, ending today | "this week", "since Monday", "Sept" |
| Topic filter | None (all recordings) | "FTP", "anything with Connor" |
| Scope | All (Work, Personal, Mixed) | "work only", "personal only" |
| Time zone | America/Detroit (Eastern) | — |

## Steps

### 1. List the recordings

- With **no topic**, call `search_pocket_conversations` without `query`, using
  `recordingDateAfter` / `recordingDateBefore`. Keep calling with `cursor = data.meta.nextCursor`
  until `hasMore` is false.
- With **a topic**, call it with `query` set to the topic and the same dates. Query mode
  returns at most 8 hits, so also run one recency pass and keep the recordings whose title
  or summary matches the topic.
- Pages include full transcripts and are often too large to read inline. When a result is
  saved to a file, pull out only the metadata with `jq`:
  `.data.recordings[] | [.recordingId, .recordingDate, .recordingTitle, (.content|length)]`.
- **Skip**, and list under "Skipped" in the output:
  - recordings with `transcriptAvailable: false`;
  - content that is only `[background noise]` or similar, or that is under about 100
    characters with no actionable content;
  - Pocket's "Getting Started with Pocket" guide.

### 2. Get summaries and tags

Call `get_pocket_conversation` with the kept IDs (batching all of them in one call is fine).
Use `jq` to keep only `recordingId`, `recordingTitle`, `recordingTags` and `summary.markdown`,
and drop `transcriptSegments` and `audioUrl`. Strip `<pocket:...>` blocks from the summary.
Use the date from step 1, not from this call, because the dates can differ.

Read a transcript only when the summary doesn't say who owns an action item.

### 3. Get action items

Call `search_pocket_actionitems` with `recordingDateFrom` / `recordingDateTo` set to the range.
**The tool returns at most 50 items.** If a call returns exactly 50, split the range in half
and query each half, repeating until every call returns fewer than 50. Remove duplicates by
`actionItemId`, and keep only items whose `recordingId` is among the kept recordings.

Then read each summary's "Action Items", "Next Steps" and "Operational Directives" sections.
Add any concrete task there that has no matching Pocket item, with `source: "Summary"`.
Don't add open questions or observations.

### 4. Build each row

**Topic**: 3–7 words naming the subject, not the meeting type. For example, use
"Verbent loan migration – account mapping", not "Loan Mapping and Reconciliation Discussion".

**Category**: `Work`, `Personal`, or `Mixed` (substantial content of both kinds).

**Tags**: if Pocket `recordingTags` exist, use them. Otherwise assign 1–3 tags from this
list, so the weekly summary can group rows the same way every week. Add a new tag only
when none fits:
- Work: `FTP`, `ALM/ALCO`, `ALMC`, `DPC`, `GL Recon`, `Loan Data`, `QRM/Data Quality`,
  `Forecasting`, `Collateral`, `Derivatives`, `1:1`, `Daily Plan`, `Governance`
- Personal: `Family`, `Health`, `Home Finance`, `Real Estate`, `Citizenship/Admin`,
  `Social`, `Career Reflection`, `Tech/AI`

**Summary / Takeaways**: exactly two sentences. Sentence 1 states what was decided or
learned. Sentence 2 states the open issue, risk or next step. Include numbers and names
when the source has them. Write plainly, with no filler.

**Action items**: write each as a short task in the imperative ("Send…", "Confirm…").
Then set the owner:

| Pocket `assignee` | Owner | `owner_basis` |
|---|---|---|
| `"me"` | Sergio | `Pocket` |
| a name | that name | `Pocket` |
| `null` or `"Other"`, and the context, label or message names one person who will do it | that name | `Inferred: <why>` |
| `null` in a solo voice memo the user dictated | Sergio | `Inferred: self-dictated` |
| anything else | **`No clear owner`** | `None: <what's missing>` |

Never guess an owner. If two people are possible, or the speaker is unnamed ("her mom",
"Speaker 0"), write `No clear owner` and explain why in `owner_basis`.

Also carry over `due` (date only, local), `priority`, `status`, `type` (`create_reminder`,
`draft_email`, `send_message`), `source` (`Pocket` or `Summary`) and `action_item_id`.

**Name conflicts**: if the recording title and the action items name the same person
differently (for example "Dan" and "Ben"), keep both in the text, like
"Dan (Pocket heard 'Ben')", and add a line to `notes`.

### 5. Write the JSON

Save to `seek-output/seek_<from>_<to>.json`, creating the folder if needed:

```json
{
  "range": {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD", "tz": "America/Detroit"},
  "generated": "YYYY-MM-DDTHH:MM",
  "filters": {"topic": null, "scope": "all"},
  "meetings": [
    {
      "recording_id": "…", "date": "YYYY-MM-DD", "time": "HH:MM",
      "title": "Pocket title", "topic": "…", "category": "Work|Personal|Mixed",
      "tags": ["…"], "summary": "Sentence one. Sentence two.",
      "action_items": [
        {"action": "…", "owner": "…", "owner_basis": "…", "due": "YYYY-MM-DD|null",
         "priority": "high|medium|low", "status": "TODO", "type": "create_reminder",
         "source": "Pocket|Summary", "action_item_id": "…|null"}
      ]
    }
  ],
  "skipped": [{"recording_id": "…", "title": "…", "reason": "…"}],
  "notes": ["…"]
}
```

Sort `meetings` newest first. This file is how the other prompts get their input:
- **Follow-up** reads one meeting (by `recording_id` or topic) for its summary, action
  items and owners.
- **Weekly summary** reads every `Work` and `Mixed` meeting and groups them by `tags`.

### 6. Build the Excel file

```bash
python3 .claude/skills/seek/build_xlsx.py seek-output/seek_<from>_<to>.json
```

The script writes `seek-output/seek_<from>_<to>.xlsx` with three sheets:
- **Meetings**: one row per recording.
- **Action Items**: one row per item, with "No clear owner" highlighted.
- **About**: the range, counts, skipped recordings and notes.

### 7. Report back

Keep it short:
- the counts: recordings found, kept, skipped, and action items;
- how many items have **No clear owner**, listed by topic;
- any name conflicts or data problems;
- the path to the `.xlsx` (send it with SendUserFile when available).

Don't paste the whole table into chat.

## Privacy

`seek-output/` is git-ignored. Never commit it, and never copy email addresses or phone
numbers from Pocket payloads into the output.
