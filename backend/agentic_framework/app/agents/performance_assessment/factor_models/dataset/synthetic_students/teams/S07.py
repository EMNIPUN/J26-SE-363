"""Team S07: Fitness tracker (React Native + TypeScript, Express/TypeScript API). Five sprints. Students: steady API
developer, rusher on the mobile screens (one sprint with no commits), two-burst worker, a free rider who pastes a library
and then fades, and a student whose tasks alternate between hard-and-small and easy-and-large."""
from _kit import T, Q, S

TEAM = {
    "team": "S07", "domain": "Fitness tracker", "stack": "React Native and Express (TypeScript)",
    "sprint_starts": {"S07-S1": "2026-01-05", "S07-S2": "2026-01-19", "S07-S3": "2026-02-02", "S07-S4": "2026-02-16", "S07-S5": "2026-03-02"},
    "edges": [
        ("api/src/app.ts", "api/src/routes/workouts.ts"), ("api/src/app.ts", "api/src/routes/auth.ts"), ("api/src/app.ts", "api/src/routes/goals.ts"),
        ("api/src/app.ts", "api/src/routes/stats.ts"), ("api/src/routes/workouts.ts", "api/src/controllers/workoutController.ts"),
        ("api/src/routes/workouts.ts", "api/src/middleware/auth.ts"), ("api/src/routes/goals.ts", "api/src/controllers/goalController.ts"),
        ("api/src/routes/goals.ts", "api/src/middleware/auth.ts"), ("api/src/routes/stats.ts", "api/src/services/statsService.ts"),
        ("api/src/routes/stats.ts", "api/src/middleware/auth.ts"), ("api/src/routes/auth.ts", "api/src/controllers/authController.ts"),
        ("api/src/controllers/workoutController.ts", "api/src/models/Workout.ts"), ("api/src/controllers/goalController.ts", "api/src/models/Goal.ts"),
        ("api/src/controllers/authController.ts", "api/src/models/User.ts"), ("api/src/middleware/auth.ts", "api/src/models/User.ts"),
        ("api/src/services/statsService.ts", "api/src/models/Workout.ts"), ("api/src/services/statsService.ts", "api/src/services/streak.ts"),
        ("api/src/services/streak.ts", "api/src/models/Workout.ts"), ("api/src/controllers/goalController.ts", "api/src/services/statsService.ts"),
        ("mobile/App.tsx", "mobile/src/screens/Home.tsx"), ("mobile/App.tsx", "mobile/src/screens/LogWorkout.tsx"), ("mobile/App.tsx", "mobile/src/screens/History.tsx"),
        ("mobile/App.tsx", "mobile/src/screens/Goals.tsx"), ("mobile/App.tsx", "mobile/src/screens/Stats.tsx"),
        ("mobile/src/screens/Home.tsx", "mobile/src/components/WorkoutCard.tsx"), ("mobile/src/screens/History.tsx", "mobile/src/components/WorkoutCard.tsx"),
        ("mobile/src/screens/Home.tsx", "mobile/src/api/client.ts"), ("mobile/src/screens/LogWorkout.tsx", "mobile/src/api/client.ts"),
        ("mobile/src/screens/History.tsx", "mobile/src/api/client.ts"), ("mobile/src/screens/Goals.tsx", "mobile/src/api/client.ts"),
        ("mobile/src/screens/Stats.tsx", "mobile/src/api/client.ts"),
    ],
    "students": {
        "SYN-031": {
            "class": "consistent_deep_contributor", "scenario": "API developer working most days across five sprints; slightly thinner last sprint; validation gaps",
            "S07-S1": S(
                [T("T1", "Workout model and log endpoint", "Log a workout with type, duration and calories.",
                   ["POST /workouts stores type, duration, calories and date", "Duration must be positive", "Only the logged-in user's workouts are returned by GET /workouts"], 5, 3, "Done", [1, 0, 1], 4,
                   """export async function logWorkout(req: AuthedRequest, res: Response) {
  const { type, durationMin, calories } = req.body;
  const w = await Workout.create({ user: req.user.id, type, durationMin, calories, date: new Date() });
  res.status(201).json(w);   // durationMin is not validated
}""")],
                [(0, 10, "workout model", "T1", [("api/src/models/Workout.ts", "code", 24, 0)]),
                 (1, 14, "log workout controller", "T1", [("api/src/controllers/workoutController.ts", "code", 31, 0)]),
                 (2, 11, "routes and auth middleware", "T1", [("api/src/routes/workouts.ts", "code", 14, 0), ("api/src/middleware/auth.ts", "code", 22, 0)]),
                 (4, 15, "list own workouts", "T1", [("api/src/controllers/workoutController.ts", "code", 17, 0)]),
                 (6, 10, "workout tests", "T1", [("api/tests/workouts.test.ts", "test", 46, 0)]),
                 (9, 14, "app wiring", "T1", [("api/src/app.ts", "code", 19, 0)]),
                 (11, 11, "fix date handling", "T1", [("api/src/controllers/workoutController.ts", "code", 4, 3)])],
                Q("good", 4, "logWorkout reads the user from req.user, not the body", "Why not take the user id from the body?",
                  "A client could send another user's id. req.user comes from the verified token."), 0.9, 0.95, prs=[(7, "Workout log", True), (12, "App wiring", True)]),
            "S07-S2": S(
                [T("T1", "Workout history with filters", "List workouts filtered by type and date range, paged.",
                   ["Filter by type", "Filter by date range", "Paging with page and size", "Total count in response"], 5, 4, "Done", [1, 1, 1, 1], 5,
                   """const q: FilterQuery<IWorkout> = { user: req.user.id };
if (type) q.type = type;
if (from || to) q.date = { ...(from && { $gte: new Date(from) }), ...(to && { $lte: new Date(to) }) };
const [items, total] = await Promise.all([Workout.find(q).sort({ date: -1 }).skip(page * size).limit(size), Workout.countDocuments(q)]);"""),
                 T("T2", "Delete and edit a workout", "A user can edit or delete their own workout.",
                   ["PATCH /workouts/:id", "DELETE /workouts/:id", "Other users' workouts give 404"], 3, 3, "Done", [1, 1, 1], 4,
                   """const w = await Workout.findOneAndDelete({ _id: req.params.id, user: req.user.id });
if (!w) return res.status(404).end();""")],
                [(0, 10, "filters", "T1", [("api/src/controllers/workoutController.ts", "code", 28, 5)]),
                 (1, 15, "paging", "T1", [("api/src/controllers/workoutController.ts", "code", 14, 2)]),
                 (3, 11, "edit and delete", "T2", [("api/src/controllers/workoutController.ts", "code", 35, 0), ("api/src/routes/workouts.ts", "code", 6, 0)]),
                 (4, 16, "tests for filters", "T1", [("api/tests/workouts.test.ts", "test", 51, 0)]),
                 (7, 10, "tests for ownership", "T2", [("api/tests/workouts.test.ts", "test", 28, 0)]),
                 (9, 14, "count query", "T1", [("api/src/controllers/workoutController.ts", "code", 5, 3)]),
                 (11, 11, "input validation", "T2", [("api/src/controllers/workoutController.ts", "code", 14, 1)])],
                Q("strong", 5, "the delete query includes the user id", "Why findOneAndDelete with both id and user?",
                  "If it only used the id any user could delete anyone's workout. Adding the user means other people's ids simply return 404."), 0.9, 0.95,
                prs=[(8, "Filters and paging", True), (12, "Edit and delete", True)]),
            "S07-S3": S(
                [T("T1", "Weekly statistics", "Totals for the week: minutes, calories, count per type.",
                   ["Total minutes", "Total calories", "Count per type", "Week starts on Monday"], 5, 3, "Done", [1, 1, 1, 0], 4,
                   """const start = startOfWeek(new Date(), { weekStartsOn: 0 });   // Sunday, should be Monday""")],
                [(0, 11, "stats service", "T1", [("api/src/services/statsService.ts", "code", 47, 0)]),
                 (1, 14, "stats route", "T1", [("api/src/routes/stats.ts", "code", 11, 0)]),
                 (3, 10, "aggregate per type", "T1", [("api/src/services/statsService.ts", "code", 19, 4)]),
                 (5, 15, "stats tests", "T1", [("api/tests/stats.test.ts", "test", 39, 0)]),
                 (8, 11, "fix empty week", "T1", [("api/src/services/statsService.ts", "code", 5, 2)]),
                 (10, 16, "cache stats for a minute", "T1", [("api/src/routes/stats.ts", "code", 12, 0)])],
                Q("good", 4, "weekly totals use an aggregation by type", "What is wrong with weekStartsOn 0?",
                  "0 is Sunday and the requirement says Monday. I missed it."), 0.9, 0.95, prs=[(6, "Weekly stats", True)]),
            "S07-S4": S(
                [T("T1", "Streak calculation", "Count consecutive days with at least one workout.",
                   ["Current streak", "Longest streak", "A missed day resets the current streak", "Time zone of the user respected"], 8, 4, "Done", [1, 1, 1, 0], 4,
                   """export function currentStreak(days: string[], today: string): number {
  const set = new Set(days);
  let n = 0, d = parseISO(today);
  if (!set.has(today)) d = subDays(d, 1);
  while (set.has(format(d, 'yyyy-MM-dd'))) { n++; d = subDays(d, 1); }
  return n;
}""")],
                [(0, 10, "streak service", "T1", [("api/src/services/streak.ts", "code", 52, 0)]),
                 (2, 14, "streak tests", "T1", [("api/tests/streak.test.ts", "test", 61, 0)]),
                 (3, 11, "longest streak", "T1", [("api/src/services/streak.ts", "code", 21, 0)]),
                 (5, 15, "streak endpoint", "T1", [("api/src/routes/stats.ts", "code", 10, 0)]),
                 (8, 10, "today not yet logged case", "T1", [("api/src/services/streak.ts", "code", 4, 1), ("api/tests/streak.test.ts", "test", 15, 0)]),
                 (11, 14, "refactor to pure function", "T1", [("api/src/services/streak.ts", "code", 12, 18)])],
                Q("strong", 5, "currentStreak starts from yesterday when today has no workout", "Why subtract a day when today is missing?",
                  "A user who has not logged yet today still has their streak. It only breaks if yesterday was also missed."), 0.95, 0.95,
                prs=[(6, "Streak", True), (12, "Refactor", True)]),
            "S07-S5": S(
                [T("T1", "Goals API", "Set a weekly minutes goal and check progress.",
                   ["Create a goal", "Progress as percentage", "One active goal per user"], 5, 3, "Partially Done", [1, 1, 0], 3,
                   """export async function progress(userId: string, goal: IGoal) {
  const { minutes } = await weekTotals(userId);
  return Math.min(100, Math.round((minutes / goal.targetMin) * 100));
}   // a second goal can still be created""")],
                [(0, 10, "goal model and controller", "T1", [("api/src/models/Goal.ts", "code", 18, 0), ("api/src/controllers/goalController.ts", "code", 33, 0)]),
                 (2, 15, "progress calculation", "T1", [("api/src/controllers/goalController.ts", "code", 14, 0)]),
                 (4, 11, "goal routes", "T1", [("api/src/routes/goals.ts", "code", 12, 0)]),
                 (8, 14, "goal tests", "T1", [("api/tests/goals.test.ts", "test", 27, 0)])],
                Q("good", 4, "progress caps the percentage at 100", "Why Math.min?", "A user can exceed the goal, but a progress bar should not go past full."), 0.9, 0.95,
                prs=[(9, "Goals API", True)]),
        },
        "SYN-032": {
            "class": "last_minute_rusher", "scenario": "mobile screens finished in the last two days of each sprint; sprint 3 the student was ill and has no commits",
            "S07-S1": S(
                [T("T1", "Home screen", "Show today's workouts and the weekly total.",
                   ["List of today's workouts", "Weekly total", "Button to log a workout"], 5, 3, "Done", [1, 0, 1], 3,
                   """export default function Home({ navigation }: Props) {
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  useEffect(() => { api.get('/workouts?today=1').then(r => setWorkouts(r.data.items)); }, []);
  return <View>{workouts.map(w => <WorkoutCard key={w._id} w={w} />)}<Button title="Log workout" onPress={() => navigation.navigate('Log')} /></View>;
}   // weekly total not shown""")],
                [(11, 21, "home screen", "T1", [("mobile/src/screens/Home.tsx", "code", 64, 0), ("mobile/src/components/WorkoutCard.tsx", "code", 33, 0)]),
                 (12, 14, "api client", "T1", [("mobile/src/api/client.ts", "code", 24, 0)]),
                 (13, 16, "navigation", "T1", [("mobile/App.tsx", "code", 31, 0)]),
                 (13, 23, "button", "T1", [("mobile/src/screens/Home.tsx", "code", 8, 2)])],
                Q("partial", 3, "Home fetches today's workouts in useEffect", "What is the dependency array for?", "To run it only once when the screen mounts."), 0.8, 0.9, prs=[(13, "Home screen", True)]),
            "S07-S2": S(
                [T("T1", "Log workout screen", "A form to log a workout.",
                   ["Pick a type", "Enter minutes", "Calories optional", "Show validation errors"], 5, 3, "Partially Done", [1, 1, 1, 0], 3,
                   """const submit = async () => { await api.post('/workouts', { type, durationMin: Number(minutes), calories: Number(calories) || undefined }); navigation.goBack(); };""")],
                [(12, 13, "log form", "T1", [("mobile/src/screens/LogWorkout.tsx", "code", 78, 0)]),
                 (13, 10, "post to api", "T1", [("mobile/src/screens/LogWorkout.tsx", "code", 14, 3)]),
                 (13, 22, "type picker", "T1", [("mobile/src/screens/LogWorkout.tsx", "code", 22, 4)])],
                Q("good", 4, "submit posts and goes back", "What if minutes is empty?", "Number('') is 0, so it posts 0 minutes and the API should reject it."), 0.8, 0.9, prs=[(13, "Log workout", True)]),
            "S07-S3": S(
                [T("T1", "History screen", "Show past workouts with paging.",
                   ["List with infinite scroll", "Filter by type"], 5, 3, "To Do", [0, 0], 1, carried="")],
                [], Q("weak", 1, "(no code this sprint)", "How would infinite scroll work?", "FlatList onEndReached, page + 1."), 0.0, 0.0),
            "S07-S4": S(
                [T("T1", "History screen", "Show past workouts with paging.",
                   ["List with infinite scroll", "Filter by type"], 5, 3, "Done", [1, 0], 3,
                   """<FlatList data={items} renderItem={({ item }) => <WorkoutCard w={item} />} onEndReached={() => setPage(p => p + 1)} />""", carried="S07-S3-SYN-032-T1")],
                [(11, 22, "history list", "T1", [("mobile/src/screens/History.tsx", "code", 69, 0)]),
                 (12, 20, "onEndReached paging", "T1", [("mobile/src/screens/History.tsx", "code", 21, 5)]),
                 (13, 14, "history route", "T1", [("mobile/App.tsx", "code", 9, 0)])],
                Q("partial", 3, "FlatList onEndReached increments the page", "Where do the next items get appended?", "Not appended, the effect replaces the list. That is a bug."), 0.8, 0.9, prs=[(13, "History", True)]),
            "S07-S5": S(
                [T("T1", "Stats screen", "Weekly chart and streak.",
                   ["Bar chart of minutes per day", "Streak badge", "Pull to refresh"], 5, 3, "Done", [1, 1, 0], 4,
                   """<BarChart data={{ labels: days, datasets: [{ data: minutes }] }} width={w} height={220} />
<Text>🔥 {streak.current}-day streak</Text>""")],
                [(10, 20, "stats screen", "T1", [("mobile/src/screens/Stats.tsx", "code", 88, 0)]),
                 (12, 15, "streak badge", "T1", [("mobile/src/screens/Stats.tsx", "code", 14, 0)]),
                 (13, 19, "route", "T1", [("mobile/App.tsx", "code", 7, 0)])],
                Q("good", 4, "Stats passes days and minutes to the bar chart", "Where does streak come from?", "From the /stats/streak endpoint the API team added."), 0.85, 0.9, prs=[(13, "Stats screen", True)]),
        },
        "SYN-033": {
            "class": "burst_worker", "scenario": "two bursts per sprint with a quiet gap; sprint 4 has only one burst",
            "S07-S1": S(
                [T("T1", "Registration and login", "Users register and log in with email and password.",
                   ["Register hashes the password", "Login returns a token", "Wrong password gives 401"], 5, 3, "Done", [1, 1, 1], 4,
                   """const ok = await bcrypt.compare(password, user.passwordHash);
if (!ok) return res.status(401).json({ error: 'invalid credentials' });""")],
                [(0, 10, "user model", "T1", [("api/src/models/User.ts", "code", 22, 0)]),
                 (0, 15, "register", "T1", [("api/src/controllers/authController.ts", "code", 38, 0)]),
                 (1, 11, "login", "T1", [("api/src/controllers/authController.ts", "code", 24, 0), ("api/src/routes/auth.ts", "code", 9, 0)]),
                 (11, 10, "auth tests", "T1", [("api/tests/auth.test.ts", "test", 55, 0)]),
                 (12, 14, "fix token expiry", "T1", [("api/src/controllers/authController.ts", "code", 3, 2)])],
                Q("good", 4, "login compares with bcrypt.compare", "Why not compare the plain strings?", "The database stores a hash, not the password."), 0.9, 0.9, prs=[(2, "Auth", True), (13, "Auth tests", True)]),
            "S07-S2": S(
                [T("T1", "Offline queue for logged workouts", "Workouts logged offline are sent when the connection returns.",
                   ["Workouts saved locally when offline", "Sent in order on reconnect", "Duplicates avoided"], 8, 5, "Partially Done", [1, 1, 0], 3,
                   """export async function flush() {
  const queue = JSON.parse((await AsyncStorage.getItem('queue')) ?? '[]');
  for (const item of queue) { await api.post('/workouts', item); }
  await AsyncStorage.removeItem('queue');
}   // one failed post loses the rest, no duplicate guard""")],
                [(1, 10, "local queue", "T1", [("mobile/src/api/client.ts", "code", 41, 0)]),
                 (1, 17, "flush on reconnect", "T1", [("mobile/src/api/client.ts", "code", 24, 0)]),
                 (2, 12, "connection listener", "T1", [("mobile/App.tsx", "code", 19, 0)]),
                 (10, 11, "queue tests", "T1", [("mobile/tests/queue.test.ts", "test", 36, 0)]),
                 (11, 15, "keep order", "T1", [("mobile/src/api/client.ts", "code", 8, 2)])],
                Q("good", 4, "flush posts each queued workout then clears the queue", "What if one post fails?", "The loop throws and the queue is not cleared, so already sent ones get sent again. I need an id per item."), 0.85, 0.9,
                prs=[(3, "Offline queue", True)]),
            "S07-S3": S(
                [T("T1", "Push reminders", "Remind the user at 18:00 if no workout was logged.",
                   ["Reminder at the chosen time", "Skipped if a workout exists today", "User can turn it off"], 5, 3, "Done", [1, 1, 1], 4,
                   """await Notifications.scheduleNotificationAsync({ content: { title: 'Time to move' }, trigger: { hour: 18, minute: 0, repeats: true } });""")],
                [(0, 10, "schedule reminder", "T1", [("mobile/src/screens/Goals.tsx", "code", 36, 0)]),
                 (1, 16, "skip if logged", "T1", [("mobile/src/screens/Goals.tsx", "code", 19, 0)]),
                 (2, 11, "settings switch", "T1", [("mobile/src/screens/Goals.tsx", "code", 22, 0)]),
                 (11, 14, "cancel on logout", "T1", [("mobile/App.tsx", "code", 6, 0)]),
                 (12, 10, "tests", "T1", [("mobile/tests/reminder.test.ts", "test", 31, 0)])],
                Q("good", 4, "the reminder repeats daily at 18:00", "How is it skipped when a workout exists?", "The app cancels and reschedules for tomorrow after a workout is logged."), 0.9, 0.9,
                prs=[(3, "Reminders", True), (13, "Reminder tests", True)]),
            "S07-S4": S(
                [T("T1", "Share a workout", "Share a summary to other apps.",
                   ["Share button", "Summary text with type, duration and calories"], 3, 2, "Done", [1, 1], 4,
                   """Share.share({ message: `${w.type} for ${w.durationMin} min, ${w.calories ?? 0} kcal` });""")],
                [(0, 10, "share button", "T1", [("mobile/src/screens/History.tsx", "code", 23, 0)]),
                 (0, 15, "share text", "T1", [("mobile/src/components/WorkoutCard.tsx", "code", 14, 0)]),
                 (1, 11, "test", "T1", [("mobile/tests/share.test.ts", "test", 15, 0)])],
                Q("good", 4, "Share.share takes a message string", "Where does the share sheet come from?", "The operating system."), 0.9, 0.9, prs=[(2, "Share", True)]),
            "S07-S5": S(
                [T("T1", "Accessibility and large text", "Support dynamic type and screen readers.",
                   ["accessibilityLabel on buttons", "Text scales", "Contrast checked"], 5, 3, "Partially Done", [1, 1, 0], 3,
                   """<Pressable accessibilityRole="button" accessibilityLabel="Log workout" onPress={log}><Text>＋</Text></Pressable>""")],
                [(1, 10, "labels", "T1", [("mobile/src/screens/Home.tsx", "code", 16, 3)]),
                 (1, 16, "text scaling", "T1", [("mobile/src/components/WorkoutCard.tsx", "code", 11, 4)]),
                 (11, 11, "labels on history", "T1", [("mobile/src/screens/History.tsx", "code", 9, 1)]),
                 (12, 14, "contrast fix", "T1", [("mobile/src/components/WorkoutCard.tsx", "code", 5, 5)])],
                Q("partial", 3, "buttons get an accessibilityLabel", "What is accessibilityRole for?", "Tells the screen reader it is a button."), 0.9, 0.9, prs=[(13, "Accessibility", True)]),
        },
        "SYN-034": {
            "class": "free_rider", "scenario": "pastes a large library into a counted folder (huge line count, one commit), almost nothing else; fades out after sprint 4",
            "S07-S1": S(
                [T("T1", "Project README and setup docs", "How to run API and mobile app.",
                   ["README with setup steps"], 1, 1, "Done", [1], 3, "# Fitness tracker\n## Run\n`npm install && npm start`")],
                [(5, 20, "readme", "T1", [("README.md", "config_or_docs", 19, 0)])],
                Q("weak", 2, "README lists npm start", "What does npm start run in the API?", "The server, I think."), 1.0, 0.0),
            "S07-S2": S(
                [T("T1", "Chart component", "A reusable bar chart component.",
                   ["Bar chart with labels", "Responsive width"], 3, 2, "Done", [1, 0], 2,
                   """// pasted chart library source, 1,900 lines, unchanged apart from the import path
export class BarChart extends React.Component { /* ... */ }""")],
                [(13, 22, "add chart component", "T1", [("mobile/src/components/WorkoutCard.tsx", "code", 1860, 12)])],
                Q("weak", 2, "WorkoutCard contains a pasted chart library", "Which part did you change?", "Only the import path."), 0.2, 0.1, prs=[(13, "Chart component", True)]),
            "S07-S3": S(
                [T("T1", "Unit tests for stats", "Tests for the stats service.",
                   ["Three tests for weekly totals"], 2, 1, "Partially Done", [1], 2,
                   """it('sums minutes', () => { expect(total([{ durationMin: 10 }, { durationMin: 20 }])).toBe(30); });""")],
                [(12, 21, "stats test", "T1", [("api/tests/stats.test.ts", "test", 11, 0)])],
                Q("weak", 2, "one test for the total of minutes", "What does an empty list return?", "Zero, I would hope."), 1.0, 0.4),
            "S07-S4": S(
                [T("T1", "Unit tests for stats", "Tests for the stats service.",
                   ["Three tests for weekly totals"], 2, 1, "To Do", [0], 1, carried="S07-S3-SYN-034-T1")],
                [], Q("weak", 1, "(no code this sprint)", "What tests are missing?", "The empty week and the type counts."), 0.0, 0.0),
        },
        "SYN-035": {
            "class": "no_specific_pattern", "scenario": "alternating work: hard tasks with little code, then easy tasks with a lot of code; joins in sprint 2",
            "S07-S2": S(
                [T("T1", "Time zone aware daily buckets", "Group workouts into days using the user's time zone.",
                   ["Store the user's time zone", "Daily buckets use that zone", "Daylight saving change handled"], 8, 5, "Done", [1, 1, 1], 5,
                   """const day = (d: Date, tz: string) => formatInTimeZone(d, tz, 'yyyy-MM-dd');
const buckets = workouts.reduce<Record<string, number>>((m, w) => { const k = day(w.date, user.tz); m[k] = (m[k] ?? 0) + w.durationMin; return m; }, {});""")],
                [(7, 14, "bucket by user time zone", "T1", [("api/src/services/statsService.ts", "code", 17, 4), ("api/src/models/User.ts", "code", 3, 0)]),
                 (10, 11, "dst test cases", "T1", [("api/tests/stats.test.ts", "test", 35, 0)])],
                Q("strong", 5, "buckets are keyed by the date in the user's time zone", "Why not use UTC dates?", "A workout at 23:30 in Colombo would land on the next UTC day and break streaks."), 0.95, 0.95, prs=[(11, "Time zone buckets", True)]),
            "S07-S3": S(
                [T("T1", "Exercise library screens", "List of exercises with descriptions and icons.",
                   ["List of 40 exercises", "Detail page", "Icon per muscle group"], 3, 2, "Done", [1, 1, 1], 4,
                   """export const exercises: Exercise[] = [{ id: 'squat', name: 'Squat', group: 'legs', text: '...' }, /* 39 more */];""")],
                [(1, 14, "exercise data", "T1", [("mobile/src/screens/Goals.tsx", "code", 312, 0)]),
                 (2, 10, "exercise list screen", "T1", [("mobile/src/screens/Goals.tsx", "code", 96, 0)]),
                 (2, 16, "detail page", "T1", [("mobile/src/screens/Goals.tsx", "code", 120, 0)]),
                 (4, 11, "icons", "T1", [("mobile/src/screens/Goals.tsx", "code", 88, 0)])],
                Q("good", 4, "the exercise list is a static array", "What would you change if exercises came from the API?", "Fetch them, cache them, and show a loading state."), 0.9, 0.9, prs=[(5, "Exercise library", True)]),
            "S07-S4": S(
                [T("T1", "Personal records", "Detect and store a new personal record for an exercise.",
                   ["Compare with previous best", "Store the record with date", "Handle equal values"], 8, 5, "Partially Done", [1, 1, 0], 4,
                   """export function isPR(prev: number | undefined, value: number): boolean { return prev === undefined || value > prev; }   // equal value is not a PR, requirement not stated""")],
                [(6, 15, "record detection", "T1", [("api/src/services/statsService.ts", "code", 22, 0)]),
                 (8, 11, "record tests", "T1", [("api/tests/stats.test.ts", "test", 28, 0)])],
                Q("good", 4, "isPR is true for no previous record or a higher value", "Is a tie a record?", "Not in my code. The requirement doesn't say so I had to choose."), 0.9, 0.95, prs=[(9, "Personal records", True)]),
            "S07-S5": S(
                [T("T1", "Seed 200 sample workouts for the demo", "Script that inserts realistic sample data.",
                   ["200 workouts over 60 days", "Several users", "Runs repeatedly"], 2, 1, "Done", [1, 1, 0], 3,
                   """for (let i = 0; i < 200; i++) await Workout.create({ user: pick(users), type: pick(types), durationMin: rand(15, 90), date: daysAgo(rand(0, 60)) });""")],
                [(2, 13, "seed script", "T1", [("api/src/models/Workout.ts", "code", 84, 0)]),
                 (3, 11, "sample users", "T1", [("api/src/models/User.ts", "code", 52, 0)]),
                 (9, 15, "readme for seed", "T1", [("README.md", "config_or_docs", 10, 0)])],
                Q("partial", 3, "the seed loop creates 200 random workouts", "How would running the seed twice behave?", "It adds 200 more."), 0.9, 0.9, prs=[(10, "Seed data", True)]),
        },
    },
}
