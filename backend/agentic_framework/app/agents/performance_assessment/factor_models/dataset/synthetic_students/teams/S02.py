"""Team S02: Library management (FastAPI + React). Three sprints. Students: steady backend, late frontend,
reviewer who also writes fines logic, a free rider who leaves after sprint 2, and a student with an exam-week dip."""
from _kit import T, Q, S

TEAM = {
    "team": "S02", "domain": "Library management", "stack": "FastAPI and React",
    "sprint_starts": {"S02-S1": "2026-02-09", "S02-S2": "2026-02-23", "S02-S3": "2026-03-09"},
    "edges": [
        ("app/main.py", "app/routers/books.py"), ("app/main.py", "app/routers/loans.py"), ("app/main.py", "app/routers/members.py"), ("app/main.py", "app/db.py"),
        ("app/routers/books.py", "app/schemas.py"), ("app/routers/books.py", "app/models.py"), ("app/routers/books.py", "app/services/search.py"),
        ("app/routers/loans.py", "app/services/loans.py"), ("app/routers/loans.py", "app/schemas.py"), ("app/routers/loans.py", "app/auth.py"),
        ("app/routers/members.py", "app/models.py"), ("app/routers/members.py", "app/schemas.py"), ("app/routers/members.py", "app/auth.py"),
        ("app/services/loans.py", "app/models.py"), ("app/services/loans.py", "app/services/fines.py"), ("app/services/fines.py", "app/models.py"),
        ("app/services/search.py", "app/models.py"), ("app/auth.py", "app/models.py"), ("app/models.py", "app/db.py"),
        ("web/src/App.jsx", "web/src/pages/Catalogue.jsx"), ("web/src/App.jsx", "web/src/pages/BookPage.jsx"), ("web/src/App.jsx", "web/src/pages/MyLoans.jsx"),
        ("web/src/App.jsx", "web/src/pages/Librarian.jsx"), ("web/src/pages/Catalogue.jsx", "web/src/api.js"), ("web/src/pages/BookPage.jsx", "web/src/api.js"),
        ("web/src/pages/MyLoans.jsx", "web/src/api.js"), ("web/src/pages/Librarian.jsx", "web/src/api.js"),
    ],
    "students": {
        "SYN-006": {
            "class": "consistent_deep_contributor", "scenario": "steady backend work all sprint; skips documentation and one edge case each sprint",
            "S02-S1": S(
                [T("T1", "Loan model and checkout endpoint", "A member can borrow an available book for 14 days.",
                   ["POST /loans creates a loan with a due date 14 days ahead", "A book that is already on loan is refused", "Response includes the due date"], 5, 4, "Done", [1, 1, 0], 4,
                   """def checkout(db, member_id, book_id):
    book = db.get(Book, book_id)
    if book.on_loan:
        raise HTTPException(409, "book already on loan")
    loan = Loan(member_id=member_id, book_id=book_id, due=date.today() + timedelta(days=14))
    book.on_loan = True
    db.add(loan); db.commit()
    return loan   # due date is stored but the response schema does not expose it yet"""),
                 T("T2", "Return a book", "Mark a loan as returned and free the book.",
                   ["POST /loans/{id}/return sets returned_at", "The book becomes available again", "Returning twice gives 400"], 3, 3, "Done", [1, 1, 1], 5,
                   """def return_book(db, loan_id):
    loan = db.get(Loan, loan_id)
    if loan.returned_at:
        raise HTTPException(400, "already returned")
    loan.returned_at = datetime.utcnow(); loan.book.on_loan = False
    db.commit(); return loan""")],
                [(0, 10, "loan model", "T1", [("app/models.py", "code", 26, 0)]),
                 (1, 14, "checkout service", "T1", [("app/services/loans.py", "code", 33, 0), ("app/routers/loans.py", "code", 21, 0)]),
                 (2, 11, "refuse books already on loan", "T1", [("app/services/loans.py", "code", 9, 2)]),
                 (3, 15, "schemas for loans", "T1", [("app/schemas.py", "code", 18, 0)]),
                 (4, 10, "return book", "T2", [("app/services/loans.py", "code", 24, 1), ("app/routers/loans.py", "code", 8, 0)]),
                 (6, 16, "tests for checkout and return", "T2", [("tests/test_loans.py", "test", 58, 0)]),
                 (8, 11, "double return guard", "T2", [("app/services/loans.py", "code", 6, 1), ("tests/test_loans.py", "test", 14, 0)]),
                 (9, 14, "fix due date timezone", "T1", [("app/services/loans.py", "code", 4, 3)]),
                 (11, 10, "wire router into main", None, [("app/main.py", "code", 5, 0)])],
                Q("good", 4, "checkout marks the book on loan and stores a due date", "Why is on_loan stored on the book as well as derived from loans?",
                  "Mostly so the catalogue query is fast. But it means two places can disagree if a return fails halfway."),
                0.9, 0.9, prs=[(5, "Loans: checkout and return", True), (12, "Wire loans router", True)]),
            "S02-S2": S(
                [T("T1", "Fine calculation", "Late returns cost 20 rupees per day, capped at the book price.",
                   ["Fine is 20 per overdue day", "Fine never exceeds the book price", "Fine is stored on the loan when it is returned"], 5, 3, "Done", [1, 1, 1], 4,
                   """def fine_for(loan):
    days = max(0, (loan.returned_at.date() - loan.due).days)
    return min(days * 20, loan.book.price)"""),
                 T("T2", "Overdue loans list", "Librarians can see all loans past their due date.",
                   ["GET /loans/overdue returns unreturned loans past due", "Sorted by days overdue", "Only librarians may call it"], 3, 3, "Partially Done", [1, 1, 0], 3,
                   """@router.get("/overdue")
def overdue(db: Session = Depends(get_db)):
    q = db.query(Loan).filter(Loan.returned_at.is_(None), Loan.due < date.today())
    return sorted(q, key=lambda l: l.due)   # role check still missing""")],
                [(0, 10, "fine function", "T1", [("app/services/fines.py", "code", 17, 0)]),
                 (1, 15, "store fine on return", "T1", [("app/services/loans.py", "code", 11, 2), ("app/models.py", "code", 3, 0)]),
                 (3, 11, "fine tests", "T1", [("tests/test_loans.py", "test", 39, 0)]),
                 (4, 16, "cap fine at price", "T1", [("app/services/fines.py", "code", 4, 1), ("tests/test_loans.py", "test", 9, 0)]),
                 (7, 10, "overdue endpoint", "T2", [("app/routers/loans.py", "code", 19, 0)]),
                 (8, 14, "sort overdue", "T2", [("app/routers/loans.py", "code", 4, 1)]),
                 (10, 11, "fix overdue filter for returned loans", "T2", [("app/routers/loans.py", "code", 3, 2)])],
                Q("strong", 5, "fine_for caps the fine at the book price", "What happens to a loan returned before the due date?",
                  "days becomes max(0, negative) = 0, so the fine is 0. I handled that in the max so we never charge a negative fine."),
                0.9, 0.9, prs=[(5, "Fines", True), (11, "Overdue list", True)],
                reviews=[(9, "SYN-010", "COMMENTED", "Query looks fine.", "brief")]),
            "S02-S3": S(
                [T("T1", "Email reminder before due date", "Members receive an email the day before a book is due.",
                   ["A job finds loans due tomorrow", "An email is sent to each member", "A member is not emailed twice"], 5, 4, "Partially Done", [1, 1, 0], 3,
                   """def due_tomorrow(db):
    tomorrow = date.today() + timedelta(days=1)
    return db.query(Loan).filter(Loan.due == tomorrow, Loan.returned_at.is_(None)).all()

def send_reminders(db, mailer):
    for loan in due_tomorrow(db):
        mailer.send(loan.member.email, "Book due tomorrow", loan.book.title)
    # no reminder_sent flag yet, so running the job twice emails twice"""),
                 T("T2", "Member borrowing limit", "A member can have at most five books on loan.",
                   ["Sixth checkout is refused", "Message tells the member the limit", "Returned books do not count"], 3, 2, "Done", [1, 1, 1], 5,
                   """open_loans = db.query(Loan).filter_by(member_id=member_id, returned_at=None).count()
if open_loans >= 5:
    raise HTTPException(409, "limit of 5 books on loan reached")""")],
                [(0, 10, "borrowing limit", "T2", [("app/services/loans.py", "code", 12, 1)]),
                 (1, 15, "limit tests", "T2", [("tests/test_loans.py", "test", 27, 0)]),
                 (3, 11, "reminder query", "T1", [("app/services/loans.py", "code", 22, 0)]),
                 (4, 14, "reminder sender", "T1", [("app/services/fines.py", "code", 19, 0)]),
                 (6, 10, "reminder tests", "T1", [("tests/test_loans.py", "test", 33, 0)]),
                 (9, 16, "move reminders out of fines module", "T1", [("app/services/fines.py", "code", 3, 20), ("app/services/loans.py", "code", 20, 0)]),
                 (11, 11, "readme for running the job", None, [("README.md", "config_or_docs", 21, 0)]),
                 (12, 15, "cleanup", None, [("app/services/loans.py", "code", 4, 7)])],
                Q("good", 4, "send_reminders loops over loans due tomorrow", "What stops a member getting the reminder twice?",
                  "Nothing yet. I know we need a reminder_sent column. I ran out of time."),
                0.85, 0.9, prs=[(5, "Borrowing limit", True), (12, "Reminders", True)],
                reviews=[(8, "SYN-008", "COMMENTED", "Why do the reminders live in fines.py? Both use the loan model but they are different jobs, move the reminder code to its own service.", "substantive")]),
        },
        "SYN-007": {
            "class": "last_minute_rusher", "scenario": "React pages written in the last two days every sprint; works but rough edges",
            "S02-S1": S(
                [T("T1", "Catalogue page with search", "Show all books and filter by title.",
                   ["Lists books from the API", "A search box filters by title", "Shows whether a book is available"], 3, 3, "Done", [1, 1, 1], 4,
                   """export default function Catalogue() {
  const [books, setBooks] = useState([]);
  const [q, setQ] = useState('');
  useEffect(() => { api.get('/books', { params: { q } }).then(r => setBooks(r.data)); }, [q]);
  return <><input value={q} onChange={e => setQ(e.target.value)} />{books.map(b => <li key={b.id}>{b.title} {b.on_loan ? '(on loan)' : ''}</li>)}</>;
}"""),
                 T("T2", "Book detail page", "One book with author, ISBN and a borrow button.",
                   ["Loads one book", "Shows author and ISBN", "Borrow button calls the API and shows the result"], 3, 2, "Partially Done", [1, 1, 0], 2,
                   """export default function BookPage() {
  const { id } = useParams(); const [book, setBook] = useState();
  useEffect(() => { api.get(`/books/${id}`).then(r => setBook(r.data)); }, [id]);
  return book ? <div><h1>{book.title}</h1><p>{book.author} · {book.isbn}</p><button>Borrow</button></div> : null;
}   // the button has no handler yet""")],
                [(11, 21, "catalogue page", "T1", [("web/src/pages/Catalogue.jsx", "code", 74, 0), ("web/src/api.js", "code", 14, 0)]),
                 (12, 14, "search box", "T1", [("web/src/pages/Catalogue.jsx", "code", 22, 6)]),
                 (12, 23, "book page", "T2", [("web/src/pages/BookPage.jsx", "code", 66, 0)]),
                 (13, 12, "routes", "T2", [("web/src/App.jsx", "code", 28, 0)]),
                 (13, 20, "availability label", "T1", [("web/src/pages/Catalogue.jsx", "code", 9, 2)]),
                 (13, 23, "styles", None, [("web/src/pages/BookPage.jsx", "code", 24, 4), ("web/src/App.jsx", "code", 11, 3)])],
                Q("partial", 3, "Catalogue refetches when the search text changes", "Why is q in the dependency array of useEffect?",
                  "So it searches again when the text changes. I think it fires on every key press which is a bit much."),
                0.75, 0.9, prs=[(13, "Catalogue and book page", True)]),
            "S02-S2": S(
                [T("T1", "My loans page", "Members see their current loans and fines.",
                   ["Shows current loans with due dates", "Shows the fine on late loans", "Return button"], 5, 3, "Done", [1, 0, 1], 3,
                   """export default function MyLoans() {
  const [loans, setLoans] = useState([]);
  useEffect(() => { api.get('/loans/mine').then(r => setLoans(r.data)); }, []);
  return loans.map(l => <li key={l.id}>{l.title} due {l.due} <button onClick={() => api.post(`/loans/${l.id}/return`)}>Return</button></li>);
}"""),
                 T("T2", "Borrow button works", "Finish the borrow button on the book page.",
                   ["Button calls POST /loans", "Shows error when the book is on loan"], 2, 2, "Done", [1, 1], 4,
                   """const borrow = async () => {
  try { await api.post('/loans', { book_id: book.id }); setMsg('Borrowed'); }
  catch (e) { setMsg(e.response?.data?.detail || 'Failed'); }
};""", carried="S02-S1-SYN-007-T2")],
                [(10, 22, "borrow button handler", "T2", [("web/src/pages/BookPage.jsx", "code", 31, 6)]),
                 (12, 23, "my loans page", "T1", [("web/src/pages/MyLoans.jsx", "code", 58, 0)]),
                 (13, 11, "return button", "T1", [("web/src/pages/MyLoans.jsx", "code", 12, 2)]),
                 (13, 21, "route and nav", "T1", [("web/src/App.jsx", "code", 13, 1)])],
                Q("good", 4, "borrow shows the API's detail message", "Why show e.response.data.detail instead of a fixed message?",
                  "Because the backend sends specific reasons like 'book already on loan', and the user needs to know which one."),
                0.8, 0.9, prs=[(13, "Borrow and my loans", True)]),
            "S02-S3": S(
                [T("T1", "Librarian page: add and edit books", "Librarians add a book and edit its details.",
                   ["Form to add a book", "Edit existing book", "Validation of ISBN length", "Only shown to librarians"], 8, 5, "Partially Done", [1, 1, 0, 0], 3,
                   """export default function Librarian() {
  const [form, setForm] = useState({ title: '', author: '', isbn: '' });
  const save = async (e) => { e.preventDefault(); await api.post('/books', form); setForm({ title: '', author: '', isbn: '' }); };
  return <form onSubmit={save}>{Object.keys(form).map(k => <input key={k} placeholder={k} value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })} />)}<button>Add</button></form>;
}   // edit and validation not done""")],
                [(11, 20, "librarian form", "T1", [("web/src/pages/Librarian.jsx", "code", 91, 0)]),
                 (12, 22, "post new book", "T1", [("web/src/pages/Librarian.jsx", "code", 18, 4), ("web/src/api.js", "code", 6, 0)]),
                 (13, 17, "route for librarian page", "T1", [("web/src/App.jsx", "code", 8, 0)]),
                 (13, 23, "style pass", None, [("web/src/pages/Librarian.jsx", "code", 20, 8)])],
                Q("partial", 3, "Librarian form keeps fields in one state object", "How does the form update only one field?",
                  "It spreads the old form and replaces the key that changed."),
                0.8, 0.9, prs=[(13, "Librarian page", True)],
                reviews=[(12, "SYN-010", "COMMENTED", "ok", "approval")]),
        },
        "SYN-008": {
            "class": "reviewer_coordinator", "scenario": "reviews and merges most pull requests; writes small, careful pieces of code; reviews get deeper over time",
            "S02-S1": S(
                [T("T1", "Project setup and CI", "Repository, linting and a test workflow.",
                   ["README explains how to run backend and web", "Tests run on every pull request", "Lint step fails the build on errors"], 3, 3, "Done", [1, 1, 0], 3,
                   """# .github/workflows/test.yml
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt && pytest""")],
                [(0, 9, "repo setup and readme", "T1", [("README.md", "config_or_docs", 44, 0)]),
                 (1, 10, "github actions workflow", "T1", [(".github/workflows/test.yml", "config_or_docs", 18, 0)]),
                 (5, 16, "db session helper", None, [("app/db.py", "code", 22, 0)])],
                Q("good", 4, "db.py creates the engine and a session per request", "Why a session per request?",
                  "So requests do not share uncommitted state, and the session is closed at the end of each request."),
                0.95, 0.9, mfo=2,
                reviews=[(5, "SYN-006", "APPROVED", "The 409 for a book already on loan is right. One problem: on_loan is set before the commit, so if the commit fails the in-memory book says on loan but the row does not. Do the update inside the same transaction and roll back on error.", "substantive"),
                         (12, "SYN-007", "COMMENTED", "The borrow button has no click handler so nothing happens. Add it, and show the message from the API.", "brief"),
                         (12, "SYN-010", "APPROVED", "The search pattern is built from the raw text, so typing % or _ acts as a wildcard and lists every book. Escape those characters before building the like pattern.", "substantive")],
                comments=[(6, "SYN-006", "Good point about the rollback, I will fix it. @SYN-008 can you re-check?", 1, 1)]),
            "S02-S2": S(
                [T("T1", "Fines report for librarians", "Totals of unpaid fines per member.",
                   ["Endpoint lists members with unpaid fines", "Total per member", "Mark a fine as paid"], 5, 3, "Done", [1, 1, 1], 4,
                   """@router.get("/fines")
def fines(db: Session = Depends(get_db)):
    rows = db.query(Loan.member_id, func.sum(Loan.fine)).filter(Loan.fine_paid.is_(False), Loan.fine > 0).group_by(Loan.member_id).all()
    return [{"member_id": m, "total": t} for m, t in rows]""")],
                [(2, 11, "fines report query", "T1", [("app/routers/members.py", "code", 24, 0)]),
                 (4, 15, "mark fine as paid", "T1", [("app/routers/members.py", "code", 15, 0), ("app/models.py", "code", 2, 0)]),
                 (8, 10, "tests for fines report", "T1", [("tests/test_loans.py", "test", 31, 0)])],
                Q("strong", 5, "fines groups unpaid fines by member", "Why filter on fine > 0 and fine_paid false?",
                  "Loans with no fine would add zero rows to the group, and paid ones should not appear in what the member still owes."),
                0.95, 0.9, mfo=3,
                reviews=[(2, "SYN-006", "COMMENTED", "Your fine_for uses returned_at, but a loan that is still out never gets a fine until it is returned. The overdue page and the report will disagree. Decide if a fine accrues while a book is out.", "substantive"),
                         (4, "SYN-006", "APPROVED", "The cap at the book price matches the requirement, nice test for the boundary.", "substantive"),
                         (9, "SYN-007", "CHANGES_REQUESTED", "My loans page calls the return endpoint without awaiting it or refreshing the list, so the row stays after you return a book. Await the call and reload.", "substantive"),
                         (10, "SYN-010", "COMMENTED", "Please add a test for an empty search string.", "brief"),
                         (11, "SYN-006", "APPROVED", "looks good", "approval")],
                comments=[(5, "SYN-006", "I think a fine should accrue while it is out, let us ask the lecturer. @SYN-006", 1, 1), (9, "SYN-007", "Thanks, will fix.", 1, 0)]),
            "S02-S3": S(
                [T("T1", "Deploy to a test server", "Backend and web on a small server for the demo.",
                   ["Backend runs with docker compose", "Web build served by nginx", "Environment variables documented"], 5, 4, "Done", [1, 1, 1], 4,
                   """services:
  api:
    build: .
    environment: [DATABASE_URL, SECRET_KEY]
    ports: ["8000:8000"]
  web:
    image: nginx:alpine
    volumes: ["./web/dist:/usr/share/nginx/html:ro"]""")],
                [(1, 10, "dockerfile and compose", "T1", [("Dockerfile", "config_or_docs", 21, 0), ("docker-compose.yml", "config_or_docs", 26, 0)]),
                 (2, 15, "nginx config", "T1", [("nginx.conf", "config_or_docs", 19, 0)]),
                 (6, 11, "document environment variables", "T1", [("README.md", "config_or_docs", 28, 4)])],
                Q("partial", 3, "docker-compose starts the API and nginx", "What does the volume on the web service do?",
                  "It puts the built React files in the folder nginx serves from."),
                0.95, 0.85, mfo=4,
                reviews=[(3, "SYN-006", "COMMENTED", "send_reminders mixes the query and the mail call, so the test has to fake the mailer to check which loans are picked. Pass the loans in, or split the two.", "substantive"),
                         (4, "SYN-006", "APPROVED", "The 409 message includes the limit, which matches the acceptance criteria. Test covers returned books not counting.", "substantive"),
                         (9, "SYN-010", "CHANGES_REQUESTED", "Search interpolates the text into the SQL string. Use a bound parameter, this is injectable. Add a test with a quote in the title.", "substantive"),
                         (11, "SYN-007", "COMMENTED", "The librarian page shows to every user. At least hide the link when the role is not librarian, the real check must also be on the API.", "substantive"),
                         (12, "SYN-007", "APPROVED", "ok", "approval")],
                comments=[(3, "SYN-006", "Yes, I'll split it before merge. @SYN-006", 1, 1), (10, "SYN-010", "That one is serious, thanks. @SYN-010 please push the fix today.", 1, 1)]),
        },
        "SYN-009": {
            "class": "free_rider", "scenario": "no commits in sprint 1, a trivial change in sprint 2, then leaves the team",
            "S02-S1": S(
                [T("T1", "Member registration endpoint", "Register a member with name and email.",
                   ["POST /members stores a member", "Email must be unique", "Returns 201"], 3, 2, "To Do", [0, 0, 0], 1)],
                [], Q("weak", 1, "(no code this sprint)", "Describe how a member is stored.", "In the database. I did not get to it this sprint."), 0.0, 0.0),
            "S02-S2": S(
                [T("T1", "Member registration endpoint", "Register a member with name and email.",
                   ["POST /members stores a member", "Email must be unique", "Returns 201"], 3, 2, "Partially Done", [1, 0, 0], 2,
                   """@router.post("/members")
def register(m: MemberIn, db: Session = Depends(get_db)):
    member = Member(name=m.name, email=m.email)
    db.add(member); db.commit()
    return member   # no uniqueness check, returns 200""", carried="S02-S1-SYN-009-T1")],
                [(12, 22, "member endpoint", "T1", [("app/routers/members.py", "code", 17, 0)]),
                 (13, 20, "fix typo in schema", None, [("app/schemas.py", "code", 1, 1)])],
                Q("weak", 2, "register stores name and email", "What happens if two members use the same email?",
                  "It would save both, I think. I did not add a check."), 0.7, 0.3, prs=[(13, "Member endpoint", False)]),
        },
        "SYN-010": {
            "class": "no_specific_pattern", "scenario": "strong first sprint, exam-week dip in sprint 2, middling recovery in sprint 3",
            "S02-S1": S(
                [T("T1", "Book CRUD API", "Create, list, get, update and delete books.",
                   ["CRUD endpoints for books", "Duplicate ISBN rejected", "List supports paging"], 5, 4, "Done", [1, 1, 0], 4,
                   """@router.post("/books", status_code=201)
def add(b: BookIn, db: Session = Depends(get_db)):
    if db.query(Book).filter_by(isbn=b.isbn).first():
        raise HTTPException(409, "isbn exists")
    book = Book(**b.dict()); db.add(book); db.commit(); return book"""),
                 T("T2", "Search books", "Search by title or author.",
                   ["q parameter searches title and author", "Case insensitive", "Escapes special characters"], 3, 3, "Done", [1, 1, 0], 3,
                   """def search(db, q):
    like = f"%{q}%"
    return db.query(Book).filter(or_(Book.title.ilike(like), Book.author.ilike(like))).all()""")],
                [(0, 14, "book model and schema", "T1", [("app/models.py", "code", 18, 0), ("app/schemas.py", "code", 15, 0)]),
                 (1, 10, "book crud routes", "T1", [("app/routers/books.py", "code", 52, 0)]),
                 (2, 15, "isbn unique check", "T1", [("app/routers/books.py", "code", 7, 0)]),
                 (4, 11, "paging", "T1", [("app/routers/books.py", "code", 12, 3)]),
                 (5, 16, "search service", "T2", [("app/services/search.py", "code", 20, 0)]),
                 (7, 10, "search route", "T2", [("app/routers/books.py", "code", 9, 0)]),
                 (8, 14, "search tests", "T2", [("tests/test_books.py", "test", 34, 0)]),
                 (10, 11, "fix update route", "T1", [("app/routers/books.py", "code", 6, 4)])],
                Q("good", 4, "search builds an ilike pattern for title and author", "What is the problem with building the pattern as f\"%{q}%\"?",
                  "If q contains % or _ they act as wildcards. I should escape them."),
                0.85, 0.95, prs=[(6, "Books API", True), (11, "Search", True)]),
            "S02-S2": S(
                [T("T1", "Book availability endpoint", "Show how many copies are available.",
                   ["GET /books/{id}/availability", "Counts copies not on loan"], 3, 2, "Partially Done", [1, 0], 2,
                   """@router.get("/books/{id}/availability")
def availability(id: int, db: Session = Depends(get_db)):
    return {"available": 1}   # placeholder until copies are modelled""")],
                [(9, 23, "availability placeholder", "T1", [("app/routers/books.py", "code", 8, 0)])],
                Q("partial", 3, "availability returns a placeholder", "Why does availability return 1?",
                  "It is a placeholder. We never modelled several copies of a book."), 0.9, 0.95, prs=[(10, "Availability placeholder", True)]),
            "S02-S3": S(
                [T("T1", "Reservation queue", "Members can reserve a book that is on loan.",
                   ["POST /reservations adds a member to the queue", "First in queue is notified on return", "A member cannot reserve twice"], 5, 4, "Partially Done", [1, 0, 1], 3,
                   """def reserve(db, member_id, book_id):
    if db.query(Reservation).filter_by(member_id=member_id, book_id=book_id).first():
        raise HTTPException(409, "already reserved")
    db.add(Reservation(member_id=member_id, book_id=book_id, created=datetime.utcnow())); db.commit()""")],
                [(2, 11, "reservation model", "T1", [("app/models.py", "code", 14, 0)]),
                 (4, 15, "reserve endpoint", "T1", [("app/routers/books.py", "code", 23, 0)]),
                 (7, 10, "no duplicate reservations", "T1", [("app/routers/books.py", "code", 8, 1)]),
                 (9, 16, "reservation tests", "T1", [("tests/test_books.py", "test", 29, 0)]),
                 (12, 14, "escape like wildcards", None, [("app/services/search.py", "code", 6, 2)])],
                Q("good", 4, "reserve rejects a second reservation by the same member", "How is the queue order decided?",
                  "By created time. The notify on return is not written."), 0.85, 0.9,
                prs=[(10, "Reservations", True)]),
        },
    },
}
