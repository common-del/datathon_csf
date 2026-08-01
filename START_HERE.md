# START HERE

**The drill for the day: `playbook/DAY1_ALGORITHM.md`. The guided analysis: `DAY1_COCKPIT.ipynb`.**

Read this page on Saturday morning. Nothing else.

## The one thing you have to do

1. Get the Akshara CSV from the event intranet.
2. Save it into `C:\Users\CSF\Desktop\Datathon\datathon2026\data\primary\`
3. Close Chrome and other memory-hungry apps (the file is ~5 million rows and the run
   peaks near 4 GB of RAM).
4. Double-click **RUN_ME.bat**
5. Wait. At census scale the full run takes roughly 4 to 7 minutes on this laptop.
   For a fast exploration loop first, open C:\Users\CSF\Desktop\Datathon\datathon2026\src\config.py and set SAMPLE_FRACTION = 0.25
   (about 90 seconds), then set it back to None for the final run.

That's it. No code. No typing.

## Then, in this order

| Order | Open this | Why |
|---|---|---|
| 1 | `outputs\tables\qa_flags.csv` | What's wrong with the data. Read this before you believe anything. |
| 2 | `outputs\RUN_LOG.txt` | Confirms every step ran. Any failures are listed at the bottom. |
| 3 | `outputs\dashboard.html` | Your whole analysis, in a browser. Double-click it. |
| 4 | `playbook\INSIGHT_PLAYBOOK.md` | Tells you what each output means and which sentence to write. |
| 5 | `playbook\DAY1_BATTLE_PLAN.md` | Hour by hour against the 7pm deadline. |

## If something breaks

The pipeline is built so one broken step never stops the rest. If a step fails, it says so and carries on.

**If column detection fails** (the log says NOT FOUND next to a column name):

Open `src\config.py`. Find `MANUAL_OVERRIDES`. Put the real column name in quotes. Save. Run again.

```python
MANUAL_OVERRIDES = {
    "district": "DISTRICT_NAME",     # <- example
```

**If it can't find the 20 question columns**, in the same file set:

```python
MANUAL_ITEM_COLUMNS = ["Q1","Q2","Q3", ...  "Q20"]
```

That's the only editing you will ever need to do.

## What you're carrying that other teams are not

- 8 external datasets already cleaned and joined, at **Gram Panchayat** level, not just district.
- A verified Karnataka district name crosswalk. Every other team will lose an hour to Bijapur vs Vijayapura.
- 5 original metrics with names, already computed.
- A 12-slide deck, pre-formatted, with the figure filenames printed on each slide.
- `claims.json` generated automatically, so every number you quote is traceable.
