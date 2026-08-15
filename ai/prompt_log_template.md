# Prompt log - task 1
## What I wanted
A breakdown of the Part B project folder before doing any code - including the folder structure, purpose 
of each subfolder, which scripts already exist, which need editing, which must never be modified, and 
the end-to-end project flow.

## Prompt (s)
I am completing FINS3645 Project Part B in the file path fins-agent\fins2026\z5481255_projectB Explain:
-the folder structure
-what each folder is used for
-which scripts already exist
-which scripts I need to edit
-which scripts should never be modified
-how the project flows from beginning to end. 
Do not generate code at this stage.

## What the assistant produced 
Provided the full folder tree for z5481255_projectB, explained the purpose of each folder. Listed which 
scripts already exist as stubs versus already-working (data_access.py, check_handin.py, test_smoke.py 
all working; run_part_b.py, etl.py, features.py, sentiment.py, portfolios.py, fusion.py, and streamlit_app.py 
all stubs). Listed the eight scripts to edit, including replacing AGENTS.md/CLAUDE.md. Listed the four 
things that should never be modified. Described the full eight-step project flow from loading raw data 
through to deployment, ending with the exact run order (run_part_b.py -> streamlit run -> 
check_handin.py -> git status).

## What was wrong or risky 
Nothing in the output was incorrect - this was just an introductory request with no code or claims to verify yet.

## What I changed and why 
Nothing changed - used this as my baseline understanding for how to build on my Part A foundation. 


# Prompt log - task 2
## What I wanted
To understand whether Part B specifies its own integrity-check methods or leaves them open to reuse 
from Part A, which format daily_returns() should use, whether the headline panel logic can stay 
unchanged, and what run_part_b.py's step order is.

## Prompt (s)
Before writing code, read PROJECT_BRIEF.md for Project B (not Project A), plus 
context/DATA_GUIDE.md and context/project_context.md. Then answer these in plain language - no 
code yet.
1.Does Part B's brief say how to do the integrity checks in etl.py (dedup, missing dates, outliers), or is it 
left open to me? If its left to me, can I just reuse my Part A method exactly - dedup on (ticker, date), 
missing-date audit, and the rolling 63-day / z>5 outlier method? Tell me if anything about Part B means 
this should change. 
2.daily_returns() can return long format (ticker, date, return) like my Part A version, or wide format 
(dates as rows, tickers as columns). Which is better here?
3.Can assemble_headline_panel() stay exactly the same as my Part A version - dedup on (ticker, date, 
title), map to the next trading day, one row per headline - since scoring and lagging happens later in 
sentiment.py, not here?
4.run_part_b.py only loads equities and crypto right now. Confirm I also need to load news headlines, 
and give me the correct order of steps for main() based on returns -> funds/backtests -> sentiment -> 
fusion -> save outputs.
Don't write any code yet - just answer these questions and justify. 

## What the assistant produced 
Confirmed the Part B brief leaves integrity checks open (those were Part A Station 1 deliverables, and 
the brief explicitly says to reuse the Part A foundation). Approved reusing the exact Part A method 
(dedup, missing-date audit, rolling-63-day/z>5 outlier flagging), with two caveats: cap crypto at 
2023-12-31 (10 stray 2024-01-01 rows), and keep the crypto-returns-then-left-merge ordering intact. 
Recommended wide format for daily_returns() since portfolios.py computes covariance and feeds a 
weight vector into an optimiser, and wide format lines the covariance matrix up directly with the 
DataFrame's columns - stated this matches the oos_backtest() stub signature. Confirmed 
assemble_headline_panel() should stay identical to Part A, flagging two things to verify not change: 
timezone normalisation before the merge, and not stripping raw text since VADER relies on 
casing/punctuation/negation. Confirmed run_part_b.py needs to load news headlines and gave the full 
9-step order for main(), ending with a warning that sentiment must be lagged before reaching fusion.py 
or look-ahead is reintroduced. 

## What was wrong or risky 
The wide/long recommendation and reuse approval hadn't yet been checked against the actual Part B 
stub signatures or a real long/wide compatibility check.

## What I changed and why 
Proceeded to verify the daily_returns()/sector_sentiment_index() shape compatibility directly (task 3) 
before accepting the format recommendation.


# Prompt log - task 3
## What I wanted
To confirm, before committing to a wide-format daily_returns(), that the long headline/sentiment chain 
and the wide returns chain would actually connect without needing an unplanned reshape.

## Prompt (s)
Before we proceed: does sector_sentiment_index() in sentiment.py expect long or wide format 
returns/panel data as input? I want to know now, since assemble_headline_panel() stays long and 
daily_returns() is going wide - confirm these two shapes will actually connect cleanly downstream rather 
than needing an extra reshape I haven't planned for.

## What the assistant produced 
Confirmed sector_sentiment_index() expects long-format input. Explained the whole sentiment pipeline 
stays long end-to-end (panel -> scores -> sector index) and never touches the wide returns, while 
daily_returns() going wide is only consumed by portfolios.py meeting only inside fusion.py. 
Recommended keeping score_headlines() returning per-headline or per-ticker-day long scores, and 
doing the ticker-day averaging inside sector_sentiment_index().

## What was wrong or risky 
Nothing wrong 

## What I changed and why 
No changes needed - just confirmed the shape for later steps. 


