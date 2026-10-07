---
name: weekly-summary
description: Write a high-level weekly update (accomplished, in flight, needs attention) from Pocket meetings for Sergio's team and management, delivered as a Gmail draft to his Outlook. Use when the user asks for a weekly summary, weekly update, status update, or "what did we get done this week".
---

# Weekly summary

A one-screen update for the team and management. It says what got done, what is in
progress, and what needs a decision or an owner. The output is a **Gmail draft**. Never
send it.

## Fixed settings

- **To:** `sergio.mendezlarregui@flagstar.com`, and only that address. No CC or BCC.
- **Scope:** Work only. This prompt never includes personal content and never asks about scope.
- **Time zone:** America/Detroit
- **Signature:** "Best,\nSergio"

## Inputs

| Input | Default |
|---|---|
| Week | The current week, Monday through today. Use the previous Monday–Friday if today is Saturday–Monday before noon. |
| Audience | Both the team and management. Write for the more senior reader. |

## Steps

1. **Get the data.** Use the newest `seek-output/seek_*.json` whose range covers the week.
   If none does, follow Seek's steps 1–5 for the week with scope `work`, without asking.
   Then keep only `Work` and `Mixed` meetings that fall inside the week. For a Mixed
   meeting, use only the work part.
2. **Group by workstream** using Seek's `tags`. Combine tags that belong together, for
   example `Loan Data` + `QRM/Data Quality` becomes "Loan data & QRM data quality". Aim for
   4–7 workstreams. Leave out `Daily Plan` and `1:1` as workstreams, but use what's in them.
3. **Put each item in one bucket.**
   - **Accomplished:** decisions made, approvals, fixes in place, deliverables finished.
     It has to be stated in a recording as done or decided. A Pocket `TODO` status on its
     own never counts as done.
   - **In flight:** started work with an owner. Show it as "<item> — <owner>".
   - **Needs attention:** items with **No clear owner**, blockers, risks, and overdue items
     (a `due` date before today that is still `TODO`).
   - **Next week:** dated items due next week, plus upcoming meetings that were mentioned.
4. **Write the update** using the template below.
5. **Create the draft** with `create_draft`, filling in `htmlBody` and a plain-text `body`.
6. **Report back:** the subject, the `viewUrl`, the number of workstreams, and anything you
   left out or weren't sure how to classify.

## Template

Subject: `Weekly update – week of <Mon D>`

```
Hi all,

<Headline: 2–3 sentences. The most important result of the week, the main risk, and what
needs a decision. Lead with the conclusion.>

Accomplished
• <Workstream>: <result, with numbers>

In flight
• <Workstream>: <item> — <owner>; <item> — <owner>

Needs attention
• <item> — No clear owner / blocked on <x> / overdue since <date>

Next week
• <item or meeting> — <date if known>

Best,
Sergio
```

## Writing rules

- Use the Pyramid Principle: put the conclusion first, then support it. Write for a busy
  executive who reads only the headline.
- Keep each bullet to 25 words or fewer and the whole update to about 250–350 words.
  Choose what matters rather than listing everything.
- Prefer outcomes and numbers ("Approved 12-mo CD at 4.30% APY") over activity ("Discussed
  CD pricing").
- Name owners. Never invent an owner. If an item has none, list it under **Needs attention**
  as "No clear owner".
- Leave out internal frustrations, interpersonal commentary, and anything said in confidence
  in a 1:1. From a 1:1, use only the agreed priorities.
- If a name is uncertain (for example "Dan / Ben"), use the name in the meeting title and
  mention it to Sergio in chat.

## HTML formatting

Same style as the follow-up prompt:
- Calibri/Arial 11pt;
- `<b>` section headers and `<ul>` lists;
- the workstream name in bold at the start of each bullet;
- "No clear owner" highlighted with a `#FFE699` background.

Don't use tables, images or external CSS.
