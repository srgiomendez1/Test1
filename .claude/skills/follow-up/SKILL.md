---
name: follow-up
description: Draft a follow-up email for a meeting or presentation recorded in Pocket, as a Gmail draft addressed to Sergio's Outlook so he can forward it. Use when the user says "follow-up", "follow up on", "recap email", or "send notes from" a meeting or presentation.
---

# Follow-up

Turns one Pocket recording into a ready-to-forward recap email. The output is a **Gmail
draft**. Never send it.

## Fixed settings

- **To:** `sergio.mendezlarregui@flagstar.com`, and only that address. No CC or BCC. Sergio
  forwards it from Outlook.
- **Signature:** "Best,\nSergio"
- **Time zone:** America/Detroit

## Inputs

| Input | Default |
|---|---|
| Which recording | Required: a title, topic, date, recording ID, or "last meeting" |
| Type | Detect it: **Meeting** (discussion, decisions, tasks) or **Presentation** (Sergio presented to a group) |
| Audience | The participants named in the recording |

If more than one recording matches, list the matches (date, time, title) and ask which one.
Don't ask about anything else.

## Steps

1. **Find the recording.** Look in the newest `seek-output/seek_*.json` for a matching
   meeting. If none matches, follow Seek's steps 1–4 for just this recording, with scope
   `work` and no scope question.
2. **Get the detail.** Call `get_pocket_conversation` for the recording and keep only
   `summary.markdown`, using `jq` if the result is saved to a file. Use it for decisions,
   numbers and context that the two-sentence Seek summary leaves out. Read the transcript
   only to settle who owns an item or to confirm a figure.
3. **Remove personal content.** In a Mixed recording, use only the work part. Never include
   family, health or personal-finance details, email addresses or phone numbers from the
   transcript.
4. **Write the email** using the template below.
5. **Create the draft** with `create_draft`. Fill in both `htmlBody` and a plain-text `body`.
6. **Report back** in a couple of lines: the subject, the draft's `viewUrl`, the suggested
   recipients, and any items with **No clear owner**.

## Template: Meeting

Subject: `Follow-up: <Topic> – <Mon D>`

```
[Forward to: <participant names> — delete this line before sending]

Hi all,

Thanks for the time today. Recap of <topic> below.

Key takeaways
• <3–5 bullets: what was learned or agreed, with numbers>

Decisions
• <only decisions actually made; leave this section out if there were none>

Action items
<table: Action | Owner | Due>

Open questions
• <unresolved items; leave this section out if there are none>

Next step: <one line: next checkpoint or meeting, if known>

Best,
Sergio
```

## Template: Presentation

Subject: `Recap: <Presentation title> – <Mon D>`

```
[Forward to: <audience> — delete this line before sending]

Hi all,

Thank you for joining <presentation>. Summary of what we covered and what comes next.

What we covered
• <3–5 bullets: the main points presented>

Questions raised
• <question> — <answer given, or "to follow up">

Action items
<table: Action | Owner | Due>

Materials: [attach or link deck]

Happy to walk through any of it in more detail.

Best,
Sergio
```

## Writing rules

- Keep it concise and direct, and make it scannable in 30 seconds.
- Don't open with "I hope this finds you well" or similar filler.
- Use the meeting's own terms (FTP, ALMC, DPC, QRM, NII/EVE, bp). Don't explain them.
- Include numbers exactly as the source states them. If a figure is approximate, say "~".
- **Owners:** use Seek's owner rules. If an item has no clear owner, write
  **"No clear owner — can someone take this?"** in the Owner cell. Never invent an owner.
- **Due dates:** use the Pocket date if there is one. Otherwise use what was said
  ("before next DPC"), or "—" if nothing was said.
- **Names:** if a name is uncertain (for example "Dan / Ben"), use the name in the meeting
  title. Mention the uncertainty to Sergio in chat, not in the email.

## HTML formatting

Use simple inline-styled HTML that renders the same in Gmail and Outlook:
- `font-family: Calibri, Arial, sans-serif; font-size: 11pt` on a wrapping `<div>`;
- `<b>` section headers;
- `<ul>` for bullets;
- for action items, a `<table>` with `border-collapse:collapse`, 1px `#ccc` borders, `6px`
  cell padding, and a `#1F3A5F` header row with white text;
- a `#FFE699` background on any "No clear owner" cell;
- the "Forward to" line in grey italics.

Don't use images or external CSS.