# Prompt log - task 4
## What I wanted
Where in the pipeline the >/= 1 trading day sentiment lag is applied. 

## Prompt (s)
You didn't mention where the >=1 trading day lag gets applied in this chain. Confirm exactly: does 
sector_sentiment_index() output the lagged date directly (so date X's row reflects sentiment measured 
on date X-1 or earlier), or does the raw (unlagged) index get produced here and the lag applied later, 
inside fusion.py? I want one clear point in the pipeline where this happens, not something that could be 
silently duplicated or skipped between two files.

## What the assistant produced 
Confirmed the lag is applied inside sentiment.py as the final step of sector_sentiment_index(), not in 
fusion.py, and explained why this is the correct granularity (score_headlines() scores at 
headline/ticker-day level, which is the wrong shape for a time-series lag). Gave me two implementation 
nuances: shift by the trading calendar not calendar days, and reindex to the full trading grid before 
shifting so the fill policy doesn't distort the shift. 

## What was wrong or risky 
The assistant’s answer assumed I already chose a no-headline-day policy when I hadn't.

## What I changed and why 
Followed up (task 5) to force the no-headline-day policy decision before accepting this lag design as final.


# Prompt log - task 5
## What I wanted
To choose the no-headline-day policy (drop/carry-forward/neutral) with the lag mechanics already in view.

## Prompt (s)
Before I approve this lag design: I haven't chosen the no-headline-day policy yet (drop/carry-forward/neutral). 
Walk me through how the lag and the shift behave differently under each of the three options rather than picking the policy first.

## What the assistant produced 
Walked through all three policies with an eight-day example. Drop: keeps only news days before 
shifting, producing a variable lag and deferring the fill decision to a later file (a duplication risk). 
Carry-forward: fills the calendar with the last known score before shifting. Neutral-fill: discards the signal 
on single no-news days, leaving thin sectors mostly at zero. Recommended carry-forward, and flagged 
that the brief states the policy at the ticker-day level, so the same policy should apply at both levels for 
consistency. 

## What was wrong or risky 
The recommendation was reasonable but it didn't establish whether carry-forward would persist a stale 
score for days or for weeks. 

## What I changed and why 
Requested the headline-density gap data (task 6) before locking in carry-forward as the policy


# Prompt log - task 6
## What I wanted
Evidence on how long carry-forward could persist a stale sentiment score in a thin sector.

## Prompt (s)
For a sector with a long gap between headlines (eg. Materials or Utilities), how many trading days can 
carry-forward persist a single old score before the next headline arrives? Pull this from the actual 
headline-density data we already computed in Part A (classify_headline_density) - I want to know how 
long this gap is before committing to carry-forward as the policy. 

## What the assistant produced 
Sector-level and ticker-level news-coverage gaps from the real news data. Found that at the 
sector-index level the gap is several days, with even the thinnest sectors having news on ~92-95% of 
trading days with a max gap of 3-4 trading days. Longer gaps were found to only exist at the individual 
ticker level (eg. AEP up to 33 trading days). Recommended keeping carry-forward at the sector-index 
level and applying it after sector-level averaging.

## What was wrong or risky 
Nothing risky - it directly answered my question from task 5. 

## What I changed and why 
I used this as reasoning to confirm carry-forward as the final policy in later steps while flagging the 
ticker-level tail risk as something fusion's design needed to account for. 


# Prompt log - task 7
## What I wanted
To see the evidence behind the AEP tail-gap number and to know whether the ~92-95% sector 
coverage figure represented multi-ticker news flow or mostly single-ticker mentions.

## Prompt (s)
For AEP, show me the two consecutive headline dates that produce the 33-trading-day gap. I want to 
see the real before/after headlines surrounding that gap. Also, Of the ~92-95% of "has news" days in 
Materials/RealEstate/Utilities, what fraction have news from only 1 of the 5 tickers versus 2+? I want to 
know if "has news" mostly means "one ticker got mentioned" or sector-wide coverage. 

## What the assistant produced 
Identified the two headline dates (2020-06-10 to 2020-07-27) and showed the real headlines: before 
was an ETF article mentioning AEP only incidentally; after was four AEP-specific headlines. For the 
coverage question, single-ticker days were only ~14-17% of news days across the three thin sectors, 
with 80%+ of news days covering 2-5 tickers, confirming the coverage figure reflects sector-wide flow. 
Concluded the real risk is ticker-level persistence inside fusion, not the sector index.

## What was wrong or risky 
Both answers sources the actual data with specific dates and headline text. 

## What I changed and why 
This output informed keeping fusion at the sector level rather than the ticker level (see task 8). 


# Prompt log - task 8
## What I wanted
Final confirmation that the sentiment fusion design matches the brief exactly before any code was written.

