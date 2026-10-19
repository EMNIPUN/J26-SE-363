"""Assembles the Code Ownership comprehension dataset.

    python build_dataset.py            writes dataset/ownership_qa.csv and dataset/blind_sheet.json (answers shuffled, ratings removed, for an independent rater)
    python build_dataset.py --merge F  merges an independent rater's ratings (JSON {item_id: rating}) into ownership_qa.csv as `rating_independent`

Inputs: dataset/snippets.csv (real standard-library functions and generated questions), dataset/answers.txt (answers written at rubric levels 1-5) and
dataset/answers_extra.txt (short correct and long weak answers added to break the link between answer length and rating).
"""
import csv
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "dataset"
SEED = 20261019

RUBRIC = """Comprehension rubric (1-5). The rater sees the code, the question, the facts a good answer must contain, and one student answer.
5  Complete and correct: states what the code does in the asked case AND why, specific to this code.
4  Correct on the main point; misses the reason or one detail, or is slightly general.
3  Partly right: gets the gist but is vague, hedges, or misses the key fact, or has one clear mistake.
2  Mostly restates the code line by line (or a general description) without showing understanding of what happens or why; or mostly wrong.
1  Wrong, about a different part of the code, empty of content, or irrelevant."""


def parse_answers(text, out=None):
    out, cur = ({} if out is None else out), None
    for line in text.splitlines():
        if line.startswith("#") and not line.startswith("## "):
            continue
        m = re.match(r"^## (K\d{3})\s*$", line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, {})
        elif cur and (m2 := re.match(r"^([1-5]): (.+)$", line)):
            out[cur].setdefault(int(m2.group(1)), []).append(m2.group(2).strip())
    return out


def rows():
    snippets = list(csv.DictReader(open(DATA / "snippets.csv", encoding="utf-8")))
    answers = parse_answers((DATA / "answers.txt").read_text(encoding="utf-8"))
    parse_answers((DATA / "answers_extra.txt").read_text(encoding="utf-8"), answers)
    out = []
    for s in snippets:
        a = answers.get(s["snippet_id"], {})
        assert sorted(a) == [1, 2, 3, 4, 5], f"{s['snippet_id']}: levels {sorted(a)}"
        for rating, text in ((r, t) for r in (5, 4, 3, 2, 1) for t in a[r]):
            k = len([o for o in out if o["snippet_id"] == s["snippet_id"] and o["rating"] == rating])
            out.append({"item_id": f"{s['snippet_id']}-{rating}{'abc'[k]}", "snippet_id": s["snippet_id"], "source": s["source"], "function": s["function"], "question_type": s["question_type"],
                        "code": s["code"], "question": s["question"], "reference_criteria": s["reference_criteria"], "answer": text, "rating": rating,
                        "score": (rating - 1) / 4, "answer_author": "assistant (Claude)", "rating_source": "written_level"})
    return out


def main():
    data = rows()
    with open(DATA / "ownership_qa.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)
    order = list(range(len(data)))
    random.Random(SEED).shuffle(order)
    blind = [{"blind_id": f"B{n+1:03d}", "item_id": data[i]["item_id"], "function": data[i]["function"], "code": data[i]["code"], "question": data[i]["question"],
              "facts_a_good_answer_contains": json.loads(data[i]["reference_criteria"]), "answer": data[i]["answer"]} for n, i in enumerate(order)]
    sheet = [{k: v for k, v in b.items() if k != "item_id"} for b in blind]
    (DATA / "blind_sheet.json").write_text(json.dumps({"rubric": RUBRIC, "items": sheet}, indent=1, ensure_ascii=False), encoding="utf-8")
    (DATA / "blind_key.json").write_text(json.dumps({b["blind_id"]: b["item_id"] for b in blind}, indent=1), encoding="utf-8")
    print(len(data), "answers for", len({d["snippet_id"] for d in data}), "functions")


def merge(path):
    ratings = json.loads(Path(path).read_text(encoding="utf-8"))
    key = json.loads((DATA / "blind_key.json").read_text(encoding="utf-8"))
    by_item = {key[b]: int(r) for b, r in ratings.items()}
    data = list(csv.DictReader(open(DATA / "ownership_qa.csv", encoding="utf-8")))
    for d in data:
        d["rating_independent"] = by_item.get(d["item_id"], "")
    with open(DATA / "ownership_qa.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)
    print("merged", len(by_item), "independent ratings")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--merge":
        merge(sys.argv[2])
    else:
        main()
