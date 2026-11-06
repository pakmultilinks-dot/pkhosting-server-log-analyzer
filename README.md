# PKHosting Server Log Analyzer

A small tool for a hosting admin who has a log file and wants to know,
in plain language, what went wrong. Upload a web server log or an
application log and the tool groups the problems by type, counts them,
shows the worst URLs and IPs, and suggests a likely cause and a fix for
each problem type. It is built for PKHosting.com, a Pakistani web
hosting brand, but it works on any log in the two formats below.

## Who it is for

A support admin or a site owner who sees errors and wants a quick
answer to three questions: what broke, how often, and what should I
check first. You do not need to read raw log lines to use it. The
per-line table is still there if you want to check the detail.

## Supported formats

Format A, Nginx or Apache combined access log:

```
203.0.113.10 - - [05/Oct/2026:13:55:36 +0500] "GET /shop HTTP/1.1" 200 5123 "-" "Mozilla/5.0" 0.412
```

Format A, Nginx error log:

```
2026/10/05 13:55:36 [error] 123#0: *45 connect() failed (111: Connection refused) while connecting to upstream, client: 203.0.113.10
```

Format B, application log in Python logging style:

```
2026-10-05 13:55:36,123 ERROR app.db: connection to database failed: could not connect to server
```

Generic timestamped lines with a level in brackets, such as
`2026-10-05 13:55:36 [ERROR] something failed`, are also read.

## Problem types

Every line is put into one group: 404 not found, 500 server error,
502, 503 or 504 upstream or timeout, slow request, database connection
error, PHP or application exception, authentication failure, SSL or TLS
error, file not found or permission error, rate limit 429, bot or
crawler flood, and unknown or other. Lines with no problem are marked
OK. A request slower than 5 seconds counts as slow, and a bot user
agent counts as a flood only when the same IP made 10 or more bot
requests in the same file, so one stray crawler visit is not flagged.

## Run it locally

```
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501 in a browser. Upload one or more
`.log` or `.txt` files, or pick a built-in sample log from the menu.
The sample logs are in `sample_logs/`.

## Deploy on Streamlit Cloud

1. Push this repo to GitHub (it is already public at
   https://github.com/pakmultilinks-dot/pkhosting-server-log-analyzer).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Choose New app, pick this repo, branch `main`, and main file
   `app.py`, then Deploy. Streamlit Cloud installs
   `requirements.txt` on its own, no other setup is needed.

## How it was tested

The evaluation uses 18 generated log files in `tests/fixtures/`,
401 lines in total, a mix of Nginx access, Nginx error, Apache
access, and application logs. Each fixture has a ground truth JSON
file stating the expected dominant problem type and one expected label
per line. The fixtures are made by `tests/generate_fixtures.py`,
seeded and deterministic, so regenerating them gives the same files.
No real customer logs were used, and no real PKHosting server was
touched.

Run it yourself:

```
python3 tests/generate_fixtures.py
python3 evaluate.py
```

Results, run 6 November 2026:

- Overall per-line accuracy: 100.0 percent (401 of 401 lines)
- Dominant problem type correct on 18 of 18 fixtures (100.0 percent)
- Full per-log table: `evaluation/results.md` and
  `evaluation/results.json`

Read the 100 percent honestly: the fixtures were generated to match
the parser rules written in `logparser.py`, so the result shows the
parser works as specified on generated data. It does not prove the
parser will be perfect on real-world logs, where lines are messier
and one line can fit two problem types.

## How the code is organised

- `app.py`: the Streamlit interface, upload, samples, summary, charts,
  and the per-line table.
- `logparser.py`: the parser and classifier, standard library only,
  so it can be tested without Streamlit.
- `tests/generate_fixtures.py`: makes the 18 labelled fixtures and
  the 3 sample logs.
- `evaluate.py`: runs the parser on all fixtures and writes the
  evaluation results.
- `sample_logs/`: 3 small demo logs offered in the app.
- `evaluation/`: the latest evaluation output.

## Limitations

- The classifier is rule-based, not a trained model. It matches
  status codes, keywords, and patterns, so unusual log lines fall
  into unknown or other.
- Access log timing only works when the log records a request time.
  Apache combined logs in the fixtures carry no timing field, so slow
  requests in Apache logs are only caught from the message text.
- Bot flood detection needs many requests from one IP in a single
  file. A slow drip from many IPs will not be flagged.
- The tool reads logs you upload in the browser session. Do not
  upload logs that contain passwords, session tokens, or customer
  data. The sample and test logs in this repo are generated and
  contain only example IPs and addresses.