## Prompt (s)
Confirm the final design of sentiment tilt in fusion.py operates at the sector level only (carry-forward 
computed once in sector_sentiment_index(), then the same sector value applied to every ticker in that 
sector's fund weights). This avoids needing a separate mechanism for the AEP-style tail cases. Confirm 
this matches how the brief describes fusion, and flag if anything in the brief specifically requires 
ticker-level granularity instead.

## What the assistant produced 
Confirmed the sector-level design matches the brief, citing the relevant lines. Confirmed sentiment 
applies to equity data only, crypto keeps base weights. After this confirmation, the assistant proceeded 
into implementation without an explicit approval by myself: it read the stubs and Part A reference code, 
verified the environment, then implemented etl.py, features.py, sentiment.py, portfolios.py, fusion.py, and 
run_part_b.py in sequence, fixing several bugs along the way (index-based OOS date arithmetic, a 
pandas join overlap error, an index-naming KeyError), ran the full pipeline end-to-end, found and fixed a 
rebalance-day weight-sum bug and a crypto double-counting bug in one figure.

## What was wrong or risky 
The assistant treated my confirmation-seeking question as authourisation to proceed with full 
implementation, without me actually giving it approval to proceed - overriding my agent instructions of 
the plan-then-approve workflow. Several bugs were also found and silently fixed mid-implementation.

## What I changed and why 
Rewrote sections of AGENTS.md more explicitly, specifying that the assistant must stop and wait for an 
explicit go-ahead after every question from that point forward, and requested before-and-after 
differences for every bug fix made (task 9).


# Prompt log - task 9
## What I wanted
To stop further unapproved agent actions from happening, to see the exact before/after code for every 
bug fixed, and to get a list of which generated figures needed my review. 

## Prompt (s)
Show me the before/after code diff for these three fixes, in order: (1) the OOS-only reindex bug, (2) the 
rebalance-day weight/date-range bug, (3) the crypto double-counting fix. I want to see each one. 
Also confirm how you said you can't view images and verified figures numerically only - list every figure 
you generated so I know which ones I need to review.

## What the assistant produced 
Provided all three before/after diffs:
(1) adding a reindex to fix fund_returns.csv containing pre-OOS zero-return rows
(2) an inclusive rebalance-day end-slice so weight sums became exactly 1.0, changing several metrics
(3) separating crypto ticker columns from the sector aggregation to stop double-counting in the 
weights-over-time figure. Confirmed it could not view images and listed all six generated figures for 
manual review.

## What was wrong or risky 
Nothing wrong or risky here - this output went over the earlier bugs and fixes and supplied the concrete 
evidence requested. Confirmed several of the bug fixes had changed core performance numbers.

## What I changed and why 
Used the differences to independently verify each fix's correctness before accepting any of the numbers 
produced during the unauthourised run, checking all six figures. 


# Prompt log - task 10
## What I wanted
My assistant to demonstrate that it has read and understood my newly edited AGENTS file and to do a 
full audit of everything that it built against that file before moving forward. 

## Prompt (s)
I've replaced CLAUDE.md with the real project instructions. Read CLAUDE.md and AGENTS.md in file 
path fins-agent\fins2026\z5481255_projectB in full now, then do two things before anything else - no 
code, no further tool calls beyond reading files needed for the audit below.
1. Confirm you've read CLAUDE.md and AGENTS.md by summarising it back to me in your own words, 
section by section. I specifically want you to restate Section 6 (Workflow and Approval) in detail - tell me 
exactly what it requires of you regarding stopping and waiting for explicit approval, and confirm you 
understand that a clarifying answer or explanation from you is not the same as me approving 
something.
2. Audit everything you've already built (etl.py, features.py, sentiment.py, portfolios.py, fusion.py, 
run_part_b.py, streamlit_app.py) against this CLAUDE.md file, and tell me anywhere the existing code 
does NOT match what's written in it. In particular check:
- The covariance shrinkage in portfolios.py (delta=0.05) - is this mentioned or justified anywhere in 
CLAUDE.md? If not, flag it as an unapproved methodology choice per Section 6.
- The crypto weekend-merge method (log-cum-sum reindex/expm1, folding weekend moves into the 
next equity day) - CLAUDE.md Section 3 states crypto non-trading days should be dropped from the 
merged panel, consistent with Part A. Confirm whether the current code matches this or contradicts it.
- Anywhere else you made a methodology choice (rebalance frequency, risk-free rate assumption, 
transaction costs, window length, solver choice) that isn't explicitly stated or justified in CLAUDE.md.
- Whether every number or claim already reported to me (e.g. Sharpe ratios, the AEP gap analysis, 
coverage percentages) was actually verified per Section 4's rules, or just stated.
List every mismatch you find, even small ones. Don't fix anything yet - just report back what you find.

## What the assistant produced 
Provided confirmation that it read both CLAUDE.md and AGENTS.md. Listed eight methodology 
choices in the AGENTS file that I didn’t document in CLAUDE.md (covariance shrinkage, 
solver+fallback, expected-return estimator, tilt strength, z-score standardisation, fusion fund scope, 
dropna thresholds, an undocumented equity date cap). There were some contradictions regading the 
crypto weekend-fold method versus CLAUDE.md's stated drop rule, and a rebalance-day 
weight-coverage discrepancy. Found that there were no on-chart captions anywhere and made a more 
honest self-assessment of which prior claims it made were actually verified, including admitting no 
record existed of an AEP gap analysis being run in the current session context.

## What was wrong or risky 
The audit was thorough and justified, but it showed how much of the pipeline was built on unapproved 
methodology choices and that my instruction files contradicted themselves in some areas. 

## What I changed and why 
I used this output to guide my decisions in tasks 11 to 13, rather than rejecting the whole pipeline it 
developed. I made sure that the self-contradictions were dealt with myself rather than my agent’s discretion. 


