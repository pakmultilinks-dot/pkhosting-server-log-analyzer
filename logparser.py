"""Rule-based parser for web server and application logs.

Supported formats:
  A. Nginx / Apache combined access logs and Nginx error logs.
  B. Application logs in Python logging style, plus generic timestamped lines.

Every parsed line is classified into one problem type. The parser uses
only the Python standard library, so it can be tested without Streamlit.

Problem type slugs (stable, used in evaluation ground truth):
  ok, 404_not_found, 500_server_error, upstream_timeout, slow_request,
  database_error, app_exception, auth_failure, ssl_error,
  file_permission_error, rate_limit, bot_flood, unknown_other
"""

import re
from collections import Counter

# Human readable labels for the problem types.
LABELS = {
    "ok": "OK, no problem",
    "404_not_found": "404 not found",
    "500_server_error": "500 server error",
    "upstream_timeout": "502, 503 or 504, upstream or timeout",
    "slow_request": "Slow request",
    "database_error": "Database connection error",
    "app_exception": "PHP or application exception",
    "auth_failure": "Authentication failure",
    "ssl_error": "SSL or TLS error",
    "file_permission_error": "File not found or permission error",
    "rate_limit": "Rate limit (429)",
    "bot_flood": "Bot or crawler flood",
    "unknown_other": "Unknown or other",
}

# Likely causes and suggested fixes, shown in the app per problem type.
CAUSES_FIXES = {
    "404_not_found": (
        "A visitor or a search engine asked for a page that no longer exists, "
        "or a link on the site points to a wrong address.",
        "Fix the broken link, add a redirect from the old address to the new "
        "page, or restore the missing file. Check the top URLs in the table.",
    ),
    "500_server_error": (
        "The application crashed while handling the request, often a code "
        "error, a bad deploy, or a service the app depends on being down.",
        "Read the application error log for the matching time, roll back the "
        "last deploy if the errors started after it, and fix the failing code.",
    ),
    "upstream_timeout": (
        "The web server could not reach the application behind it, or the "
        "application took too long to answer. Common causes are a stopped "
        "app server, a full worker pool, or a slow database query.",
        "Check that the app server process is running, restart it if needed, "
        "raise the worker count, and look for the slow query in the app log.",
    ),
    "slow_request": (
        "The request finished but took much longer than normal, usually a "
        "slow database query, an uncached page, or a busy server.",
        "Find the slow URL in the table, check the query behind it, add an "
        "index or a cache, and check server load at that time.",
    ),
    "database_error": (
        "The application could not connect to the database, the database was "
        "down, credentials were wrong, or the connection pool was full.",
        "Check the database service is running, test the login details, "
        "check the connection limit, and look for a recent config change.",
    ),
    "app_exception": (
        "Unhandled code error, such as a missing variable, a bad import, or "
        "a call to a service that returned unexpected data.",
        "Read the full traceback in the application log, fix the failing "
        "line, and add a check for the bad input that caused it.",
    ),
    "auth_failure": (
        "Repeated failed logins, either a user who forgot a password or a "
        "brute force attempt against the login page.",
        "If one IP fails many times, block it and enable rate limiting on "
        "login. If it is a real user, help them reset the password.",
    ),
    "ssl_error": (
        "A certificate problem, such as an expired certificate, a name that "
        "does not match the domain, or a client that cannot do a handshake.",
        "Renew the certificate, check the domain name on it, and confirm "
        "the certificate chain is complete.",
    ),
    "file_permission_error": (
        "The server tried to read a file that is missing or that it has no "
        "permission to read.",
        "Check the file exists at the path in the log, fix the file "
        "permissions and owner, and check the document root setting.",
    ),
    "rate_limit": (
        "Too many requests from one client in a short time, so the server "
        "started refusing with 429.",
        "Find the IP in the table. If it is a real user, raise the limit. "
        "If it is a scraper, keep the limit and block the IP.",
    ),
    "bot_flood": (
        "A crawler or bot is requesting many pages quickly, which can slow "
        "the site for real visitors.",
        "Check robots.txt, slow the bot down with rate limiting, and block "
        "it if it ignores robots.txt and brings no traffic value.",
    ),
    "unknown_other": (
        "The line does not match a known problem pattern.",
        "Read the raw line in the table and check it against the application "
        "documentation for that message.",
    ),
    "ok": (
        "No problem on this line.",
        "No action needed.",
    ),
}

