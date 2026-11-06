"""Evaluate the log parser against the 18 generated fixtures.

For each fixture it compares the parser output with the ground truth
JSON written by tests/generate_fixtures.py: dominant problem type and
per-line classification. Writes evaluation/results.json and
evaluation/results.md with the overall accuracy and a per-log table.
Run from the repo root: python3 evaluate.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from logparser import parse_log  # noqa: E402

FIXTURES = os.path.join(HERE, "tests", "fixtures")
OUT_DIR = os.path.join(HERE, "evaluation")


def main():
    rows = []
    total_lines = 0
    correct_lines = 0
    correct_dominant = 0
    fixture_files = sorted(f for f in os.listdir(FIXTURES) if f.endswith(".log"))
    for name in fixture_files:
        with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
            text = fh.read()
        with open(os.path.join(FIXTURES, name + ".json"), encoding="utf-8") as fh:
            truth = json.load(fh)
        result = parse_log(text)
        # True per-line accuracy: ground truth stores one label per line,
        # in file order, so compare each parsed record with its label.
        labels = truth["labels"]
        matched = sum(
            1 for rec, label in zip(result["records"], labels)
            if rec["problem_type"] == label
        )
        total = truth["total_lines"]
        per_line_acc = matched / total if total else 0.0
        dominant_ok = result["dominant_type"] == truth["expected_dominant"]
        correct_dominant += 1 if dominant_ok else 0
        total_lines += total
        correct_lines += matched
        expected = truth["expected_counts"]
        predicted = result["counts"]
        rows.append({
            "file": name,
            "format": truth["format"],
            "lines": total,
            "expected_dominant": truth["expected_dominant"],
            "predicted_dominant": result["dominant_type"],
            "dominant_correct": dominant_ok,
            "per_line_accuracy": round(per_line_acc, 4),
            "expected_counts": expected,
            "predicted_counts": predicted,
        })
    overall_line_acc = correct_lines / total_lines if total_lines else 0.0
    dominant_acc = correct_dominant / len(rows) if rows else 0.0
    summary = {
        "fixtures": len(rows),
        "total_lines": total_lines,
        "correct_lines": correct_lines,
        "overall_per_line_accuracy": round(overall_line_acc, 4),
        "dominant_type_accuracy": round(dominant_acc, 4),
        "dominant_correct": correct_dominant,
        "rows": rows,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    lines = [
        "# Evaluation results",
        "",
        "Generated fixtures only, no real customer logs. "
        "Parser run on %d fixtures, %d lines in total." % (len(rows), total_lines),
        "",
        "- Overall per-line accuracy: %.1f%% (%d of %d lines)"
        % (overall_line_acc * 100, correct_lines, total_lines),
        "- Dominant problem type correct on %d of %d fixtures (%.1f%%)"
        % (correct_dominant, len(rows), dominant_acc * 100),
        "",
        "| File | Format | Lines | Expected dominant | Predicted dominant | Correct | Per-line accuracy |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(
            "| %s | %s | %d | %s | %s | %s | %.1f%% |"
            % (
                r["file"], r["format"], r["lines"], r["expected_dominant"],
                r["predicted_dominant"], "yes" if r["dominant_correct"] else "NO",
                r["per_line_accuracy"] * 100,
            )
        )
    lines.append("")
    lines.append("## Notes")
    if overall_line_acc < 1.0:
        lines.append(
            "Accuracy is below 100 percent. The misses are shown in the "
            "per-log table and in results.json, with expected vs predicted "
            "counts per fixture. Common causes are ambiguous lines that fit "
            "two problem types, for example a 403 that is both an access "
            "denial and a permission error, and warning lines that carry no "
            "clear problem signal."
        )
    else:
        lines.append(
            "All 18 fixtures classified correctly on dominant type and on "
            "per-line counts. This is expected because the fixtures were "
            "generated to match the documented parser rules, so the result "
            "shows the parser works as specified on generated data, not "
            "that it will be perfect on real-world logs."
        )
    lines.append("")
    with open(os.path.join(OUT_DIR, "results.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("fixtures: %d, lines: %d" % (len(rows), total_lines))
    print("overall per-line accuracy: %.1f%%" % (overall_line_acc * 100))
    print("dominant type accuracy: %.1f%% (%d/%d)" % (dominant_acc * 100, correct_dominant, len(rows)))
    for r in rows:
        print("%s: dominant %s, per-line %.1f%%" % (
            r["file"], "OK" if r["dominant_correct"] else "WRONG",
            r["per_line_accuracy"] * 100))


if __name__ == "__main__":
    main()