# Prompt log - task 11
## What I wanted
To resolve the crypto weekend-merge method, the rebalance-day boundary, and the carry-forward-level 
question with evidence and explanations before merging AGENTS.md and CLAUDE.md into one file.

## Prompt (s)
I am going to merge the contents of the two files AGENTS.md and CLAUD.md into one by myself. 
AGENTS.md will be the single source of agent instructions and I will empty CLAUDE.md because the 
file must still exist, just with no content -- It just has one line "see AGENTS.md". 
Before merging AGENTS.md and CLAUDE.md, I need answers to these questions Don't change any 
files or run code yet - just answer: 
1. Crypto weekend merge - I have three different descriptions (drop, carry last value forward, fold into 
next day) and I don't know if they're actually different or just worded differently. Pick one crypto ticker, 
one week with a weekend in it, and show me the real numbers for what Monday's merged return would 
be under each of the three methods. Once I see the actual numbers I'll pick one.
2. Rebalance days - the code applies weights from r through and including the next rebalance date, not 
up to the day before. Explain simply why this is still look-ahead-safe, so I understand it before approving it as-is.
3. Carry-forward - in plain terms, when a ticker has no headline but other tickers in its sector do, what 
actually happens to that ticker in the sector average? One clear sentence, no jargon.
Just answer, don't fix anything yet.

## What the assistant produced 
Confirmed that no files were changed and no code was run. Explained that "carry last value forward" 
collapses into either drop or fold depending on whether returns or price levels are carried forward. 
Provided a hypothetical worked table showing drop and fold produce different Monday returns, and 
asked for approval to run the real read-only computation. Explained why weights applying through the 
rebalance date itself is still look-ahead-safe. Explained plainly that a silent ticker simply isn't counted in 
that day's sector average. 

## What was wrong or risky 
Nothing wrong or risky. 

## What I changed and why 
I approved the items individually in task 12 and did crypto-merge numbers before finalising that specific 
decision (task 13), rather than deciding on the hypothetical table alone.


# Prompt log - task 12
## What I wanted
To make a decision on each of the previously flagged unapproved items and have the fixes applied with the differences shown to me. 

## Prompt (s)
These are my batch decisions on items 1-8, 12-15:
Approved as-is: 1 (shrinkage), 2 (solver+fallback), 3 (expected-return estimator), 4 (tilt=0.10 - this was 
already in my original AGENTS.md, carry it into the merged file), 5 (z-score standardisation - same, 
already implied by original AGENTS.md), 7 (dropna/fallback thresholds).
Approved with a required fix:
- 6: keep fusion scoped to the 2 Combined funds, but state this explicitly in AGENTS.md and flag it for 
the report as a deliberate scope choice.
- 8: confirm the equity date cap is genuinely a no-op (check whether any real equity rows exist past 
2023-12-31) before treating it as harmless.
- 14: state the exact rebalance rule in code comments and AGENTS.md (21 trading days for 
combined/equity, 30 for crypto), and fix the app's "rebalanced monthly" label since it's wrong for crypto's cadence.
Must fix, not approved as-is:
- 12: add the sample-period annotation to sharpe_barplot.png.
- 13: add a caption to all 6 figures, not just titles/axes/sample period.
- 15: replace the hardcoded date strings in streamlit_app.py with values computed from the actual loaded data.
Make these fixes now, showing me diffs for each, then wait for further instructions.

## What the assistant produced 
Real BTC-USD numbers for one specific weekend (drop -1.87%, fold +0.33%, opposite signs). Applied 
all approved fixes and showed diffs for each: AGENTS.md updated with the fusion-scope explanation 
and exact rebalance rule. The missing sample-period annotation was added to the Sharpe bar plot; and 
the hardcoded app date strings replaced with values computed from the loaded data, including a corrected rebalance-rule label. 

## What was wrong or risky 
The fixes were correct but the results folder still contained the artifacts versions pre-fix. 

## What I changed and why 
Waited to approve a full re-run until after the crypto weekend-merge decision was finalised so that the 
re-run regenerates everything together. 


# Prompt log - task 13
## What I wanted
Multi-week evidence on how often and by how much drop and fold diverge before finalising the crypto merge decision. 

## Prompt (s)
Before I finalise the crypto merge decision, three things need to be confirmed:
1. The BTC-USD week you already checked showed Drop and Fold with opposite signs, not just 
different sizes. Show me the same drop-vs-fold comparison for 3-4 more weeks, including at least one 
from March 2020 (COVID crash) and one from a calmer period, so I know if sign-flips like that are common or not.
2. Confirm the initial estimation window is one year of each family's own calendar (252 equity days / 365 
crypto days) - is that actually what I confirmed earlier, or is this a number you chose? I want to make 
sure this is correct before it's locked into the code comment and used for the report's first-live-date figures.
3. Once I approve the final crypto merge method, the next full pipeline re-run needs to regenerate 
everything - not just the numbers affected by the merge fix, but also today's caption, sample-period, and 
hardcoded-date fixes, since none of those are reflected in the actual results/ folder yet. Confirm the 
re-run will pick up all of this together in one pass.
Just answer 1 and 2 for now - don't run the pipeline yet.

