# Design decisions

Notes on why Impact Lens is built the way it is. I add to this whenever I pick between two options or something breaks.

## Schema first, AI later

I built the database before writing any LLM code. If a portfolio manager asks why a company got a score, I need to show the model, the prompt version and the passages behind it, and that has to be designed in from the start. It did mean the first few days produced nothing clever to look at.

## Nothing gets overwritten

Assessments and reviews are append-only. A correction is a new row, so I can always see what the model said, what the reviewer changed and when. The cost is that every query needs a "latest row" view, which I'll add with the analytics.

## The database enforces the rules

Scores must be 0 to 3, revenue share 0 to 100, and a review is approve, edit or reject. These are constraints in PostgreSQL, so a bug in my Python can't write bad data. Changing a rule now needs a migration, which I think is the right amount of friction.

## One database for everything

Documents, embeddings, assessments and reviews all live in PostgreSQL with pgvector. I didn't want a second system to secure and keep in sync. A dedicated vector database would scale further, but at 8,328 passages that isn't my problem.

## Migrations for every schema change

I use Alembic and never change tables by hand. It's a bit more work for small changes. In return the schema history is in Git and the database can be rebuilt from scratch.

## Twenty companies, chosen on purpose

Eight have obvious exposure to my themes, six are ambiguous and six have little or none. I wanted the evaluation to check whether the model can tell these apart. Twenty is a small sample, so any accuracy number will be indicative at best.

## Company reports only

The inputs are public annual and sustainability reports. I don't use third-party ESG ratings, because I want each score to point at a page in the company's own disclosure. The downside is that reports are structured very differently and some evidence is hard to find.

## PDFs stay off GitHub

The reports are the companies' copyright, so they're git-ignored. `data/sources.csv` lists company, year, title and URL for each one. Anyone rerunning the project has to download them again.

## Embeddings run on my laptop

I use bge-small-en-v1.5 through sentence-transformers. No document text leaves the machine and there's no cost per call, which is how I'd expect a bank to want it. It's slow on an Intel Mac (the Shell report alone took two and a half


**First retrieval tests.** I ran one question against three reports: a clear case, an ambiguous one and a low-exposure one.

*Vestas, clean energy.* I asked what share of revenue comes from wind turbines. The top five passages were all about revenue, including the key figures on page 8 and the segment definitions on page 55. But three of them were accounting policy on when revenue is recognised, and the actual segment split didn't make the top five.

*Geberit, water.* I asked which products help save or manage water. The top passages were about about revenue and turbines, on pages 8, 55. Page 8 has the actual revenue figures, and page 55 names the business segments.

*Shell, clean energy.* I asked how much revenue comes from renewable energy. three of the five are accounting-policy text about when revenue is recognised (pages 141–142). They match the word "revenue" but don't say how much comes from turbines. The segment revenue split, which is the real evidence, isn't in the top five.

What I took from this: the search finds the right subject, but it can rank text that shares the question's words above the text that answers it. For the assessment step I plan to retrieve eight passages and search with the full theme definition instead of a single question.

**First assessment of Vestas, clean energy.** Score 3 with high confidence, which is right for a company that only makes and services wind turbines. Every claim had a citation with a page number, and the passages were much better than in my first search test: the EU Taxonomy statement on page 129 and the business model on page 60, instead of accounting policy text. The model left the revenue share empty because no passage states a percentage, even though the real answer is close to 100%. That's the behaviour I asked for in the prompt. One quote contained "technol- ogies", a word split by a line break in the PDF, so the quote check will have to allow for small differences like that.

**First assessment of Shell, clean energy.** The model gave a score of 2 with high confidence and a revenue share of 15%. The citations were real, but the 15% came from a chart of energy delivered by volume, not revenue, and it counted all power as clean energy. The chart had also been flattened into text, so the percentages may have been matched to the wrong labels. I kept prompt v1 unchanged as the baseline and added this case to the gold set with an expected score of 1.

