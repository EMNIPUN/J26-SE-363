"""Team S09: Expense splitting app (Android, Kotlin, Room). Three sprints. Students: steady core-logic developer, a
reviewer-coordinator who does many short reviews, a free rider whose big tasks are finished by teammates, a solo worker on
separate files (no shared files, no reviews), and a student on hard algorithmic work."""
from _kit import T, Q, S


def K(p):
    return "app/src/main/java/split/" + p


def KT(p):
    return "app/src/test/java/split/" + p


TEAM = {
    "team": "S09", "domain": "Expense splitting", "stack": "Android (Kotlin, Room)",
    "sprint_starts": {"S09-S1": "2026-02-02", "S09-S2": "2026-02-16", "S09-S3": "2026-03-02"},
    "edges": [
        (K("ui/MainActivity.kt"), K("ui/GroupScreen.kt")), (K("ui/MainActivity.kt"), K("ui/AddExpenseScreen.kt")), (K("ui/MainActivity.kt"), K("ui/BalancesScreen.kt")),
        (K("ui/GroupScreen.kt"), K("ui/ExpenseViewModel.kt")), (K("ui/AddExpenseScreen.kt"), K("ui/ExpenseViewModel.kt")), (K("ui/BalancesScreen.kt"), K("ui/ExpenseViewModel.kt")),
        (K("ui/ExpenseViewModel.kt"), K("data/Repository.kt")), (K("ui/ExpenseViewModel.kt"), K("domain/SettleUp.kt")), (K("ui/ExpenseViewModel.kt"), K("domain/Splitter.kt")),
        (K("data/Repository.kt"), K("data/ExpenseDao.kt")), (K("data/Repository.kt"), K("data/AppDatabase.kt")), (K("data/ExpenseDao.kt"), K("data/Expense.kt")),
        (K("data/ExpenseDao.kt"), K("data/Group.kt")), (K("data/AppDatabase.kt"), K("data/Expense.kt")), (K("data/AppDatabase.kt"), K("data/Group.kt")),
        (K("domain/SettleUp.kt"), K("data/Expense.kt")), (K("domain/Splitter.kt"), K("data/Expense.kt")), (K("export/CsvExport.kt"), K("data/Repository.kt")),
        (K("ui/BalancesScreen.kt"), K("export/CsvExport.kt")),
    ],
    "students": {
        "SYN-041": {
            "class": "consistent_deep_contributor", "scenario": "owns the domain logic (splitting and settling); regular commits through all sprints; late bug found in rounding",
            "S09-S1": S(
                [T("T1", "Equal and custom split", "Split an expense equally or by custom shares.",
                   ["Equal split among participants", "Custom shares add up to the total", "Remainder cents given to the payer", "Zero participants rejected"], 8, 5, "Done", [1, 1, 0, 1], 4,
                   """fun splitEqually(totalCents: Long, people: List<String>): Map<String, Long> {
    require(people.isNotEmpty()) { "no participants" }
    val base = totalCents / people.size
    val rem = (totalCents % people.size).toInt()
    return people.mapIndexed { i, p -> p to base + if (i < rem) 1 else 0 }.toMap()   // remainder goes to the first people, not the payer
}""")],
                [(0, 10, "expense entity", "T1", [(K("data/Expense.kt"), "code", 22, 0)]),
                 (1, 14, "equal split", "T1", [(K("domain/Splitter.kt"), "code", 31, 0)]),
                 (2, 11, "custom shares", "T1", [(K("domain/Splitter.kt"), "code", 29, 0)]),
                 (3, 15, "splitter tests", "T1", [(KT("SplitterTest.kt"), "test", 57, 0)]),
                 (5, 10, "reject empty participants", "T1", [(K("domain/Splitter.kt"), "code", 4, 0), (KT("SplitterTest.kt"), "test", 9, 0)]),
                 (7, 14, "money as cents", "T1", [(K("data/Expense.kt"), "code", 6, 4), (K("domain/Splitter.kt"), "code", 12, 12)]),
                 (10, 11, "fix remainder distribution test", "T1", [(KT("SplitterTest.kt"), "test", 14, 3)])],
                Q("good", 4, "money is stored as cents in a Long", "Why not Double?", "Floating point cannot represent 0.1 exactly, so sums drift. Cents as integers are exact."), 0.9, 0.95,
                prs=[(4, "Splitting", True), (11, "Cents", True)]),
            "S09-S2": S(
                [T("T1", "Who owes whom", "Compute balances and the fewest payments to settle.",
                   ["Net balance per person", "Settlement suggestions", "Total of balances is zero", "Handles one-person groups"], 8, 5, "Done", [1, 1, 1, 0], 5,
                   """fun settle(balances: Map<String, Long>): List<Payment> {
    val debtors = ArrayDeque(balances.filter { it.value < 0 }.entries.sortedBy { it.value })
    val creditors = ArrayDeque(balances.filter { it.value > 0 }.entries.sortedByDescending { it.value })
    val out = mutableListOf<Payment>()
    var d = debtors.removeFirstOrNull(); var c = creditors.removeFirstOrNull()
    var dv = d?.value ?: 0; var cv = c?.value ?: 0
    while (d != null && c != null) {
        val pay = minOf(-dv, cv)
        out += Payment(d.key, c.key, pay)
        dv += pay; cv -= pay
        if (dv == 0L) { d = debtors.removeFirstOrNull(); dv = d?.value ?: 0 }
        if (cv == 0L) { c = creditors.removeFirstOrNull(); cv = c?.value ?: 0 }
    }
    return out
}""")],
                [(0, 10, "balance calculation", "T1", [(K("domain/SettleUp.kt"), "code", 36, 0)]),
                 (1, 15, "settlement algorithm", "T1", [(K("domain/SettleUp.kt"), "code", 41, 0)]),
                 (2, 11, "settlement tests", "T1", [(KT("SettleUpTest.kt"), "test", 68, 0)]),
                 (4, 14, "property style test totals zero", "T1", [(KT("SettleUpTest.kt"), "test", 23, 0)]),
                 (7, 10, "wire into view model", "T1", [(K("ui/ExpenseViewModel.kt"), "code", 17, 0)]),
                 (9, 15, "sort stable for ties", "T1", [(K("domain/SettleUp.kt"), "code", 3, 2)]),
                 (11, 11, "doc comment on algorithm", None, [(K("domain/SettleUp.kt"), "code", 14, 0)])],
                Q("strong", 5, "settle matches the largest debtor with the largest creditor", "Is this the minimum number of payments?",
                  "No, it is a greedy approach and gives at most n-1 payments, but the true minimum is NP-hard in general. For group sizes here it is good enough."), 0.95, 0.95,
                prs=[(5, "Settle up", True), (12, "View model wiring", True)],
                reviews=[(10, "SYN-042", "COMMENTED", "ok", "approval")]),
            "S09-S3": S(
                [T("T1", "Rounding bug fix", "Cents lost when splitting among three people.",
                   ["Split of 100 among 3 sums to 100", "Remainder goes to the payer"], 3, 2, "Done", [1, 1], 4,
                   """fun splitEqually(totalCents: Long, people: List<String>, payer: String): Map<String, Long> {
    val base = totalCents / people.size; val rem = (totalCents % people.size).toInt()
    val order = listOf(payer) + people.filter { it != payer }
    return order.mapIndexed { i, p -> p to base + if (i < rem) 1 else 0 }.toMap()
}""", carried="S09-S1-SYN-041-T1"),
                 T("T2", "Multiple currencies", "Expenses can use LKR or USD with a fixed rate.",
                   ["Currency per expense", "Balances shown in the group currency", "Rate stored with the expense"], 5, 3, "Partially Done", [1, 1, 0], 3,
                   """data class Expense(val id: Long, val cents: Long, val currency: String, val rateToGroup: Double = 1.0)   // rate is not stored per expense in the DAO yet""")],
                [(0, 10, "rounding bug test", "T1", [(KT("SplitterTest.kt"), "test", 22, 0)]),
                 (1, 14, "payer gets remainder", "T1", [(K("domain/Splitter.kt"), "code", 9, 4)]),
                 (3, 11, "currency field", "T2", [(K("data/Expense.kt"), "code", 7, 0)]),
                 (5, 15, "conversion in balances", "T2", [(K("domain/SettleUp.kt"), "code", 14, 3)]),
                 (8, 10, "currency tests", "T2", [(KT("SettleUpTest.kt"), "test", 28, 0)]),
                 (10, 14, "room migration for currency", "T2", [(K("data/AppDatabase.kt"), "code", 11, 1)])],
                Q("good", 4, "the payer is moved to the front so the remainder goes to them", "Why does the order matter?", "The first rem people get one extra cent. Putting the payer first makes it them."), 0.9, 0.95,
                prs=[(2, "Rounding fix", True), (11, "Currencies", True)]),
        },
        "SYN-042": {
            "class": "reviewer_coordinator", "scenario": "many short reviews on every pull request, merges for others; reviews are fast and sometimes shallow; writes the UI glue",
            "S09-S1": S(
                [T("T1", "App skeleton and navigation", "Activities, navigation graph and theme.",
                   ["Three screens with navigation", "Material theme"], 3, 2, "Done", [1, 1], 4,
                   """NavHost(navController, startDestination = "groups") {
    composable("groups") { GroupScreen(nav) }
    composable("add/{groupId}") { AddExpenseScreen(nav) }
    composable("balances/{groupId}") { BalancesScreen(nav) }
}""")],
                [(0, 10, "main activity and nav", "T1", [(K("ui/MainActivity.kt"), "code", 44, 0)]),
                 (1, 15, "theme", "T1", [("app/src/main/res/values/themes.xml", "config_or_docs", 21, 0)]),
                 (6, 11, "view model", None, [(K("ui/ExpenseViewModel.kt"), "code", 38, 0)])],
                Q("good", 4, "NavHost declares the three destinations", "What does the groupId argument do?", "It tells the screen which group to load."), 0.95, 0.9,
                mfo=3,
                reviews=[(4, "SYN-041", "COMMENTED", "splitEqually gives the extra cents to the first people in the list, but the requirement says the payer. Pass the payer in and put them first.", "substantive"),
                         (4, "SYN-044", "APPROVED", "Looks fine.", "brief"),
                         (11, "SYN-041", "APPROVED", "good", "approval"),
                         (12, "SYN-045", "COMMENTED", "Can you add a test for exactly two people?", "brief")],
                comments=[(5, "SYN-041", "Yes, I'll change it. @SYN-042", 1, 1)]),
            "S09-S2": S(
                [T("T1", "Add expense screen", "Form to add an expense with payer and participants.",
                   ["Amount, description, payer", "Choose participants", "Validates positive amount", "Saves via the view model"], 5, 4, "Done", [1, 1, 1, 0], 4,
                   """Button(onClick = { vm.addExpense(amount.toLongOrNull(), desc, payer, selected) }, enabled = selected.isNotEmpty()) { Text("Save") }
// amount is parsed but a negative value is not rejected""")],
                [(0, 10, "add expense form", "T1", [(K("ui/AddExpenseScreen.kt"), "code", 82, 0)]),
                 (1, 15, "participants selection", "T1", [(K("ui/AddExpenseScreen.kt"), "code", 31, 4)]),
                 (3, 11, "save through view model", "T1", [(K("ui/ExpenseViewModel.kt"), "code", 14, 0)]),
                 (6, 14, "ui test for form", "T1", [("app/src/androidTest/java/split/AddExpenseTest.kt", "test", 36, 0)])],
                Q("good", 4, "Save is enabled only when participants are selected", "What validates the amount?", "toLongOrNull gives null for text, but a negative number passes. That's a gap."), 0.9, 0.9,
                mfo=4, prs=[(7, "Add expense screen", True)],
                reviews=[(2, "SYN-041", "APPROVED", "The settle algorithm with two queues is clear. Is the output ordering stable if two people owe the same amount? Add a test.", "substantive"),
                         (4, "SYN-044", "APPROVED", "The export writes the header and one row per expense correctly, but a description or name with a comma will break the row. Add quoting for commas and quotes and a test with such a name.", "substantive"),
                         (5, "SYN-045", "COMMENTED", "Why does the interval merge allocate a new list each time?", "brief"),
                         (11, "SYN-041", "APPROVED", "lgtm", "approval")],
                comments=[(3, "SYN-041", "Added a tie test. @SYN-042", 1, 1), (6, "SYN-044", "I'll quote names, thanks.", 1, 0)]),
            "S09-S3": S(
                [T("T1", "Release APK and test notes", "Signed build and a manual test checklist.",
                   ["Signed release build", "Checklist of 15 manual tests", "Known issues listed"], 3, 3, "Done", [1, 1, 1], 4,
                   "signingConfigs { release { storeFile file(System.getenv('KEYSTORE')) } }")],
                [(7, 10, "release build config", "T1", [("app/build.gradle", "config_or_docs", 18, 0)]),
                 (9, 14, "manual test checklist", "T1", [("docs/test-checklist.md", "config_or_docs", 44, 0)]),
                 (11, 11, "known issues", "T1", [("docs/known-issues.md", "config_or_docs", 16, 0)])],
                Q("good", 4, "the keystore path comes from an environment variable", "Why not commit the keystore?", "Anyone with the repo could sign apps as us."), 0.95, 0.9,
                mfo=3,
                reviews=[(3, "SYN-041", "APPROVED", "Currency conversion in balances rounds each expense separately, so the totals can differ by a cent from converting the sum. Fine for the demo, add a note to the known issues.", "substantive"),
                         (10, "SYN-041", "COMMENTED", "Room migration looks right, did you test an upgrade from version 1 on a real device?", "substantive"),
                         (11, "SYN-044", "APPROVED", "ok", "approval")],
                comments=[(4, "SYN-041", "Will note it. @SYN-042", 1, 1)]),
        },
        "SYN-043": {
            "class": "free_rider", "scenario": "claims large tasks but teammates finish them; own commits are tiny; slight effort at the end",
            "S09-S1": S(
                [T("T1", "Room database setup", "Entities, DAO and database class.",
                   ["Expense and Group entities", "DAO with insert and queries", "Database singleton"], 5, 3, "Done", [1, 1, 1], 3,
                   """@Database(entities = [Expense::class, Group::class], version = 1)
abstract class AppDatabase : RoomDatabase() { abstract fun expenseDao(): ExpenseDao }   // written by a teammate""", by="SYN-041")],
                [(12, 21, "gradle sync", None, [("app/build.gradle", "config_or_docs", 3, 1)])],
                Q("weak", 2, "(database written by a teammate)", "What does the @Database annotation take?", "The entities and a version, I think."), 0.0, 0.0),
            "S09-S2": S(
                [T("T1", "Groups screen", "List groups and create a new one.",
                   ["List of groups", "Create group dialog"], 5, 3, "Partially Done", [1, 0], 2,
                   """@Composable fun GroupScreen(nav: NavController) { val groups by vm.groups.collectAsState(); LazyColumn { items(groups) { Text(it.name) } } }""")],
                [(12, 20, "group list", "T1", [(K("ui/GroupScreen.kt"), "code", 29, 0)]),
                 (13, 17, "group name text", "T1", [(K("ui/GroupScreen.kt"), "code", 4, 2)])],
                Q("weak", 2, "LazyColumn shows the group names", "Where is the create dialog?", "I didn't get to it."), 0.8, 0.4, prs=[(13, "Group list", True)]),
            "S09-S3": S(
                [T("T1", "Create group dialog", "Dialog to create a group.",
                   ["Name input", "Creates the group", "Cancel"], 3, 2, "Partially Done", [1, 1, 0], 3,
                   """AlertDialog(onDismissRequest = onClose, confirmButton = { TextButton(onClick = { vm.addGroup(name); onClose() }) { Text("Create") } })""", carried="S09-S2-SYN-043-T1")],
                [(8, 20, "create group dialog", "T1", [(K("ui/GroupScreen.kt"), "code", 34, 0)]),
                 (10, 15, "wire addGroup", "T1", [(K("ui/ExpenseViewModel.kt"), "code", 7, 0)]),
                 (12, 19, "fix dialog dismiss", "T1", [(K("ui/GroupScreen.kt"), "code", 5, 3)])],
                Q("partial", 3, "the dialog calls vm.addGroup then closes", "Where is the Cancel button?", "Not added, the dismiss handler closes it."), 0.85, 0.7, prs=[(13, "Create group dialog", True)]),
        },
        "SYN-044": {
            "class": "no_specific_pattern", "scenario": "works alone on separate files (export feature); few shared files, no PR discussion; steady small deliveries",
            "S09-S1": S(
                [T("T1", "CSV export of expenses", "Export a group's expenses to CSV.",
                   ["Header row", "One row per expense", "Amount in decimal not cents"], 3, 2, "Done", [1, 1, 1], 4,
                   """fun toCsv(expenses: List<Expense>): String = buildString {
    appendLine("date,description,payer,amount")
    expenses.forEach { appendLine("${it.date},${it.description},${it.payer},${"%.2f".format(it.cents / 100.0)}") }
}   // commas in descriptions are not quoted""")],
                [(2, 15, "csv export", "T1", [(K("export/CsvExport.kt"), "code", 24, 0)]),
                 (5, 11, "export tests", "T1", [(KT("CsvExportTest.kt"), "test", 28, 0)]),
                 (9, 14, "decimal format", "T1", [(K("export/CsvExport.kt"), "code", 3, 2)])],
                Q("good", 4, "toCsv builds the text with buildString", "What if a description has a comma?", "It breaks the row. I need to quote fields."), 0.95, 1.0, prs=[(10, "CSV export", True)]),
            "S09-S2": S(
                [T("T1", "Share CSV from the balances screen", "A share button that sends the CSV.",
                   ["Share button on balances screen", "Quote fields with commas"], 3, 2, "Done", [1, 1], 4,
                   """private fun quote(s: String) = if (s.any { it == ',' || it == '"' || it == '\\n' }) "\\"" + s.replace("\\"", "\\"\\"") + "\\"" else s""")],
                [(2, 11, "quote csv fields", "T1", [(K("export/CsvExport.kt"), "code", 11, 2), (KT("CsvExportTest.kt"), "test", 17, 0)]),
                 (5, 15, "share button", "T1", [(K("ui/BalancesScreen.kt"), "code", 22, 0)]),
                 (8, 10, "share intent", "T1", [(K("ui/BalancesScreen.kt"), "code", 9, 0)])],
                Q("good", 4, "quote wraps fields containing commas, quotes or newlines", "How are double quotes inside a field written?", "Doubled, as the CSV standard says."), 0.95, 1.0,
                prs=[(9, "Share CSV", True)]),
            "S09-S3": S(
                [T("T1", "Dark theme", "Support the system dark theme.",
                   ["Colours for dark mode", "Follows system setting"], 2, 2, "Done", [1, 1], 4,
                   """val colors = if (isSystemInDarkTheme()) darkColorScheme() else lightColorScheme()""")],
                [(3, 14, "dark colour scheme", "T1", [(K("ui/MainActivity.kt"), "code", 12, 2)]),
                 (8, 11, "check contrast", "T1", [(K("ui/BalancesScreen.kt"), "code", 4, 2)])],
                Q("good", 4, "isSystemInDarkTheme decides the colour scheme", "What happens if the user changes the setting while the app runs?", "The composable recomposes with the new value."), 0.95, 0.9,
                prs=[(9, "Dark theme", True)]),
        },
        "SYN-045": {
            "class": "no_specific_pattern", "scenario": "hard algorithmic work, little code, high quality; a week without commits then a short burst; sprint 3 only reviews and one fix",
            "S09-S1": S(
                [T("T1", "Offline sync conflict handling", "When two phones edit the same expense, keep the newest and flag the conflict.",
                   ["Each expense has a version and updatedAt", "Newer update wins", "Conflicts are recorded", "Deleted expenses stay deleted"], 8, 5, "Partially Done", [1, 1, 0, 1], 4,
                   """fun merge(local: Expense, remote: Expense): MergeResult =
    when {
        local.version == remote.version -> MergeResult.Same
        local.deleted || remote.deleted -> MergeResult.Resolved(if (local.deleted) local else remote)
        local.updatedAt >= remote.updatedAt -> MergeResult.Conflict(winner = local, loser = remote)
        else -> MergeResult.Conflict(winner = remote, loser = local)
    }   // conflicts are returned but not stored""")],
                [(8, 14, "merge function", "T1", [(K("data/Repository.kt"), "code", 26, 0)]),
                 (11, 11, "version fields", "T1", [(K("data/Expense.kt"), "code", 5, 0)]),
                 (12, 16, "merge tests", "T1", [(KT("MergeTest.kt"), "test", 48, 0)])],
                Q("strong", 5, "merge keeps a deleted expense deleted", "Why does deletion win over a newer edit?", "Otherwise an expense one person removed could come back from another phone. A tombstone has to win."), 0.95, 0.95, prs=[(13, "Merge", True)]),
            "S09-S2": S(
                [T("T1", "Recurring expenses", "Expenses that repeat weekly or monthly.",
                   ["Recurrence rule on an expense", "Next occurrence computed", "Month ends handled (31st)", "Stops at end date"], 8, 5, "Done", [1, 1, 1, 1], 5,
                   """fun nextMonthly(from: LocalDate, dayOfMonth: Int): LocalDate {
    val next = from.plusMonths(1)
    return next.withDayOfMonth(minOf(dayOfMonth, next.lengthOfMonth()))
}""")],
                [(3, 15, "recurrence rule and next date", "T1", [(K("domain/Splitter.kt"), "code", 24, 0)]),
                 (9, 11, "month end tests", "T1", [(KT("SplitterTest.kt"), "test", 41, 0)]),
                 (10, 14, "end date", "T1", [(K("domain/Splitter.kt"), "code", 6, 1)])],
                Q("strong", 5, "nextMonthly clamps the day to the length of the next month", "What does it return for the 31st in February?", "The 28th or 29th. withDayOfMonth would throw, so I use the smaller of the two."), 0.95, 0.95, prs=[(11, "Recurring expenses", True)]),
            "S09-S3": S(
                [T("T1", "Conflict log screen", "Show conflicts recorded during sync.",
                   ["List of conflicts", "Which version won"], 3, 2, "Partially Done", [1, 0], 2,
                   """// list of MergeResult.Conflict, winner/loser not shown""")],
                [(12, 15, "fix merge order", "T1", [(K("data/Repository.kt"), "code", 2, 2)])],
                Q("good", 4, "the merge compares updatedAt with greater-or-equal", "What if both timestamps are the same?", "Local wins. A tie could use the device id, but I left it."), 0.95, 0.95,
                prs=[(13, "Merge fix", True)],
                reviews=[(4, "SYN-041", "COMMENTED", "The currency rate is a Double on the expense. Rounding of converted amounts should use the same cents rule as splitting, otherwise the sums disagree by a cent. Add a test with a rate of 3.3.", "substantive"),
                         (9, "SYN-042", "COMMENTED", "The release notes link is broken.", "brief")],
                comments=[(5, "SYN-041", "Good point, I'll add the rate-3.3 test. @SYN-045", 1, 1)]),
        },
    },
}
