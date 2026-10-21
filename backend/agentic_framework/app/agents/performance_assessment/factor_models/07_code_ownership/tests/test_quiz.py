"""Run from factor_models/:  python -m unittest discover -s 07_code_ownership/tests

Question generation (phase 1): deterministic, structural for Python, general for other languages, nothing when there is nothing worth asking about.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE.parents[1] / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


Q = load("t_ko_quiz", "quiz.py")
QS = load("t_ko_questions", "questions.py")

CART = '''
def cart_total(items, discount):
    """Total price of the cart after the discount."""
    # reject nonsense before doing any work
    if discount < 0:
        raise ValueError("discount must not be negative")
    total = 0
    for item in items:
        if item["qty"] <= 0:
            continue
        total += item["price"] * item["qty"]
    total = total - total * discount
    return round(total, 2)


def other_logic(rows, key):
    out = {}
    for row in rows:
        if key not in row:
            continue
        out.setdefault(row[key], []).append(row)
    try:
        first = next(iter(out))
    except StopIteration:
        return {}
    return {first: out[first], "n": len(out)}
'''

JS = '''
export function computeTotal(items, discount) {
  let total = 0;
  for (const item of items) {
    if (!item.price) { continue; }
    total += item.price * item.qty;
  }
  if (discount > 0) {
    total = total - total * discount;
  }
  const tax = total * 0.08;
  return Math.round((total + tax) * 100) / 100;
}
'''


class Generate(unittest.TestCase):
    def test_python_gets_a_structural_question_with_facts(self):
        q = Q.generate([{"path": "shop/cart.py", "text": CART}], "STU-001", "T01-S1")
        self.assertEqual(q["ast_metadata"]["language"], "python")
        self.assertIn(q["question_type"], QS.QUESTION_TYPES)
        self.assertTrue(q["facts"]["params"] if "params" in q["facts"] else q["facts"]["name"])
        self.assertTrue(q["reference_criteria"])
        self.assertIn(q["ast_metadata"]["name"], q["question"])

    def test_the_shown_code_has_no_docstring_or_comment_lines(self):
        q = Q.generate([{"path": "shop/cart.py", "text": CART}], "STU-001", "T01-S1", salt="a")
        for _ in range(3):
            if q["ast_metadata"]["name"] == "cart_total":
                break
            q = Q.generate([{"path": "shop/cart.py", "text": CART}], "STU-00" + str(_ + 2), "T01-S1")
        self.assertNotIn("Total price of the cart", q["code_snippet"])
        self.assertNotIn("reject nonsense", q["code_snippet"])

    def test_same_student_and_sprint_always_get_the_same_quiz(self):
        a = Q.generate([{"path": "shop/cart.py", "text": CART}], "STU-007", "T02-S1")
        b = Q.generate([{"path": "shop/cart.py", "text": CART}], "STU-007", "T02-S1")
        self.assertEqual(a, b)

    def test_different_students_can_get_different_questions(self):
        qs = {Q.generate([{"path": "shop/cart.py", "text": CART}], f"STU-{i:03d}", "T01-S1")["question"] for i in range(30)}
        self.assertGreater(len(qs), 1)

    def test_other_languages_get_the_general_question_with_a_warning(self):
        q = Q.generate([{"path": "src/cart.js", "text": JS}], "STU-001", "T01-S1")
        self.assertEqual(q["question_type"], "purpose")
        self.assertEqual(q["ast_metadata"]["language"], "other")
        self.assertIn("computeTotal", q["question"])
        self.assertTrue(q["warnings"])

    def test_no_function_worth_asking_about_gives_none(self):
        self.assertIsNone(Q.generate([{"path": "a.py", "text": "x = 1\n\ndef get_x(self):\n    return self.x\n"}], "s", "t"))
        self.assertIsNone(Q.generate([], "s", "t"))

    def test_exception_constructors_are_not_listed_as_calls(self):
        import ast
        node = next(n for n in ast.walk(ast.parse(CART)) if isinstance(n, ast.FunctionDef) and n.name == "cart_total")
        self.assertNotIn("ValueError", QS.facts(node)["calls"])
        self.assertEqual(QS.facts(node)["guards"][0]["raises"], "ValueError")


JS_SAMPLE = r'''
export const createCert = async (req, res) => {
  const { name, hotel } = req.body;
  if (!name) {
    return res.status(400).json({ error: 'name' });
  }
  const cert = await Cert.create({
    name,
    hotel,
  });
  await log(cert);
  res.json(cert);
};
const multi = async (
  a,
  b
) => {
  const x = a + b;
  const y = x * 2;
  const z = y - 1;
  const w = z / 3;
  console.log(w);
  await save(w);
  return w;
};
class Svc {
  async renew(
    id,
    opts
  ) {
    const c = await this.repo.find(id);
    if (!c) { throw new Error('x'); }
    c.expires = addYears(c.expires, 1);
    c.history.push('renewed');
    await c.save();
    return c;
  }
}
'''


class TestBatchOfQuestions(unittest.TestCase):
    def test_javascript_functions_are_found_whatever_their_form(self):
        names = [c["name"] for c in Q.cleaning.snippet_candidates("src/a.js", JS_SAMPLE)]
        self.assertEqual(names, ["createCert", "multi", "renew"])  # arrow functions, a header split over lines and a class method; never an `if`

    def test_no_question_is_about_a_keyword(self):
        for q in Q.generate_many([{"path": "src/a.js", "text": JS_SAMPLE}], "s", "sp", 10):
            self.assertNotRegex(q["question"], r"what does (if|for|while|switch|catch) ")

    def test_runs_of_code_fill_up_the_batch_when_there_are_too_few_functions(self):
        body = "\n".join(f"const v{i} = compute({i});\nlog(v{i});" for i in range(60))
        qs = Q.generate_many([{"path": "src/b.js", "text": body}], "s", "sp", 10)
        self.assertGreaterEqual(len(qs), 5)
        self.assertEqual(len({q["code_snippet"] for q in qs}), len(qs))

    def test_a_batch_has_distinct_questions_up_to_the_count(self):
        files = [{"path": f"src/f{i}.js", "text": JS_SAMPLE.replace("createCert", f"createCert{i}").replace("multi", f"multi{i}").replace("renew", f"renew{i}")} for i in range(4)]
        qs = Q.generate_many(files, "s", "sp", 10)
        self.assertEqual(len(qs), 10)


if __name__ == "__main__":
    unittest.main()
