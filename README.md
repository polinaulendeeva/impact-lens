# Impact Lens

Impact Lens reads company annual and sustainability reports and estimates how much of each company's business contributes to four impact themes: clean energy, water, health and sustainable food. A language model drafts each assessment with quotes from the report, automatic checks reject drafts that can't be backed up, and a person reviews what is left. Only reviewed scores count towards the portfolio figures.

I built it to learn how to put a language model inside a process where the output has to be traceable and someone has to sign it off. It is a personal project on public reports and a made-up portfolio, not investment research.

## How it works

1. Ingestion. Each PDF is split into pages, cut into overlapping chunks of about 300 words, embedded with a small local model (BAAI/bge-small-en-v1.5) and stored in PostgreSQL with pgvector. Loading is idempotent: a file's hash is checked first, so running it twice changes nothing.
2. Retrieval. For a company and a theme, the eight most relevant chunks are pulled from that company's report.
3. Assessment. Claude Haiku gets the theme definition and the eight passages, and has to answer through a fixed schema: a score from 0 to 3, a revenue share if the report states one, a rationale, and citations with exact quotes. The prompt is a versioned file, and the model name and prompt version are stored with every assessment.
4. Guardrails. Before anything is saved, code checks that every cited chunk was actually retrieved, that every quote appears in that chunk word for word, that any revenue percentage appears in the quoted text, and that the score and the "insufficient evidence" flag don't contradict each other. A draft that fails is rejected and logged with the reason.
5. Review. A Streamlit screen shows each assessment next to its passages. The reviewer approves, edits or rejects, and gives a reason. Assessments and reviews are append-only, so the model's original score is never overwritten.
6. Exposure. SQL views take the latest reviewed score per company and theme and weight it by the portfolio holding. Every figure is shown with the share of the portfolio it covers.

The score scale: 3 means about two thirds of revenue or more, 2 means a main business line, 1 means real but small, 0 means nothing meaningful.

## Results

20 companies, 20 reports, 8,328 chunks, 80 company and theme pairs.

With the second prompt version, 74 assessments passed the guardrails and 6 were rejected, mostly because a quote did not match the source text.

I labelled 40 pairs by hand as a gold set and compared:

| | Prompt v1 | Prompt v2 |
|---|---|---|
| Answered (passed guardrails) | 32 of 40 | 35 of 40 |
| Exact score | 53% | 57% |
| Within one point | 91% | 94% |
| Average bias | +0.31 | +0.14 |

The model is usually close and rarely exact. It tends to score too high, and the second prompt halved that. Its confidence rating tells me very little: high-confidence answers were right 58% of the time, about the same as the rest.

I reviewed all 74 stored assessments: 15 edits, 7 individual approvals and 52 bulk approvals of zero scores after reading the list for missed exposure.

Portfolio exposure after review:

| Theme | Reviewed | Model only | Portfolio covered |
|---|---|---|---|
| Clean energy | 27.3% | 27.3% | 93% |
| Health | 23.7% | 25.7% | 97% |
| Water | 17.0% | 22.3% | 80% |
| Sustainable food | 10.3% | 11.0% | 98% |

The clean energy figure did not move, but four scores behind it did. The corrections happened to cancel out, which is a good reason not to judge the model on the total alone.

## What is wrong with it

The labels are mine, drafted with AI help and not done blind, and I tuned the second prompt on the same 40 pairs I measured it on. The numbers above are optimistic for that reason.

For at least four companies (ABB, Siemens, Schneider Electric, Philip Morris International) I loaded a sustainability report that has no revenue by segment, so neither the model nor I could verify the share. They need the financial report. I have not checked the other fourteen documents for the same problem.

Rejected assessments currently just drop out of the exposure figure. That is why water covers only 80% of the portfolio. They should go to a person for a manual assessment.

The API has no authentication.

## Running it

You need Python 3.12, Docker and an Anthropic API key.

```bash
git clone https://github.com/polinaulendeeva/impact-lens.git
cd impact-lens
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your API key in .env
docker compose up -d
python -m alembic upgrade head
python -m app.seed
```

The reports are not in the repository. `data/sources.csv` lists where each one came from. Download them into `data/raw/` and then:

```bash
python -m ingest.run            # parse, chunk, embed, load
python -m ingest.quality        # data quality checks
python -m agent.run_all         # assess every company and theme
python -m evals.run_evals v2    # compare with the gold set
streamlit run review_ui/streamlit_app.py
python -m analytics.apply       # create the exposure views
python -m uvicorn api.main:app  # API, docs at /docs
```

Tests and linting:

```bash
python -m ruff check .
python -m pytest -q
```

Both run on every push through GitHub Actions. The tests cover the guardrails and the chunking and don't call the model or the database.

## Layout

- `app/` settings, database connection, tables, seed data
- `ingest/` PDF parsing, chunking, embedding, quality checks
- `agent/` retrieval, prompts, schema, guardrails, the full run
- `evals/` gold set, evaluation script, results per prompt version
- `review_ui/` the review screen
- `analytics/` SQL views for current assessments and exposure
- `api/` read-only FastAPI service
- `tests/` unit tests
- `DECISIONS.md` why I made the choices I made, and what went wrong along the way

## Stack

Python 3.12, PostgreSQL 16 with pgvector, SQLAlchemy, Alembic, Pydantic, PyMuPDF, sentence-transformers, the Anthropic API, Streamlit, FastAPI, pytest, ruff, Docker, GitHub Actions.