## What the assistant produced 
Ran a check on 208 weeks of BTC-USD data. 44 of them (21%) show drop and fold giving 
opposite-signed returns, so the sign-flip seen earlier is common, not a one-off. For the estimation 
window, the assistant admitted the 252/365-day figure was never actually approved by me, just chosen 
during implementation. Gave two options (252/365 per calendar, or one consistent calendar for all) and 
asked me to pick. Confirmed no pipeline run yet, still waiting on both decisions. 

## What was wrong or risky 
This was a well-reasoned output that did not assume the window was approved. 

## What I changed and why 
Made the final decisions on both items before approving the single combined pipeline re-run.


# Prompt log - task 14
## What I wanted
To finalise the crypto weekend-merge decision (drop), confirm the initial estimation window, and keep 
the rebalance boundary as-is, then have the code changed before I re-run the pipeline.

## Prompt (s)
These are my decisions:
1. Crypto weekend merge -- confirmed DROP. The multi-week analysis (21.2% of weeks sign-flip, mean 
2.15% weekly divergence, and the 2020-03-30 case where drop/fold fully reverse) makes this clearer, 
and consistent with Part A. Update etl.py's merge function to drop, not fold - show me the difference before applying it.
2. Initial estimation window -- confirmed 252 equity days / 365 crypto days - one year of history on each 
family's own calendar, consistent with the same 252/365 annualisation convention already used 
elsewhere. Update the AGENTS.md comment and code comment to state this was explicitly confirmed, not just assumed.
3. Rebalance boundary -- keeping the code as-is (weights apply to the half-open interval (r, next_r]), as already decided.
Make the drop-vs-fold change now, show me the difference. Once I approve it, re-run the full pipeline in 
one pass - this should regenerate all funds, metrics, and figures (crypto-merge-dependent AND the 
earlier caption/sample-period/hardcoded-date fixes, since neither has been reflected in results yet). 
Report the new numbers against the old ones so I can see what changed. Then wait for further 
instructions before doing anything else.

## What the assistant produced 
The assistant changed the crypto merge function to drop weekend returns instead of folding them, 
removed an unused import, and updated the code comments to say the estimation window was 
confirmed. It checked the change worked as intended, showed the difference, and waited for approval 
before running the pipeline. 

## What was wrong or risky 
Nothing wrong but the change had already been applied before the difference was shown. 

## What I changed and why 
Reviewed the difference and proceeded to merge AGENTS and CLAUDE content (as there was overlap 
since I realised I put instructions redundantly in both) before approving the pipeline rerun. 


# Prompt log - task 15
## What I wanted
A complete, merged AGENTS.md file with the missing sections added and no contradictions, shown to me before saving. 

## Prompt (s)
Before I approve the pipeline re-run, finish the AGENTS.md merge. Add these sections from 
CLAUDE.md, which are currently missing from AGENTS.md entirely:
1. The full Workflow and Approval section (stop-and-wait rule, "a clarifying answer is not approval," 
bug-diff requirement, image-viewing limitation, check_handin.py caveat).
2. The Verification Constraints section (citation/number/claim honesty, what the assistant must proactively enforce).
3. Expand the Project overview to include the actual required minimums: >=2 optimisation methods, the 
six fact-sheet items, the sentiment index description, the four-part app journey.
4. The Report section (structure, word count, target-user/customer-journey requirement, deliverables list).
5. The innovation-examples list from the brief.
Also check for and remove any duplicate or contradictory wording now that the crypto-merge and 
rebalance bullets were added incrementally alongside older text - confirm there's exactly one, 
non-contradictory statement of each rule.
Show me the full merged AGENTS.md before saving. Once I approve it, empty CLAUDE.md to a single 
line “See Agents.md”. Only after both of those am I approving the pipeline re-run.

## What the assistant produced 
A full draft of the merged file covering all five requested sections, plus a few extra rules pulled from 
CLAUDE.md that would otherwise have been lost. It removed duplicate wording and explained what it 
added, without saving anything yet. 

## What was wrong or risky 
It correctly waited for approval before saving.

## What I changed and why 
Reviewed and approved the draft in the next message before letting the pipeline run.


# Prompt log - task 16
## What I wanted
The approved changes saved and the full pipeline re-run with a clear comparison of old vs new numbers.

## Prompt (s)
Approved - the etl.py diff, the numpy cleanup, and the AGENTS.md/comment updates all look correct. 
Run the full pipeline now and report the new numbers next to the old ones.

## What the assistant produced 
The assistant saved the merged file, emptied CLAUDE.md as I requested, and ran the full pipeline. It 
reported the new performance numbers next to the old - the combined funds changed as expected from 
the merge fix, while the equity-only and crypto-only funds stayed exactly the same. It noted all six 
figures were regenerated and still needed a visual check.

## What was wrong or risky 
The changes matched what I requested given the fix only affects combined funds.

## What I changed and why 
Moved on to checking which sentiment lexicon was actually being used. 


# Prompt log - task 17
## What I wanted
To confirm whether Part B was using plain VADER or the extended lexicon I built in Part A.

## Prompt (s)
What lexicon does score_headlines() in sentiment.py actually use right now - VADER (nltk's default 
vader_lexicon), or the extended VADER + Loughran-McDonald lexicon I built in Part A (VADER base + 
68 confirmed 2020-2023 LM words)? Show me the actual code that loads/builds the lexicon, don't just describe it.

## What the assistant produced 
Showed the actual code and confirmed that the plain and unextended VADER was being used - the Part A 
lexicon extension had never been added to Part B. 

