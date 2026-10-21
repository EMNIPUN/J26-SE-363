# Reference ratings

`reference_ratings.csv` holds a rubric rating for every student-sprint record that has no rating in
`ground_truth/human_ratings.csv`: 124 real records and 175 simulated records (299 rows).

## Who rated

All rows have `rater_id = assistant` and `rater_type = assistant (rubric)`. They were produced by the AI assistant (Claude)
reading an evidence card per record (`scripts/14_evidence_cards.py`) and scoring it against the rubric in
`ground_truth/EVALUATION_FORM.md`. **No human rated these records.** The 20 ratings in `ground_truth/human_ratings.csv`
were also produced by the assistant, in the same way, so no rating in this project comes from a person.

Use them as a rubric-based reference set for development and training. Do not describe them as human judgement or as an
independent ground truth in the thesis or the presentation.

## Known limits

- The simulated records were written by the same assistant that rated them, so for those rows the rating and the data share
  an author. Agreement on simulated records says little about how the models behave on real students.
- The evidence cards hold the raw evidence only (commits, tasks, reviews, comments, code survival, a code question). They hold
  no engineered feature values, and for simulated students nothing about how they were generated.
- Ratings were written in batches in one pass, so there was no second rater and no agreement figure.

## Columns

`record_id, rater_id, rater_type`, the 24 criteria in `columns.txt` (1–5 each), `BP_pattern` (one of six behaviour patterns),
`overall_mark` (0–100) and a short `comment`.

Checks that passed on 299 rows: no duplicate ids, every value in 1–5, every expected real and simulated record present.
