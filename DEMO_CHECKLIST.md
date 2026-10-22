# Demo Checklist

## The day before

- [ ] `git pull` and confirm everyone's latest code is in
- [ ] Run `pytest` and confirm every test passes
- [ ] Start the app from a fresh terminal and confirm it opens
- [ ] Confirm the sample workflow loads
- [ ] Confirm one run succeeds, one retries then succeeds, and one fails
- [ ] Have someone outside the team follow the README from scratch
- [ ] Decide who presents which part (see the table below)
- [ ] Rehearse the full demo at least twice, with a timer

## Ten minutes before

- [ ] Close extra browser tabs and apps
- [ ] Activate the virtual environment
- [ ] Start the app and open it in the browser
- [ ] Keep a spare terminal open in the project folder
- [ ] Keep the README open in another tab

## Demo script

| # | What to do | What to say | Who |
|---|-----------|-------------|-----|
| 1 | Open the app and show Source A, Source B, and Combine | "This workflow has three tasks." | |
| 2 | Point at the arrows | "An arrow means this task must finish first." | |
| 3 | Click Check/Validate | "It looks for missing tasks and loops before running." | |
| 4 | Click Run, then show the order and outputs | "Tasks run one at a time in a safe order." | |
| 5 | Show a task that fails once, then succeeds | "It was retried and the second attempt worked." | |
| 6 | Show a task that fails all its tries | "After the last retry, the run fails." | |
| 7 | Point at the skipped task | "Later tasks are skipped because they depended on the failure." | |
| 8 | Open the README | "Anyone can set this up by following these steps." | |
| 9 | State what is not built | "No login, no arbitrary Python tasks, no parallel runs, no scheduling." | |

## If something goes wrong

- **App won't start:** check the venv is active, then run `pip install streamlit pytest` again
- **A run shows an unexpected result:** open the history screen and read the error message aloud. It shows you understand the app
- **Total failure:** show the passing `pytest` output and the saved run history as backup

## After the demo

- [ ] Note any questions you couldn't answer
- [ ] Note what the team would build next (drag-and-drop arrows, more task types, login)