# A request slower than this, in seconds, counts as a slow request.
SLOW_SECONDS = 5.0
# An IP with at least this many bot requests in one file counts as a flood.
BOT_FLOOD_MIN_REQUESTS = 10

BOT_UA = re.compile(
    r"bot|crawler|spider|scraper|headless|python-requests|curl|wget",
    re.IGNORECASE,
)

# Nginx / Apache combined access log:
# 203.0.113.10 - - [05/Oct/2026:13:55:36 +0500] "GET /shop HTTP/1.1" 200 5123 "-" "Mozilla/5.0" 0.412
ACCESS_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<url>\S+) [^"]*" '
    r'(?P<status>\d{3}) (?P<size>\S+) "[^"]*" "(?P<ua>[^"]*)"'
    r'(?: (?P<reqtime>[\d.]+))?'
)

# Nginx error log:
# 2026/10/05 13:55:36 [error] 123#0: *45 connect() failed (111: Connection refused) while connecting to upstream, client: 203.0.113.10, server: example.com, request: "GET / HTTP/1.1"
NGINX_ERROR_RE = re.compile(
    r'^(?P<date>\d{4}/\d{2}/\d{2}) (?P<time>\d{2}:\d{2}:\d{2}) '
    r'\[(?P<level>\w+)\] \d+#\d+: (?P<msg>.*)$'
)

# Application log, Python logging style:
# 2026-10-05 13:55:36,123 ERROR app.db: connection to database failed
# 2026-10-05T13:55:36Z INFO app.web: GET /shop 200
APP_LOG_RE = re.compile(
    r'^(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<time>\d{2}:\d{2}:\d{2})'
    r'(?:[.,]\d+)?(?:Z)?\s+'
    r'(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\b\s*'
    r'(?P<logger>[\w.\-]+)?\s*:?\s*(?P<msg>.*)$'
)

# Generic timestamped line with a level in brackets:
# 2026-10-05 13:55:36 [ERROR] something failed
GENERIC_RE = re.compile(
    r'^(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<time>\d{2}:\d{2}:\d{2})'
    r'(?:[.,]\d+)?\s+\[(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\]\s*'
    r'(?P<msg>.*)$'
)

STATUS_TYPE = {
    404: "404_not_found",
    500: "500_server_error",
    502: "upstream_timeout",
    503: "upstream_timeout",
    504: "upstream_timeout",
    429: "rate_limit",
    401: "auth_failure",
    403: "file_permission_error",
}


def _classify_text(text, level=None):
    """Classify a free text log message (error log or app log line)."""
    low = text.lower()
    if "ssl" in low or "tls" in low or "certificate" in low or "handshake" in low:
        return "ssl_error"
    if any(k in low for k in ("database", "mysql", "postgres", "psycopg", "sqlite", "mongodb", "redis")):
        return "database_error"
    if "too many connections" in low or "connection pool" in low:
        return "database_error"
    if "traceback" in low or "uncaught" in low or "exception" in low or "php fatal" in low or "php warning" in low:
        return "app_exception"
    if "500 internal server error" in low or re.search(r"\b500\b", low):
        return "500_server_error"
    if "upstream timed out" in low or "upstream prematurely" in low or "connect() failed" in low or "connection refused" in low:
        return "upstream_timeout"
    if "timed out" in low or "timeout" in low:
        return "upstream_timeout"
    if "slow query" in low or "slow request" in low or re.search(r"took [\d.]+s", low):
        return "slow_request"
    if "rate limit" in low or "limiting requests" in low or "too many requests" in low or re.search(r"\b429\b", low):
        return "rate_limit"
    if any(k in low for k in ("failed password", "authentication failure", "login failed", "invalid login", "unauthorized", "failed login")):
        return "auth_failure"
    if "no such file" in low or "permission denied" in low or "not found" in low:
        return "file_permission_error"
    if re.search(r"\b404\b", low):
        return "404_not_found"
    if level in ("ERROR", "CRITICAL"):
        return "unknown_other"
    if level in ("WARNING", "WARN"):
        return "unknown_other"
    return "ok"