## What was wrong or risky 
This was correct as I did not tell it to add my part A dictionary in the pipeline. 

## What I changed and why 
Used this finding to decide to build a new lexicon extension for Part B.


# Prompt log - task 18
## What I wanted
A finance-specific VADER lexicon extension for Part B - first by seeing the words and scores from the 
Loughran-McDonald dictionary before any code was written.

## Prompt (s)
I want to extend VADER's lexicon with finance-specific terms as a way to demonstrate innovation for 
Part B. Please be aware that this is different from Part A's rule where Part A banned assigning 
sentiment scores to words (counting only). Part B is different - the brief explicitly names "extending 
VADER's lexicon... having your AI agent propose finance terms and assign them sentiment scores" as a 
sanctioned innovation example. So now, proposing and assigning valence scores is exactly what's wanted.
Do this in steps, showing me output before implementing anything:
1. Check which words from the Loughran-McDonald Negative and Positive category lists (the dictionary 
I used in Part A) are absent from plain VADER's current 7,502-word lexicon. Show me the count and a 
sample of missing words in each category.
2. From that gap list, propose a shortlist of finance-specific terms that appear in market-news headlines 
rather than unspecific jargon. Aim for a focused list (about 50-100 words), not everything from LM.
3. For each proposed word, assign a valence score on VADER's own scale (roughly -4 to +4, matching 
the intensity of existing VADER entries - show me 2-3 comparable existing VADER words and their 
scores as a reference point) and give a one-sentence justification for why that score fits typical usage in 
financial headlines specifically.
4. Show me the full proposed word list with scores and justifications before writing any code. I'll review 
and approve or adjust before you build the extended lexicon into sentiment.py.
Don't implement anything yet - just do steps 1-4 and show me the output.

## What the assistant produced 
The assistant looked for the Loughran-McDonald dictionary confirmed that Part A dictionary extension was from a hardcoded 
flat 67-word list tied to 2020-2023 which I extracted from the Loughran-McDonald dictionary. It confirmed that these words 
were mostly neutral jargon rather than sentiment words. It flagged this mismatch and asked which source to use before continuing.

## What was wrong or risky 
My prompt was misleading as it assumed that the Part A dictionary was the full Loughran-McDonald dictionary when it was not. 

## What I changed and why 
Chose to drop Loughran-McDonald entirely and build the list from the real headline corpus instead.


# Prompt log - task 19
## What I wanted
A finance-sentiment word list built directly from the real headline data with scores and justifications.

## Prompt (s)
Skip Loughran-McDonald entirely - drop it from consideration for this task, now and going forward for 
this lexicon extension. Don't cross-check candidates against LM's master lists.
I want to go with Option 3 only: identify finance-sentiment candidate words by looking at what actually 
appears frequently in the 146,836 headlines that are absent from VADER's current 7,502-word lexicon, 
and that reasonably carry directional meaning in market-news headlines specifically (not neutral jargon 
like tickers or company names). 
Proceed with steps 2-4 from my original instructions on this basis:
-Shortlist ~30-60 real candidate words from the headline corpus
-For each, propose a valence score on VADER's scale (-4 to +4), calibrated against 2-3 comparable 
existing VADER words, with a one-line justification for why that score fits typical financial-headline usage
-Check for overlap with existing VADER words and flag any explicitly rather than overwriting
Show me the full list with scores and justifications before implementing anything.

## What the assistant produced 
The assistant mined the headline corpus and proposed a 60-word list (28 positive, 32 negative), 
each with a score, a comparable VADER word for reference, and a short justification. It also listed words 
that already exist in VADER, and words it deliberately left out because their meaning depends on 
context. Nothing was implemented yet. 

## What was wrong or risky 
The list was well sourced from real data with clear reasoning, and ambiguous words were correctly excluded. 

## What I changed and why 
Before approving I asked whether the change could affect anything else in the codebase.


# Prompt log - task 20
## What I wanted
Confirmation that adding the new words to VADER's lexicon would only affect the sentiment-scoring 
Function and not anything else in the project.

## Prompt (s)
Confirm the .lexicon.update() call only affects the SentimentIntensityAnalyzer instance used inside 
score_headlines() - does anything else in the codebase call _get_vader() and expect plain, unextended 
VADER? If so, the update approach could unintentionally affect it too.

## What the assistant produced 
My assistant checked the whole codebase and confirmed nothing else uses a plain VADER, so the 
change is fully contained. It also noticed the function's docstring claims to cache results when it actually 
doesn't, and flagged that as a separate small issue.

## What was wrong or risky 
Provided a thorough, verified answer that also caught an unrelated documentation problem on its own.

## What I changed and why 
Asked for the docstring/caching issue to be fixed alongside implementing the lexicon extension.


# Prompt log - task 21
## What I wanted
The docstring issue to be fixed, the lexicon extension implemented, and the pipeline re-run with the new 
sentiment and fusion numbers compared to the old ones, plus a list of which figures changed.

## Prompt (s)
Approved – but two things: fix the "cached" docstring to match reality (either add lru_cache, or reword 
the docstring - this is up to you, just tell me which you do and why), and and confirm score_headlines() 
only calls _get_vader() once per pipeline run, not once per headline.
Once that's settled, implement the .lexicon.update() extension, update AGENTS.md's methodology 
section to note this as the lexicon extension, and re-run the full pipeline. Report the new 
sentiment/fusion numbers next to the old ones, and list which figures changed so I know what to re-check visually. 