**First assessment of Geberit, water.** Score 3 with high confidence. The evidence was good (sales split by product group, page 184), but the model counted everything that touches water as water impact, including bathroom furniture and ceramics. I'd score it 2. The rationale also quoted the company motto differently from the citation. Across my first three tests the model was generous and reported high confidence every time, even when wrong.

**First full run, prompt v1.** 80 company and theme pairs: 72 stored, 8 rejected by guardrails (6 for altered quotes, 3 for a revenue share not written in the cited passage, one pair failing both). All 8 rejections were on pairs where the company has real exposure, so on the 27 pairs that matter the rejection rate was about 30%, not 10%. Ørsted's clean energy assessment was rejected because the model stated a revenue share the passage doesn't give. I loosened the quote check to accept quotes joined with "..." after it rejected an honest stitched quote, and kept it strict for altered text. Rejected assessments need a route to a human reviewer; right now they are only logged.

## How the gold labels were made

I fixed the scale to rough revenue shares first: 3 is about two thirds of revenue or more, 2 is a main business line, 1 is a real activity under about a fifth, 0 is nothing meaningful. An AI assistant drafted the 40 labels and I checked the hard ones against the reports and changed the ones I disagreed with. The labels weren't blind, since I'd seen the model's scores by then. A cleaner test would use labels written before any model run, ideally by someone else.

**Baseline evaluation, prompt v1.** On my 40 labelled pairs, 32 answers passed the guardrails. Of those, 53% matched my score exactly and 91% were within one point. Counting the 8 rejections as wrong, exact agreement was 42%. The model scored higher than me 12 times and lower 3 times. Its stated confidence was no guide: "high confidence" answers matched 55% of the time. The set is deliberately hard, so these numbers understate accuracy across all 80 pairs. Three patterns stood out: a score of 1 for anything that touches a theme, a 3 given too easily, and a 0 for Siemens on clean energy because its document has no segment data.

**Prompt v2 against v1.** I tied the scale to revenue share, excluded the company's own operations, required exact single-span quotes and banned computed percentages. On the same 40 pairs, rejections fell from 8 to 5 and the model's generosity halved (average difference +0.31 to +0.14). The "1 for anything that touches the theme" problem mostly disappeared. Exact agreement barely moved: 53% to 57% of answered pairs, which is within the noise for 40 cases and for a model whose answers vary between runs. It still gives 3 too easily, still reports high confidence almost every time, and still computed a revenue share for Ørsted. I tuned v2 on the same set I measured it on, so even this gain is an upper bound. What's left looks like a data problem (missing segment figures), a model-size question and my own threshold choices, more than a prompt problem.

**REVIEW

**Duplicate review clicks.** The dropdown showed the model's score even after I had edited it, so it looked as if my decision hadn't saved and I approved Vestas three times. I changed the label to show "edited to 1" or "approved". The duplicates stay in the table; the analytics view takes the latest decision per assessment.

**What review changed.** I reviewed all 74 stored assessments: the non-zero ones and five wrong zeros one by one, and 52 plain zeros in bulk after reading the list. Water exposure fell from 22.3 to 17.0. Clean energy stayed at 27.3, but only because my corrections cancelled out: ABB, Shell and ExxonMobil went down and Siemens went up by the same amount. So an aggregate can look right while four of its inputs are wrong. Coverage is 80% to 98% by theme, and every gap is an assessment a guardrail rejected. Ørsted alone is 7% of the portfolio, which means clean energy is understated until someone assesses it by hand.

## The API only reads

I added a small FastAPI service with three endpoints: a health check, the portfolio exposure per theme, and the current assessment for each company and theme.

I left out an endpoint for submitting reviews. A review is supposed to come from someone who has read the cited passages, and the review screen makes that the only way in. If the API accepted reviews, a script could approve a hundred scores without anyone looking at the evidence, and the exposure figures would still say "approved".

The endpoints read from the two SQL views and do no calculation of their own. The rule for which assessment is current and how exposure is weighted is written once, in `analytics/views.sql`, so the API, the review screen and a query in psql all give the same number.

What is missing: there is no authentication, so this is fine on my laptop and not anywhere else. The API also has no tests yet, because they would need a database in CI.

