"""Team S05: Online quiz platform (Django). Four sprints. The team commits straight to main in sprints 1-2 (no pull
requests, so no review data) and adopts pull requests in sprint 3. Students: late rusher, two-burst worker,
coordinator who reviews once PRs exist, a free rider with a pasted-template commit, and a steady but small contributor."""
from _kit import T, Q, S

TEAM = {
    "team": "S05", "domain": "Online quiz platform", "stack": "Django",
    "sprint_starts": {"S05-S1": "2026-01-19", "S05-S2": "2026-02-02", "S05-S3": "2026-02-16", "S05-S4": "2026-03-02"},
    "edges": [
        ("quiz/urls.py", "quiz/views.py"), ("quiz/views.py", "quiz/models.py"), ("quiz/views.py", "quiz/forms.py"), ("quiz/views.py", "quiz/scoring.py"),
        ("quiz/views.py", "quiz/leaderboard.py"), ("quiz/views.py", "quiz/templates/quiz/take.html"), ("quiz/views.py", "quiz/templates/quiz/results.html"),
        ("quiz/views.py", "quiz/templates/quiz/dashboard.html"), ("quiz/forms.py", "quiz/models.py"), ("quiz/scoring.py", "quiz/models.py"),
        ("quiz/leaderboard.py", "quiz/models.py"), ("quiz/models.py", "accounts/models.py"), ("accounts/views.py", "accounts/models.py"),
        ("accounts/urls.py", "accounts/views.py"), ("quiz/admin.py", "quiz/models.py"), ("quiz/timer.py", "quiz/models.py"), ("quiz/views.py", "quiz/timer.py"),
    ],
    "students": {
        "SYN-021": {
            "class": "last_minute_rusher", "scenario": "scoring and views written in the last two or three days; gets a bit earlier by sprint 4 but still back-loaded",
            "S05-S1": S(
                [T("T1", "Question and quiz models", "Quizzes have questions with several options and one correct answer.",
                   ["Quiz with title and time limit", "Question with text and options", "Exactly one correct option", "Admin can edit them"], 5, 4, "Done", [1, 1, 0, 1], 3,
                   """class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)   # nothing stops two correct options"""),
                 T("T2", "Take a quiz page", "Show one question at a time and record the answers.",
                   ["Page shows the question and its options", "Answer saved on submit", "Moves to the next question"], 5, 3, "Partially Done", [1, 1, 0], 3,
                   """def take(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    q = quiz.questions.all()[int(request.GET.get('n', 0))]
    return render(request, 'quiz/take.html', {'quiz': quiz, 'q': q})   # POST handling not finished""")],
                [(11, 21, "quiz and question models", "T1", [("quiz/models.py", "code", 52, 0)]),
                 (12, 14, "admin registration", "T1", [("quiz/admin.py", "code", 17, 0)]),
                 (12, 22, "take view", "T2", [("quiz/views.py", "code", 38, 0), ("quiz/templates/quiz/take.html", "code", 46, 0)]),
                 (13, 12, "urls", "T2", [("quiz/urls.py", "code", 12, 0)]),
                 (13, 20, "template tweaks", "T2", [("quiz/templates/quiz/take.html", "code", 21, 9)])],
                Q("partial", 3, "take picks the question by the n query parameter", "What happens if n is past the last question?",
                  "I think it errors, an IndexError. I did not check."), 0.8, 0.9),
            "S05-S2": S(
                [T("T1", "Scoring", "Score a finished attempt: one point per correct answer.",
                   ["Score counts correct answers", "Unanswered questions score zero", "Result stored with the attempt"], 5, 3, "Done", [1, 1, 1], 4,
                   """def score(attempt):
    correct = Option.objects.filter(question__quiz=attempt.quiz, is_correct=True).values_list('id', flat=True)
    picked = attempt.answers.values_list('option_id', flat=True)
    return len(set(correct) & set(picked))"""),
                 T("T2", "Results page", "Show the score and which answers were wrong.",
                   ["Score and percentage", "List wrong answers with the correct one", "Link to retake"], 5, 3, "Partially Done", [1, 0, 1], 3,
                   """def results(request, attempt_id):
    a = get_object_or_404(Attempt, pk=attempt_id)
    return render(request, 'quiz/results.html', {'score': score(a), 'total': a.quiz.questions.count()})""")],
                [(10, 22, "scoring function", "T1", [("quiz/scoring.py", "code", 31, 0)]),
                 (11, 13, "store result on attempt", "T1", [("quiz/models.py", "code", 14, 0)]),
                 (12, 21, "scoring tests", "T1", [("quiz/tests/test_scoring.py", "test", 44, 0)]),
                 (13, 11, "results view", "T2", [("quiz/views.py", "code", 27, 0), ("quiz/templates/quiz/results.html", "code", 39, 0)]),
                 (13, 22, "retake link", "T2", [("quiz/templates/quiz/results.html", "code", 6, 0)])],
                Q("good", 4, "score intersects correct option ids with picked ids", "Does a question with two correct options give two points?",
                  "Yes, each correct option picked adds a point, which is not what the requirement says for multiple choice. It was written for single answer."), 0.85, 0.9),
            "S05-S3": S(
                [T("T1", "Quiz timer", "A quiz ends automatically when the time limit is up.",
                   ["Timer shown on the page", "Server rejects answers after the limit", "Attempt is submitted automatically"], 8, 4, "Partially Done", [1, 1, 0], 3,
                   """def expired(attempt):
    return timezone.now() > attempt.started_at + timedelta(minutes=attempt.quiz.time_limit)
# view: if expired(attempt): return HttpResponseForbidden('time is up')   # no automatic submit""")],
                [(11, 20, "timer helper", "T1", [("quiz/timer.py", "code", 18, 0)]),
                 (12, 15, "reject late answers", "T1", [("quiz/views.py", "code", 14, 2)]),
                 (12, 23, "countdown in template", "T1", [("quiz/templates/quiz/take.html", "code", 28, 3)]),
                 (13, 19, "timer tests", "T1", [("quiz/tests/test_timer.py", "test", 26, 0)])],
                Q("good", 4, "expired compares now with started_at plus the limit", "Why is the check on the server too and not only in the browser countdown?",
                  "A student can change the browser countdown. The server check is the one that counts."),
                0.9, 0.9, prs=[(13, "Quiz timer", True)]),
            "S05-S4": S(
                [T("T1", "Leaderboard", "Top ten scores per quiz.",
                   ["Top ten attempts by score", "Ties broken by time taken", "Only the best attempt per student"], 5, 3, "Done", [1, 1, 0], 4,
                   """def top(quiz, n=10):
    return (Attempt.objects.filter(quiz=quiz, finished=True)
            .order_by('-score', 'duration')[:n])   # a student with three attempts can fill the board"""),
                 T("T2", "Dashboard for students", "A student sees their attempts and averages.",
                   ["List of attempts", "Average score", "Link to each result"], 3, 3, "Done", [1, 1, 1], 4,
                   """def dashboard(request):
    attempts = Attempt.objects.filter(student=request.user, finished=True)
    return render(request, 'quiz/dashboard.html', {'attempts': attempts, 'avg': attempts.aggregate(Avg('score'))['score__avg']})""")],
                [(7, 22, "leaderboard query", "T1", [("quiz/leaderboard.py", "code", 24, 0)]),
                 (9, 14, "leaderboard view", "T1", [("quiz/views.py", "code", 15, 0)]),
                 (11, 21, "dashboard view and template", "T2", [("quiz/views.py", "code", 17, 0), ("quiz/templates/quiz/dashboard.html", "code", 41, 0)]),
                 (12, 11, "leaderboard tests", "T1", [("quiz/tests/test_leaderboard.py", "test", 37, 0)]),
                 (13, 17, "fix duration ordering", "T1", [("quiz/leaderboard.py", "code", 3, 2)])],
                Q("good", 4, "top orders by score descending then duration", "How do ties get broken?",
                  "By the shorter duration, that is the second order_by key."),
                0.9, 0.9, prs=[(10, "Leaderboard", True), (13, "Dashboard", True)],
                reviews=[(12, "SYN-023", "APPROVED", "ok", "approval")]),
        },
        "SYN-022": {
            "class": "burst_worker", "scenario": "bursts at the start and end of each sprint with a quiet middle; clean work in each burst",
            "S05-S1": S(
                [T("T1", "Registration and login", "Students and teachers register and log in.",
                   ["Register with email and password", "Role teacher or student", "Login and logout", "Password rules enforced"], 8, 5, "Done", [1, 1, 1, 0], 4,
                   """class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[('teacher', 'Teacher'), ('student', 'Student')])""")],
                [(0, 10, "user profile model", "T1", [("accounts/models.py", "code", 24, 0)]),
                 (0, 15, "registration view", "T1", [("accounts/views.py", "code", 47, 0)]),
                 (1, 11, "login and logout", "T1", [("accounts/views.py", "code", 22, 0), ("accounts/urls.py", "code", 11, 0)]),
                 (1, 18, "role choice", "T1", [("accounts/views.py", "code", 9, 2)]),
                 (11, 10, "fix redirect after login", "T1", [("accounts/views.py", "code", 5, 3)]),
                 (12, 15, "tests", "T1", [("accounts/tests/test_auth.py", "test", 49, 0)])],
                Q("good", 4, "Profile extends the user with a role", "Why a OneToOneField to User?",
                  "Each user has exactly one profile, and Django's User model stays untouched."), 0.9, 0.9),
            "S05-S2": S(
                [T("T1", "Teacher quiz editor", "Teachers create a quiz with questions in the web UI.",
                   ["Form to create a quiz", "Add questions and options", "Edit and delete", "Only the owner can edit"], 8, 5, "Done", [1, 1, 1, 0], 4,
                   """class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'time_limit']
QuestionFormSet = inlineformset_factory(Quiz, Question, fields=['text'], extra=3, can_delete=True)""")],
                [(1, 10, "quiz form", "T1", [("quiz/forms.py", "code", 33, 0)]),
                 (1, 16, "create view", "T1", [("quiz/views.py", "code", 42, 0)]),
                 (2, 12, "formset for questions", "T1", [("quiz/forms.py", "code", 21, 0), ("quiz/templates/quiz/dashboard.html", "code", 58, 0)]),
                 (3, 19, "edit and delete", "T1", [("quiz/views.py", "code", 31, 6)]),
                 (11, 11, "show only my quizzes", "T1", [("quiz/views.py", "code", 6, 2)]),
                 (12, 16, "form tests", "T1", [("quiz/tests/test_forms.py", "test", 35, 0)])],
                Q("good", 4, "inlineformset_factory builds a set of question forms for a quiz", "Why extra=3?",
                  "It shows three empty question forms to fill in so the teacher does not have to click add each time."), 0.85, 0.9),
            "S05-S3": S(
                [T("T1", "Import questions from CSV", "Teachers upload a CSV to add many questions.",
                   ["Upload a CSV file", "Rows become questions with options", "Errors reported per row", "Large files do not time out"], 8, 5, "Partially Done", [1, 1, 1, 0], 4,
                   """def import_rows(quiz, rows):
    errors = []
    for i, row in enumerate(rows, start=2):
        try:
            q = Question.objects.create(quiz=quiz, text=row['question'])
            for k in 'abcd':
                Option.objects.create(question=q, text=row[k], is_correct=(row['answer'] == k))
        except KeyError as e:
            errors.append(f'row {i}: missing {e}')
    return errors""")],
                [(0, 10, "csv import function", "T1", [("quiz/forms.py", "code", 44, 0)]),
                 (1, 15, "upload view", "T1", [("quiz/views.py", "code", 34, 0)]),
                 (1, 21, "error report per row", "T1", [("quiz/forms.py", "code", 13, 2)]),
                 (11, 10, "import tests", "T1", [("quiz/tests/test_import.py", "test", 41, 0)]),
                 (12, 14, "wrap import in transaction", "T1", [("quiz/forms.py", "code", 6, 2)])],
                Q("good", 4, "import_rows collects errors per row", "Why enumerate from start=2?",
                  "Row 1 is the header, so the first data row is line 2 in the CSV. It makes the message match the file."),
                0.9, 0.9, prs=[(2, "CSV import", True), (13, "Import tests", True)]),
            "S05-S4": S(
                [T("T1", "Randomise question order", "Each attempt shows questions in a random order.",
                   ["Order differs per attempt", "Same order if the page reloads", "Options shuffled too"], 5, 3, "Partially Done", [1, 1, 0], 3,
                   """def order_for(attempt):
    rng = random.Random(attempt.id)
    ids = list(attempt.quiz.questions.values_list('id', flat=True))
    rng.shuffle(ids)
    return ids   # options not shuffled""")],
                [(0, 11, "seeded shuffle per attempt", "T1", [("quiz/views.py", "code", 19, 2)]),
                 (1, 17, "tests for stable order", "T1", [("quiz/tests/test_order.py", "test", 27, 0)]),
                 (11, 12, "use order in take view", "T1", [("quiz/views.py", "code", 8, 3)])],
                Q("good", 4, "order_for seeds the random generator with the attempt id", "Why seed with the attempt id?",
                  "So the same attempt always gets the same order after a reload, but different attempts differ."),
                0.9, 0.9, prs=[(2, "Random order", True)]),
        },
        "SYN-023": {
            "class": "reviewer_coordinator", "scenario": "keeps the board and runs merges; no review data in sprints 1-2 because the team did not use pull requests; reviews in sprints 3-4",
            "S05-S1": S(
                [T("T1", "Project setup and settings", "Django project, settings per environment, database config.",
                   ["Project runs with one command", "Settings split into base, dev and prod", "Secrets from environment"], 3, 3, "Done", [1, 1, 1], 4,
                   "SECRET_KEY = os.environ['DJANGO_SECRET_KEY']\nDATABASES = {'default': dj_database_url.config(default='sqlite:///db.sqlite3')}")],
                [(0, 9, "django project", "T1", [("config/settings.py", "config_or_docs", 74, 0), ("manage.py", "config_or_docs", 21, 0)]),
                 (1, 10, "split settings", "T1", [("config/settings_prod.py", "config_or_docs", 18, 0)]),
                 (2, 14, "readme", "T1", [("README.md", "config_or_docs", 33, 0)]),
                 (6, 15, "merge conflict fixes in models", None, [("quiz/models.py", "code", 5, 7)]),
                 (10, 11, "board and workflow notes", None, [("docs/workflow.md", "config_or_docs", 24, 0)])],
                Q("good", 4, "settings read the secret key from the environment", "Why is SECRET_KEY not in settings.py?",
                  "It signs sessions. If it is in git anyone can forge a session."), 0.9, 0.8),
            "S05-S2": S(
                [T("T1", "Seed data and fixtures", "Sample quizzes for demos and tests.",
                   ["Fixture with two quizzes", "Command to load it", "Used in tests"], 3, 2, "Done", [1, 1, 0], 3,
                   "python manage.py loaddata sample_quizzes.json")],
                [(2, 10, "fixtures", "T1", [("quiz/fixtures/sample_quizzes.json", "config_or_docs", 96, 0)]),
                 (3, 15, "fix merge of two feature branches", None, [("quiz/views.py", "code", 6, 4)]),
                 (8, 11, "fix migration conflict", None, [("quiz/models.py", "code", 3, 2)])],
                Q("partial", 3, "loaddata imports the JSON fixture", "What happens if the fixture ids clash with existing rows?",
                  "They are overwritten, I think."), 0.9, 0.8),
            "S05-S3": S(
                [T("T1", "Move the team to pull requests", "Branch protection, review rule and a PR template.",
                   ["Main branch protected", "One approval required", "PR template added"], 2, 2, "Done", [1, 1, 1], 4,
                   "## Summary\n## How tested\n## Screenshots")],
                [(0, 10, "pr template", "T1", [(".github/pull_request_template.md", "config_or_docs", 9, 0)]),
                 (5, 14, "tidy imports after merges", None, [("quiz/views.py", "code", 4, 4)])],
                Q("partial", 3, "the PR template lists summary and how tested", "Why require one approval?",
                  "So someone else reads every change before it reaches main."),
                0.9, 0.8, mfo=3,
                reviews=[(12, "SYN-021", "COMMENTED", "expired() trusts attempt.started_at, which is set in the same request that creates the attempt. Make sure a refresh cannot create a second attempt and reset the clock. Also add a test for the exact boundary second.", "substantive"),
                         (12, "SYN-022", "APPROVED", "CSV import silently ignores extra columns. That is fine, but a row with a blank answer letter makes every option wrong; please report that as a row error.", "substantive"),
                         (13, "SYN-025", "COMMENTED", "Can you add the migration for the new field?", "brief")],
                comments=[(13, "SYN-021", "Good point, I'll make attempt creation idempotent. @SYN-023", 1, 1)]),
            "S05-S4": S(
                [T("T1", "Final report data and screenshots", "Collect results and screenshots for the project report.",
                   ["Screenshots of each page", "Short test report"], 2, 2, "Done", [1, 1], 4, "docs/report/ with 12 screenshots and test-report.md")],
                [(8, 10, "report folder", "T1", [("docs/report.md", "config_or_docs", 55, 0)]),
                 (10, 14, "test report", "T1", [("docs/test-report.md", "config_or_docs", 38, 0)]),
                 (12, 15, "leaderboard tiebreak fix", None, [("quiz/leaderboard.py", "code", 2, 1)])],
                Q("good", 4, "leaderboard sorts by score then duration", "Why did you fix the tiebreak?",
                  "The first version used started_at, which ties by when you started, not how fast you were."),
                0.9, 0.8, mfo=4,
                reviews=[(10, "SYN-021", "COMMENTED", "The leaderboard shows every attempt, so one student with three attempts fills the board. The requirement says only the best attempt per student. Use a distinct on student or group the query.", "substantive"),
                         (11, "SYN-022", "APPROVED", "Seeded shuffle gives the same order on reload, test is clear. Options still keep their saved order, ok for now.", "substantive"),
                         (12, "SYN-021", "APPROVED", "good", "approval"),
                         (13, "SYN-025", "COMMENTED", "Fine.", "brief")],
                comments=[(11, "SYN-021", "Yes, I will fix the best attempt filter. @SYN-023", 1, 1)]),
        },
        "SYN-024": {
            "class": "free_rider", "scenario": "pasted-template commit that inflates lines; tiny real contribution; sprint 4 task finished by a teammate",
            "S05-S1": S(
                [T("T1", "Home page layout", "Landing page with a list of quizzes.",
                   ["Page lists quizzes", "Basic styling"], 3, 2, "Partially Done", [1, 0], 2,
                   """{% for quiz in quizzes %}<li><a href="{% url 'take' quiz.id %}">{{ quiz.title }}</a></li>{% endfor %}""")],
                [(10, 21, "home page", "T1", [("quiz/templates/quiz/dashboard.html", "code", 12, 0)])],
                Q("weak", 2, "dashboard.html loops over quizzes", "Where does 'quizzes' come from?", "The view passes it, I think."), 0.6, 0.2),
            "S05-S2": S(
                [T("T1", "Styling with a template", "Apply a CSS theme to the pages.",
                   ["Stylesheet applied to all pages", "Responsive layout"], 3, 2, "Done", [1, 0], 2,
                   """/* pasted from a free admin theme: 580 lines, not adapted */
.sidebar { ... } .card { ... } .btn-primary { ... }""")],
                [(13, 22, "add theme css", "T1", [("quiz/templates/quiz/take.html", "code", 612, 8)])],
                Q("weak", 2, "take.html includes a large pasted theme", "What does the .sidebar rule do in your pages?", "I'm not sure, it came with the theme."), 0.5, 0.2),
            "S05-S3": S(
                [T("T1", "Quiz categories", "Group quizzes by category.",
                   ["Category model", "Filter on the dashboard"], 3, 2, "To Do", [0, 0], 1)],
                [], Q("weak", 1, "(no code this sprint)", "How would categories be stored?", "A new table."), 0.0, 0.0),
            "S05-S4": S(
                [T("T1", "Quiz categories", "Group quizzes by category.",
                   ["Category model", "Filter on the dashboard"], 3, 2, "Done", [1, 0], 3,
                   """class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)   # added by a teammate""", by="SYN-025", carried="S05-S3-SYN-024-T1")],
                [(12, 20, "typo in template", None, [("quiz/templates/quiz/dashboard.html", "code", 1, 1)])],
                Q("weak", 2, "(categories were added by a teammate)", "How are quizzes linked to a category?", "With a foreign key, I guess."), 1.0, 0.1,
                prs=[(13, "Typo", True)]),
        },
        "SYN-025": {
            "class": "no_specific_pattern", "scenario": "steady but small: a few commits spread evenly in every sprint, modest tasks, no bursts",
            "S05-S1": S(
                [T("T1", "Attempt model", "Record which student took which quiz and when.",
                   ["Attempt links student and quiz", "Start and finish time stored"], 3, 2, "Done", [1, 1], 4,
                   """class Attempt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished = models.BooleanField(default=False)""")],
                [(1, 14, "attempt model", "T1", [("quiz/models.py", "code", 19, 0)]),
                 (4, 11, "answer model", "T1", [("quiz/models.py", "code", 12, 0)]),
                 (7, 15, "model tests", "T1", [("quiz/tests/test_models.py", "test", 22, 0)]),
                 (10, 10, "finish time", "T1", [("quiz/models.py", "code", 4, 0)])],
                Q("good", 4, "Attempt has started_at with auto_now_add", "What does auto_now_add do?", "Sets the time when the row is first created, and it is not editable afterwards."), 0.9, 0.9),
            "S05-S2": S(
                [T("T1", "Retake limit", "A student can take a quiz at most three times.",
                   ["Fourth attempt refused", "Message shown"], 2, 2, "Done", [1, 1], 4,
                   """if Attempt.objects.filter(student=user, quiz=quiz).count() >= 3:
    return HttpResponseForbidden('You have used all 3 attempts')""")],
                [(2, 15, "retake limit", "T1", [("quiz/views.py", "code", 8, 0)]),
                 (6, 11, "retake test", "T1", [("quiz/tests/test_views.py", "test", 19, 0)]),
                 (9, 14, "message wording", "T1", [("quiz/views.py", "code", 1, 1)]),
                 (12, 10, "docs", None, [("README.md", "config_or_docs", 7, 0)])],
                Q("good", 4, "the limit counts all attempts, finished or not", "Is an abandoned attempt a used attempt?",
                  "Yes, as it is written. That may be harsh."), 0.9, 0.9),
            "S05-S3": S(
                [T("T1", "Email results to students", "Send the score by email after finishing.",
                   ["Email after finish", "Contains score and quiz title"], 3, 2, "Partially Done", [1, 0], 3,
                   """send_mail(f'Result: {quiz.title}', f'You scored {score}', None, [user.email])   # score not formatted as percentage""")],
                [(1, 14, "send result mail", "T1", [("quiz/views.py", "code", 9, 0)]),
                 (5, 11, "use console email backend in dev", "T1", [("config/settings.py", "config_or_docs", 3, 0)]),
                 (9, 15, "mail test", "T1", [("quiz/tests/test_mail.py", "test", 17, 0)])],
                Q("partial", 3, "send_mail is called after the attempt is finished", "Which backend is used in development?",
                  "The console one, so it prints to the terminal."), 0.9, 0.9, prs=[(10, "Result email", True)]),
            "S05-S4": S(
                [T("T1", "Accessibility labels", "Labels on form fields and focus order.",
                   ["Every input has a label", "Tab order is logical"], 2, 2, "Done", [1, 1], 4,
                   """<label for="id_answer">Your answer</label> <input id="id_answer" name="answer">""")],
                [(2, 13, "labels in take.html", "T1", [("quiz/templates/quiz/take.html", "code", 10, 4)]),
                 (6, 11, "labels in results.html", "T1", [("quiz/templates/quiz/results.html", "code", 5, 2)]),
                 (10, 14, "category field migration", None, [("quiz/models.py", "code", 3, 0)])],
                Q("good", 4, "every input has a for attribute pointing to its id", "Why does that matter?", "A screen reader reads the label when the input is focused."), 0.9, 0.9,
                prs=[(7, "Labels", True)]),
        },
    },
}