## What the assistant produced 
Added real caching to make the docstring accurate, confirmed the function is only called once per run, 
then implemented the lexicon extension and updated AGENTS.md. After re-running the pipeline, it 
reported all ten sector sentiment scores shifted upward and the two fused funds' Sharpe ratios 
improved, and confirmed only the two sentiment-related figures changed.

## What was wrong or risky 
The numbers moved sensibly (more positive words than negative in the new list) and the change stayed scoped to the 
sentiment-related parts of the pipeline. 

## What I changed and why 
Moved on to deployment preparation next before beginning the report.


# Prompt log - task 22
## What I wanted
A check of the project against the deployment guide's requirements, a local app test, a hand-in check, a 
nested-repo check, and a clear checklist of what the assistant can do and what only I can do - with 
nothing touching git until I approved.

## Prompt (s)
Stop and Read STUDENT_DEPLOY.md in file path z5481255_projectB\docs then do the following in 
order - wait for my approval before any step that touches git or GitHub.
1. Check the current state against the guide's requirements: does streamlit_app.py exist at the folder 
root, does .streamlit/config.toml exist, is nltk correctly absent from requirements.txt and only in 
requirements-dev.txt, and does .gitignore correctly keep results/ committed while blocking raw data? 
Report what's already correct and what's missing.
2. Run streamlit run streamlit_app.py locally and confirm it starts without errors - report the outcome.
3. Run python scripts/check_handin.py and report every [FAIL] and [WARN]. Fix any [FAIL] items you 
find (show me diffs for each), but stop and ask before fixing anything that touches results/ content, not just structure.
4. Check for the nested-repo issue: confirm whether this project sits inside a larger fins-agent repository, 
and if so, tell me exactly what needs to happen (a fresh git init inside the projectB folder specifically, 
and/or a .gitignore entry in the outer repo) before any push - don't run git init or git push yet, just tell me what's needed.
5. Once 1-4 are done, give me a clear checklist split into two columns: what you can do for me 
(build/check/prepare/commit locally), and what only I can do myself (GitHub login, Streamlit Community 
Cloud login, the actual deploy click-through, making the repo public at hand-in, testing the live URL in an 
incognito browser). I want to know exactly where your part ends and mine starts before we proceed further.
Don't run git init, git add, git commit, or git push yet - stop after the checklist and wait for my explicit 
go-ahead before touching git at all.

## What the assistant produced 
The assistant checked step 1 and confirmed everything already matched the guide's requirements. It 
then started the app locally in step 2 and confirmed it launched without errors, showing the local, 
network, and external URLs, then stopped there without continuing to steps 3-5.

## What was wrong or risky 
Only two of the five requested steps were completed, and a background server was left running without 
the rest of the task being finished.

## What I changed and why 
Asked it to continue directly with the remaining steps.


# Prompt log - task 23
## What I wanted
The remaining three steps completed, including the hand-in check, the nested-repo check, and the final checklist of 
what my assistant and I each have to do. 

## Prompt (s)
continue with steps 3–5 (the check_handin.py run, the nested-repo check, and the final "what you do vs. what I do" checklist).

## What the assistant produced 
My assistant stopped the background server, ran the hand-in check and found everything passed with 
two minor warnings, confirmed the project isn't yet its own git repository and explained what's needed 
before it can be pushed, then gave the final checklist of what it can do locally versus what only I can do 
(GitHub login, the actual deploy, making the repo public, testing the live link).

## What was wrong or risky 
The output was clear and accurate with no git actions taken yet. 

## What I changed and why 
Approved the local-only steps next while keeping all GitHub and Streamlit account actions for me to do.


# Prompt log - task 24
## What I wanted
The local preparation steps done (cache cleanup, setting up the repo, staging files), with the full list of 
staged files shown to me before anything was committed.

## Prompt (s)
Go ahead with the local-only steps: pycache cleanup, git init in projectB, the outer .gitignore entry, and staging for commit.
Before you actually commit, show me the full output of `git status` after staging - I want to see the 
complete list of what's staged (especially confirming results/ contents are there and no raw .parquet/.csv 
data files are), not just a summary. Wait for my confirmation before running git commit.

## What the assistant produced 
The assistant cleaned up leftover cache folders, set the project up as its own repository, updated the 
outer folder's ignore rules so it wouldn't get mixed into a different repo, then staged all the files. It 
showed the full list of 41 staged files and confirmed the results are included with no raw data files, then waited for approval.

## What was wrong or risky 
The full list was shown as requested and checked for raw data before asking for approval.

## What I changed and why 
Approved the commit in the next message.


# Prompt log - task 25
## What I wanted
The files committed.

## Prompt (s)
Go ahead and commit

## What the assistant produced 
Before committing, the assistant noticed I had edited the submission checklist file after it was staged, 
ticking several boxes as complete. It flagged that some of those ticks weren't true yet, then committed 
as instructed while reminding me to fix the checklist. 

## What was wrong or risky 
I had accidentally ticked several checklist boxes that weren't actually completed yet, and that inaccurate version got 
committed even though it was flagged first.

## What I changed and why 
Asked for the false ticks to be undone and committed as a follow-up, plus a push dry-run. 