def _parse_line(raw, line_no):
    """Parse one raw line into a record dict, with a provisional type."""
    rec = {
        "line_no": line_no,
        "raw": raw,
        "format": "unknown",
        "ip": "",
        "url": "",
        "status": "",
        "method": "",
        "level": "",
        "problem_type": "unknown_other",
        "detail": "",
    }
    m = ACCESS_RE.match(raw)
    if m:
        rec["format"] = "access"
        rec["ip"] = m.group("ip")
        rec["url"] = m.group("url")
        rec["method"] = m.group("method")
        rec["status"] = m.group("status")
        rec["detail"] = m.group("ua") or ""
        status = int(m.group("status"))
        reqtime = m.group("reqtime")
        if status in STATUS_TYPE:
            rec["problem_type"] = STATUS_TYPE[status]
        elif reqtime is not None and float(reqtime) > SLOW_SECONDS:
            rec["problem_type"] = "slow_request"
        elif status < 400:
            rec["problem_type"] = "ok"
        else:
            rec["problem_type"] = "unknown_other"
        return rec
    m = NGINX_ERROR_RE.match(raw)
    if m:
        rec["format"] = "nginx_error"
        rec["level"] = m.group("level").upper()
        rec["problem_type"] = _classify_text(m.group("msg"), rec["level"])
        ip_m = re.search(r"client: (\S+)", raw)
        if ip_m:
            rec["ip"] = ip_m.group(1).rstrip(",")
        return rec
    m = APP_LOG_RE.match(raw)
    if m:
        rec["format"] = "application"
        rec["level"] = m.group("level")
        rec["problem_type"] = _classify_text(m.group("msg"), rec["level"])
        return rec
    m = GENERIC_RE.match(raw)
    if m:
        rec["format"] = "application"
        rec["level"] = m.group("level")
        rec["problem_type"] = _classify_text(m.group("msg"), rec["level"])
        return rec
    # Fallback: a bare line, classify on its text alone.
    rec["format"] = "application"
    rec["problem_type"] = _classify_text(raw, None)
    return rec


def parse_log(text):
    """Parse a whole log file. Returns a dict with records and a summary."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    records = [_parse_line(ln, i + 1) for i, ln in enumerate(lines)]
    # Second pass: bot flood. A bot user agent only counts as a flood when
    # the same IP made many bot requests in this file.
    bot_counts = Counter(
        r["ip"] for r in records
        if r["format"] == "access" and r["ip"] and BOT_UA.search(r["detail"])
    )
    for r in records:
        if (
            r["format"] == "access"
            and r["ip"]
            and BOT_UA.search(r["detail"])
            and bot_counts[r["ip"]] >= BOT_FLOOD_MIN_REQUESTS
        ):
            r["problem_type"] = "bot_flood"
    counts = Counter(r["problem_type"] for r in records)
    problems = {k: v for k, v in counts.items() if k not in ("ok",)}
    dominant = max(problems, key=problems.get) if problems else "ok"
    top_urls = Counter(r["url"] for r in records if r["url"]).most_common(10)
    top_ips = Counter(r["ip"] for r in records if r["ip"]).most_common(10)
    formats = Counter(r["format"] for r in records)
    return {
        "total_lines": len(records),
        "records": records,
        "counts": dict(counts),
        "problem_counts": problems,
        "dominant_type": dominant,
        "top_urls": top_urls,
        "top_ips": top_ips,
        "formats": dict(formats),
    }


def plain_summary(result):
    """Plain language summary of what went wrong, for the app."""
    total = result["total_lines"]
    problems = result["problem_counts"]
    if not problems:
        return (
            "Nothing went wrong in this log. All %d lines look normal, no "
            "errors, no slow requests, and no failed logins were found."
            % total
        )
    n_problems = sum(problems.values())
    parts = []
    for ptype, count in sorted(problems.items(), key=lambda kv: -kv[1]):
        parts.append("%s: %d" % (LABELS[ptype], count))
    dominant = result["dominant_type"]
    return (
        "Out of %d log lines, %d show a problem. The biggest problem is "
        "%s, with %d lines. Breakdown, %s."
        % (total, n_problems, LABELS[dominant].lower(), problems[dominant], ", ".join(parts))
    )
