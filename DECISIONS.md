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