# Prompt log - task 26
## What I wanted
The checklist corrected and committed, and a preview of exactly what a real push would send before 
creating the actual GitHub repo.

## Prompt (s)
Un-tick the boxes for report.pdf, public repo, deployed app, and Moodle submission in 
SUBMISSION_CHECKLIST.md, as they are not true yet and I accidentally ticked them. Commit that fix 
now as a small follow-up commit, then prepare a push dry-run so I can see exactly what would be 
pushed and to what remote, before I actually create the GitHub repo and push for real.

## What the assistant produced 
My assistant fixed the checklist and committed it separately. It then simulated what a real push would 
send, since no GitHub repo existed yet, showing two commits, 41 files, about 22 megabytes total, with 
the fund weights file being the largest. It gave the exact commands to run once the real GitHub repo was created.

## What was wrong or risky 
Nothing wrong.

## What I changed and why 
I created the GitHub repo myself, then asked it to run the two prepared commands. 


# Prompt log - task 27
## What I wanted
The project to be pushed to the new GitHub repository.

## Prompt (s)
Go ahead and run these two commands:
git remote add origin https://github.com/emilijagliguroska/z5481255_projectB.git
git push -u origin main

## What the assistant produced 
The assistant ran both commands and confirmed the push succeeded, with the local and remote copies 
matching exactly. It reminded me that logging into Streamlit Community Cloud, deploying the app, and 
making the repo public at hand-in are all steps only I can do.

## What was wrong or risky 
Nothing wrong - a clean, verified push with clear next steps.

## What I changed and why 
Knowing that my repo and base streamlit app operate and open as required, I moved onto exploring innovation extensions (task 28). 


# Prompt log - task 28 
## What I wanted 
To implement a few app extensions based on StableTrade's actual target user (risk-averse, 
pre-retirement investors), starting from a few directions I already had in mind, and to have the assistant 
expand on them and add its own ideas.

## Prompt (s) 
I want to demonstrate innovation in the Streamlit app's presentation and design grounded in 
StableTrade's actual target user - risk- averse, pre-retirement investors who care about volatility floors 
and drawdown control. Propose features or design choices that specifically serve this specific user's 
preferences. I have written some directions for you to consider but you can propose your own too:
-How risk and drawdown are visually communicated (eg. is a raw Sharpe ratio meaningful to this user) 
-How sentiment analytics are presented - should this user see raw VADER scores
-Accessibility and clarity for a less risk-tolerant and possibly less technically-literate user base
-Anything from the brief's innovation examples (a custom figure/design system rather than the provided 
style, or "any app feature you can argue is genuinely valuable") that fits this specific user 
Explain each idea you propose and why it serves this target user.
Don't implement anything yet - propose ideas first and wait for me to pick which ones to build.

## What the assistant produced 
My assistant proposed six ideas including a dollar-amount growth simulator, a worst-case stress view 
using real in-window events (FTX collapse, the 2022 bear market, March 2023 banking stress), risk 
grades instead of raw Sharpe ratios, a drawdown-recovery-time metric, a sentiment warning gauge 
instead of raw VADER scores, and a custom design system with a glossary. It also opposed using 
COVID as a fund-performance exhibit since the data doesn't support it.

## What was wrong or risky 
Provided good justifications for its interpretation of the extension ideas. 

## What I changed and why 
Asked a follow-up question about which of these proposals actually built on my Part A extensions, 
before deciding which to approve (task 29).


# Prompt log - task 29
## What I wanted 
To understand which of the six proposed app features would meaningfully extend or reinforce the 
specific extensions I'd already built in Part A so I could prioritise the ones that build on part A the best. 

## Prompt (s) 
Which options extend upon or solidify my extensions from part A ?

## What the assistant produced 
My assistant checked the actual Part A AGENTS.md file to confirm what the Part A extensions were 
(weekend-gap analysis, headline-density regime classification, and the extended lexicon 
word-frequency counting). It found that the sentiment warning gauge idea (option 5) ties into the lexicon 
and density-regime extensions, and that the stress view (option 2) somewhat reinforces the 
weekend-gap idea from the FTX crypto event. It noted the other four options don't build on any Part A 
work, then suggested a seventh idea of its own to add a stat to the crypto fact sheet showing what share 
of a coin's cumulative gains happened on days equity markets were closed, as a direct way to surface 
the Part A weekend-gap analysis inside the app.

## What was wrong or risky 
It verified what the part A extensions were and clearly distinguished its own suggestion (the fact-sheet 
addition) from the ideas I proposed. 

## What I changed and why 
I confirmed options 2 and 5 from my original list and approved the fact-sheet addition the assistant proposed. 


# Prompt log - task 30
## What I wanted 
To lock in three specific features to build including the crypto fact-sheet weekend-gain statistic the
assistant had proposed, the stress view, and the sentiment warning gauge.

## Prompt (s) 
Please add to the crypto fund fact sheet -- "X% of BTC's cumulative gains occurred on days US markets 
were closed" -- this would solidify Part A extension 1. In addition, Implement option 2 and option 5.

## What the assistant produced 
The assistant implemented all three approved features, running sanity checks on the changes to confirm 
the pipeline runs smoothly. 

## What was wrong or risky 
Nothing

## What I changed and why 
This marks the end of the app's innovation implementation before committing and report writing.
