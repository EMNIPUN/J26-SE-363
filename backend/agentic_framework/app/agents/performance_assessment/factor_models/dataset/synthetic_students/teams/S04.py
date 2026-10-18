"""Team S04: Clinic appointment scheduling (Spring Boot, Java). Four sprints. Students: deep backend with a mid-project
dip, two-burst worker, coordinator-reviewer, a free rider who is gradually replaced, and a hard-task / low-volume student."""
from _kit import T, Q, S


def J(p):
    return "src/main/java/clinic/" + p


def JT(p):
    return "src/test/java/clinic/" + p


TEAM = {
    "team": "S04", "domain": "Clinic appointment scheduling", "stack": "Spring Boot (Java)",
    "sprint_starts": {"S04-S1": "2026-01-12", "S04-S2": "2026-01-26", "S04-S3": "2026-02-09", "S04-S4": "2026-02-23"},
    "edges": [
        (J("controller/AppointmentController.java"), J("service/AppointmentService.java")), (J("controller/AppointmentController.java"), J("model/Appointment.java")),
        (J("controller/DoctorController.java"), J("service/SlotService.java")), (J("controller/DoctorController.java"), J("model/Doctor.java")),
        (J("controller/PatientController.java"), J("repository/PatientRepository.java")), (J("controller/PatientController.java"), J("model/Patient.java")),
        (J("service/AppointmentService.java"), J("repository/AppointmentRepository.java")), (J("service/AppointmentService.java"), J("service/SlotService.java")),
        (J("service/AppointmentService.java"), J("service/NotificationService.java")), (J("service/SlotService.java"), J("repository/DoctorRepository.java")),
        (J("service/SlotService.java"), J("repository/AppointmentRepository.java")), (J("service/NotificationService.java"), J("model/Patient.java")),
        (J("repository/AppointmentRepository.java"), J("model/Appointment.java")), (J("repository/DoctorRepository.java"), J("model/Doctor.java")),
        (J("repository/PatientRepository.java"), J("model/Patient.java")), (J("model/Appointment.java"), J("model/Doctor.java")), (J("model/Appointment.java"), J("model/Patient.java")),
        (J("config/SecurityConfig.java"), J("security/JwtFilter.java")), (J("security/JwtFilter.java"), J("repository/PatientRepository.java")),
        (J("controller/AppointmentController.java"), J("security/JwtFilter.java")),
    ],
    "students": {
        "SYN-016": {
            "class": "consistent_deep_contributor", "scenario": "deep backend work; productive in sprints 1, 2 and 4, a dip in sprint 3 (illness) with only a few commits",
            "S04-S1": S(
                [T("T1", "Appointment entity and booking service", "A patient books a slot with a doctor.",
                   ["Appointment links patient, doctor and start time", "Booking a free slot succeeds", "Booking a taken slot is refused", "Status starts as BOOKED"], 8, 5, "Done", [1, 1, 1, 1], 5,
                   """@Transactional
public Appointment book(long patientId, long doctorId, LocalDateTime start) {
    if (appointments.existsByDoctorIdAndStart(doctorId, start)) throw new SlotTakenException(doctorId, start);
    Appointment a = new Appointment(patientId, doctorId, start);
    a.setStatus(Status.BOOKED);
    return appointments.save(a);
}"""),
                 T("T2", "Cancel an appointment", "Patient cancels at least two hours before.",
                   ["Cancel sets status CANCELLED", "Refused within two hours of the start", "Slot becomes free again"], 3, 3, "Done", [1, 1, 0], 4,
                   """public void cancel(long id, LocalDateTime now) {
    Appointment a = appointments.findById(id).orElseThrow();
    if (a.getStart().minusHours(2).isBefore(now)) throw new TooLateException();
    a.setStatus(Status.CANCELLED);
}   // existsByDoctorIdAndStart still counts cancelled rows, so the slot stays blocked""")],
                [(0, 10, "appointment entity", "T1", [(J("model/Appointment.java"), "code", 41, 0)]),
                 (1, 14, "repository", "T1", [(J("repository/AppointmentRepository.java"), "code", 14, 0)]),
                 (2, 10, "booking service", "T1", [(J("service/AppointmentService.java"), "code", 44, 0)]),
                 (3, 15, "controller", "T1", [(J("controller/AppointmentController.java"), "code", 38, 0)]),
                 (5, 11, "slot taken exception and handler", "T1", [(J("service/AppointmentService.java"), "code", 12, 2), (J("controller/AppointmentController.java"), "code", 9, 0)]),
                 (6, 16, "booking tests", "T1", [(JT("AppointmentServiceTest.java"), "test", 63, 0)]),
                 (8, 10, "cancel", "T2", [(J("service/AppointmentService.java"), "code", 21, 0)]),
                 (9, 14, "cancel tests", "T2", [(JT("AppointmentServiceTest.java"), "test", 29, 0)]),
                 (11, 11, "status enum fix", "T1", [(J("model/Appointment.java"), "code", 5, 2)])],
                Q("strong", 5, "book checks existsByDoctorIdAndStart before saving", "Can two patients still book the same slot?",
                  "Yes, if both pass the check at once. A unique constraint on doctor and start would stop it. The check alone is not enough."),
                0.9, 0.9, prs=[(7, "Appointment booking", True), (12, "Cancel", True)]),
            "S04-S2": S(
                [T("T1", "Appointment reminders", "Email the patient 24 hours before.",
                   ["Scheduled job finds appointments in 24 hours", "Mail sent to the patient", "No duplicate reminders"], 5, 4, "Done", [1, 1, 1], 4,
                   """@Scheduled(cron = "0 0 * * * *")
public void remind() {
    LocalDateTime from = LocalDateTime.now().plusHours(24), to = from.plusHours(1);
    for (Appointment a : appointments.findBookedBetween(from, to)) {
        if (a.isReminderSent()) continue;
        mail.send(a.getPatient().getEmail(), "Appointment tomorrow", a.getStart().toString());
        a.setReminderSent(true);
    }
}"""),
                 T("T2", "Fix cancelled slots staying blocked", "Cancelled appointments free the slot.",
                   ["Booking a cancelled slot succeeds", "Test added"], 2, 2, "Done", [1, 1], 5,
                   """boolean existsByDoctorIdAndStartAndStatusNot(long doctorId, LocalDateTime start, Status status);""", carried="S04-S1-SYN-016-T2")],
                [(0, 10, "repo query ignoring cancelled", "T2", [(J("repository/AppointmentRepository.java"), "code", 4, 1), (J("service/AppointmentService.java"), "code", 3, 3)]),
                 (1, 15, "test for cancelled slot", "T2", [(JT("AppointmentServiceTest.java"), "test", 18, 0)]),
                 (3, 11, "reminder query", "T1", [(J("repository/AppointmentRepository.java"), "code", 9, 0)]),
                 (4, 14, "scheduled reminder", "T1", [(J("service/NotificationService.java"), "code", 36, 0)]),
                 (6, 10, "reminderSent flag", "T1", [(J("model/Appointment.java"), "code", 6, 0), (J("service/NotificationService.java"), "code", 5, 1)]),
                 (8, 15, "reminder tests", "T1", [(JT("NotificationServiceTest.java"), "test", 41, 0)]),
                 (10, 11, "mail failure does not stop others", "T1", [(J("service/NotificationService.java"), "code", 9, 3)])],
                Q("strong", 5, "remind skips appointments with reminderSent set", "What if the mail call throws halfway through the loop?",
                  "Then the flag is not set for that one and the rest would not run. I wrapped the send in try-catch so one failure does not stop the others, and the flag stays false so it retries next hour."),
                0.9, 0.9, prs=[(5, "Cancelled slots", True), (11, "Reminders", True)],
                reviews=[(9, "SYN-018", "COMMENTED", "ok", "approval")]),
            "S04-S3": S(
                [T("T1", "Appointment history for patients", "Patients list their past appointments.",
                   ["GET /patients/{id}/appointments", "Newest first", "Includes status"], 3, 2, "Done", [1, 1, 1], 4,
                   """List<Appointment> findByPatientIdOrderByStartDesc(long patientId);""")],
                [(4, 15, "history query", "T1", [(J("repository/AppointmentRepository.java"), "code", 3, 0), (J("controller/PatientController.java"), "code", 17, 0)]),
                 (9, 11, "history test", "T1", [(JT("AppointmentServiceTest.java"), "test", 22, 0)])],
                Q("good", 4, "findByPatientIdOrderByStartDesc derives the query from its name", "How does Spring build that query?",
                  "From the method name. It parses findBy, the field, and OrderBy and writes the JPQL."),
                0.95, 0.9, prs=[(10, "Appointment history", True)]),
            "S04-S4": S(
                [T("T1", "Rescheduling", "Move an appointment to another free slot.",
                   ["Reschedule keeps the same appointment id", "Refused if the new slot is taken", "Refused within two hours of the original start", "Patient notified"], 8, 5, "Done", [1, 1, 1, 0], 4,
                   """@Transactional
public Appointment reschedule(long id, LocalDateTime newStart, LocalDateTime now) {
    Appointment a = appointments.findById(id).orElseThrow();
    if (a.getStart().minusHours(2).isBefore(now)) throw new TooLateException();
    if (appointments.existsByDoctorIdAndStartAndStatusNot(a.getDoctorId(), newStart, Status.CANCELLED)) throw new SlotTakenException(a.getDoctorId(), newStart);
    a.setStart(newStart);
    return a;
}   // notification not sent""")],
                [(0, 10, "reschedule service", "T1", [(J("service/AppointmentService.java"), "code", 27, 0)]),
                 (1, 15, "reschedule endpoint", "T1", [(J("controller/AppointmentController.java"), "code", 16, 0)]),
                 (2, 11, "tests", "T1", [(JT("AppointmentServiceTest.java"), "test", 48, 0)]),
                 (4, 14, "same slot edge case", "T1", [(J("service/AppointmentService.java"), "code", 5, 1), (JT("AppointmentServiceTest.java"), "test", 11, 0)]),
                 (6, 10, "doc comment", None, [(J("service/AppointmentService.java"), "code", 8, 0)]),
                 (8, 16, "unique constraint migration", "T1", [(J("model/Appointment.java"), "code", 4, 0)]),
                 (10, 11, "fix error message", "T1", [(J("controller/AppointmentController.java"), "code", 2, 2)])],
                Q("strong", 5, "reschedule re-runs the two-hour and slot-taken checks", "Why is the method @Transactional?",
                  "So the read of the appointment and the change to its start happen in one transaction. Without it a concurrent change between the read and the write is possible."),
                0.95, 0.9, prs=[(5, "Reschedule", True), (11, "Constraint", True)]),
        },
        "SYN-017": {
            "class": "burst_worker", "scenario": "intense bursts at the start and end of each sprint with a quiet middle; output is solid",
            "S04-S1": S(
                [T("T1", "Doctor entity and availability", "Doctors have working hours per weekday.",
                   ["Doctor with name and specialty", "Working hours per weekday", "List doctors by specialty"], 5, 4, "Done", [1, 1, 1], 4,
                   """@Entity public class Doctor {
    @Id @GeneratedValue Long id;
    String name, specialty;
    @ElementCollection Map<DayOfWeek, TimeRange> hours = new EnumMap<>(DayOfWeek.class);
}""")],
                [(0, 10, "doctor entity", "T1", [(J("model/Doctor.java"), "code", 52, 0)]),
                 (0, 15, "doctor repository", "T1", [(J("repository/DoctorRepository.java"), "code", 12, 0)]),
                 (1, 11, "doctor controller", "T1", [(J("controller/DoctorController.java"), "code", 44, 0)]),
                 (1, 17, "filter by specialty", "T1", [(J("repository/DoctorRepository.java"), "code", 3, 0), (J("controller/DoctorController.java"), "code", 9, 0)]),
                 (11, 10, "working hours validation", "T1", [(J("model/Doctor.java"), "code", 21, 4)]),
                 (12, 16, "doctor tests", "T1", [(JT("DoctorControllerTest.java"), "test", 58, 0)])],
                Q("good", 4, "Doctor stores working hours as a map keyed by weekday", "Why an EnumMap?",
                  "Keys are weekdays, an enum, and EnumMap is compact and keeps them in order."),
                0.9, 0.9, prs=[(2, "Doctor API", True), (13, "Hours validation", True)]),
            "S04-S2": S(
                [T("T1", "Free slot calculation", "List free slots of a doctor for a day.",
                   ["Slots are 20 minutes", "Within the doctor's working hours", "Excludes booked appointments", "Excludes past slots for today"], 8, 5, "Partially Done", [1, 1, 1, 0], 4,
                   """public List<LocalTime> freeSlots(long doctorId, LocalDate day) {
    Doctor d = doctors.findById(doctorId).orElseThrow();
    TimeRange h = d.getHours().get(day.getDayOfWeek());
    if (h == null) return List.of();
    Set<LocalTime> taken = appointments.startsOn(doctorId, day).stream().map(a -> a.getStart().toLocalTime()).collect(toSet());
    List<LocalTime> out = new ArrayList<>();
    for (LocalTime t = h.start(); t.plusMinutes(20).compareTo(h.end()) <= 0; t = t.plusMinutes(20)) if (!taken.contains(t)) out.add(t);
    return out;
}   // today's past slots are not removed""")],
                [(1, 10, "slot service", "T1", [(J("service/SlotService.java"), "code", 48, 0)]),
                 (1, 16, "startsOn query", "T1", [(J("repository/AppointmentRepository.java"), "code", 6, 0)]),
                 (2, 12, "slots endpoint", "T1", [(J("controller/DoctorController.java"), "code", 14, 0)]),
                 (3, 15, "slot tests", "T1", [(JT("SlotServiceTest.java"), "test", 64, 0)]),
                 (11, 10, "fix last slot off by one", "T1", [(J("service/SlotService.java"), "code", 3, 3), (JT("SlotServiceTest.java"), "test", 12, 0)]),
                 (12, 14, "cancelled appointments free slots", "T1", [(J("repository/AppointmentRepository.java"), "code", 2, 2)])],
                Q("good", 4, "freeSlots steps through working hours in 20 minute steps", "What is the compareTo condition for?",
                  "It makes sure a slot ends before the working hours end, so the last slot is not cut."),
                0.85, 0.9, prs=[(4, "Free slots", True), (13, "Slot fixes", True)]),
            "S04-S3": S(
                [T("T1", "Doctor leave days", "A doctor can mark days as leave, which removes those slots.",
                   ["Leave day entity", "No free slots on leave days", "Booking on a leave day refused"], 5, 3, "Done", [1, 1, 0], 3,
                   """public List<LocalTime> freeSlots(long doctorId, LocalDate day) {
    if (leave.existsByDoctorIdAndDay(doctorId, day)) return List.of();
    ...
}   // book() does not check leave, only the slots list does""")],
                [(0, 10, "leave entity", "T1", [(J("model/Doctor.java"), "code", 18, 0)]),
                 (0, 16, "leave in slot service", "T1", [(J("service/SlotService.java"), "code", 11, 1)]),
                 (1, 11, "leave endpoint", "T1", [(J("controller/DoctorController.java"), "code", 19, 0)]),
                 (11, 10, "leave tests", "T1", [(JT("SlotServiceTest.java"), "test", 31, 0)]),
                 (12, 15, "format", None, [(J("controller/DoctorController.java"), "code", 4, 4)])],
                Q("partial", 3, "freeSlots returns nothing on leave days", "Where is the leave check for booking itself?",
                  "Only in the slots list so far, the booking method does not check it."),
                0.9, 0.9, prs=[(2, "Leave days", True)]),
            "S04-S4": S(
                [T("T1", "Role based access", "Patients see only their own appointments; staff see all.",
                   ["JWT carries the role", "Patients cannot read other patients' appointments", "Staff endpoints require STAFF", "Tests for each rule"], 8, 5, "Partially Done", [1, 1, 1, 0], 3,
                   """http.authorizeHttpRequests(a -> a
    .requestMatchers("/staff/**").hasRole("STAFF")
    .requestMatchers("/patients/{id}/**").access((auth, ctx) -> new AuthorizationDecision(auth.get().getName().equals(ctx.getVariables().get("id"))))
    .anyRequest().authenticated());""")],
                [(0, 10, "security config", "T1", [(J("config/SecurityConfig.java"), "code", 39, 0)]),
                 (0, 16, "jwt filter reads role", "T1", [(J("security/JwtFilter.java"), "code", 27, 5)]),
                 (1, 12, "patient can only read own", "T1", [(J("config/SecurityConfig.java"), "code", 14, 3)]),
                 (2, 14, "staff routes", "T1", [(J("controller/AppointmentController.java"), "code", 13, 0)]),
                 (11, 10, "security test for patient route", "T1", [(JT("SecurityTest.java"), "test", 33, 0)]),
                 (12, 15, "fix role prefix", "T1", [(J("security/JwtFilter.java"), "code", 2, 2)])],
                Q("good", 4, "the patient rule compares the path id with the authenticated name", "What would break if a patient's name is not their id?",
                  "The rule compares the auth name to the id, so the token subject has to be the id. If it were an email the check would always fail."),
                0.9, 0.9, prs=[(3, "Security", True), (13, "Role fixes", True)]),
        },
        "SYN-018": {
            "class": "reviewer_coordinator", "scenario": "coordinates the sprint: board, reviews, merges; writes docs and small fixes; reviews are detailed except when overloaded",
            "S04-S1": S(
                [T("T1", "Project skeleton and conventions", "Spring Boot project, package layout and code style.",
                   ["Package layout documented", "Formatter config", "Pull request template"], 2, 2, "Done", [1, 1, 1], 4,
                   "<!-- .github/pull_request_template.md -->\n## What changed\n## How to test\n## Checklist\n- [ ] tests added\n- [ ] no secrets")],
                [(0, 9, "project skeleton", "T1", [("pom.xml", "config_or_docs", 62, 0), ("README.md", "config_or_docs", 35, 0)]),
                 (1, 10, "pr template and formatter", "T1", [(".github/pull_request_template.md", "config_or_docs", 12, 0), (".editorconfig", "config_or_docs", 9, 0)]),
                 (4, 16, "patient entity", None, [(J("model/Patient.java"), "code", 24, 0)])],
                Q("good", 4, "Patient entity has name, email and phone", "Why is email unique?",
                  "It identifies the patient when they log in, and two accounts with the same email would clash."),
                0.95, 0.85, mfo=5,
                reviews=[(5, "SYN-016", "COMMENTED", "book() checks that the slot is free and then saves, but two requests at the same time can both pass. Add a unique constraint on doctor and start so the database rejects the second one, and handle the exception.", "substantive"),
                         (6, "SYN-016", "COMMENTED", "SlotTakenException should map to 409 in the controller advice, right now it will be a 500.", "substantive"),
                         (11, "SYN-017", "APPROVED", "Hours validation reads well. Maybe a test for an end time before the start time.", "brief"),
                         (12, "SYN-020", "COMMENTED", "Please explain the approach in the PR description, I cannot tell why the interval is built this way.", "brief")],
                comments=[(7, "SYN-016", "Added the handler, thanks for the 409 point. @SYN-018", 1, 1)]),
            "S04-S2": S(
                [T("T1", "Integration test setup", "Tests run against an in-memory database.",
                   ["H2 profile for tests", "Sample data loader", "Tests run in CI"], 3, 3, "Done", [1, 1, 1], 4,
                   """@SpringBootTest @ActiveProfiles("test")
class AppointmentIT {
    @Autowired AppointmentService service;
    @Test void bookingTwiceFails() { service.book(1, 1, SLOT); assertThrows(SlotTakenException.class, () -> service.book(2, 1, SLOT)); }
}"""),
                 T("T2", "Patient registration endpoint", "Register a patient.",
                   ["POST /patients creates a patient", "Duplicate email refused"], 3, 2, "Done", [1, 0], 3,
                   """@PostMapping public Patient register(@RequestBody Patient p) { return patients.save(p); }   // duplicate email gives a database error, not a clean 409""")],
                [(1, 10, "h2 test profile", "T1", [("src/test/resources/application-test.properties", "config_or_docs", 11, 0)]),
                 (2, 14, "integration test", "T1", [(JT("AppointmentIT.java"), "test", 36, 0)]),
                 (4, 11, "patient controller", "T2", [(J("controller/PatientController.java"), "code", 25, 0)]),
                 (4, 15, "ci workflow runs tests", "T1", [(".github/workflows/ci.yml", "config_or_docs", 20, 0)])],
                Q("good", 4, "the integration test books the same slot twice", "Why use H2 for tests?",
                  "It starts fast and needs no install. But it is not exactly MySQL, so some queries could behave differently in production."),
                0.95, 0.85, mfo=4,
                reviews=[(3, "SYN-016", "APPROVED", "Reminder job: mailing a patient fails if email is null, add a guard. Also the flag is set after the mail call, so a crash between the two sends twice. Acceptable for now, note it in the README.", "substantive"),
                         (4, "SYN-017", "CHANGES_REQUESTED", "freeSlots loops with a LocalTime and plusMinutes, near midnight plusMinutes wraps to the next day and the loop never ends. Compare with the end first or use durations.", "substantive"),
                         (7, "SYN-020", "COMMENTED", "The interval merge sorts on every call, fine for now. Which test covers two overlapping bookings?", "substantive"),
                         (10, "SYN-016", "APPROVED", "good", "approval")],
                comments=[(5, "SYN-017", "You are right about midnight, I will fix it. @SYN-018", 1, 1), (8, "SYN-020", "Added a test for the overlap case.", 1, 0)]),
            "S04-S3": S(
                [T("T1", "Sprint demo preparation", "Seed data, demo script and a short user guide.",
                   ["Seed script creates doctors and patients", "Demo script of the main flow", "User guide"], 3, 3, "Done", [1, 1, 1], 4,
                   "INSERT INTO doctor (name, specialty) VALUES ('Dr. Example One', 'Cardiology'), ('Dr. Example Two', 'Paediatrics');")],
                [(8, 10, "seed data", "T1", [("src/main/resources/data.sql", "config_or_docs", 28, 0)]),
                 (9, 15, "demo script", "T1", [("docs/demo.md", "config_or_docs", 41, 0)]),
                 (11, 11, "user guide", "T1", [("docs/user-guide.md", "config_or_docs", 52, 0)])],
                Q("partial", 3, "data.sql inserts sample doctors", "What happens to the seed data on each restart?",
                  "I think it is inserted again. We may need to clear the table first."),
                0.95, 0.85, mfo=3,
                reviews=[(3, "SYN-017", "COMMENTED", "Leave check is only in freeSlots, book() accepts a leave day. The rule should live in one place and booking must call it.", "substantive"),
                         (4, "SYN-016", "APPROVED", "History is sorted newest first as required.", "brief"),
                         (9, "SYN-020", "COMMENTED", "Looks good to me, merge when CI is green.", "brief")],
                comments=[(5, "SYN-017", "Agreed, I'll move it into a shared validator. @SYN-018", 1, 1)]),
            "S04-S4": S(
                [T("T1", "Release checklist and deployment notes", "How to build, configure and run in production.",
                   ["Environment variables documented", "Database setup steps", "Rollback notes"], 3, 3, "Done", [1, 1, 0], 3,
                   "## Production\nSet SPRING_DATASOURCE_URL, JWT_SECRET. Run `mvn -Pprod package`.\nRollback: redeploy the previous jar.")],
                [(9, 10, "deployment notes", "T1", [("docs/deployment.md", "config_or_docs", 47, 0)]),
                 (11, 14, "prod profile", "T1", [("src/main/resources/application-prod.properties", "config_or_docs", 14, 0)])],
                Q("partial", 3, "application-prod.properties reads secrets from the environment", "Why not put the JWT secret in the file?",
                  "Because the file is in git. Anyone with the repo would have the secret."),
                0.95, 0.85, mfo=5,
                reviews=[(2, "SYN-016", "COMMENTED", "reschedule() does not tell the patient. The requirement says the patient is notified, call NotificationService after the change and add a test that checks the mail is sent only when the new slot was saved.", "substantive"),
                         (3, "SYN-017", "CHANGES_REQUESTED", "The patient rule compares the auth name with the path id. If a patient logs in with their email this never matches and they are locked out of their own data. Use the id claim from the token.", "substantive"),
                         (5, "SYN-020", "COMMENTED", "Please add a short comment on why the interval tree is rebuilt, and a test with three overlapping bookings.", "substantive"),
                         (10, "SYN-016", "APPROVED", "lgtm", "approval"),
                         (11, "SYN-017", "APPROVED", "ok", "approval")],
                comments=[(4, "SYN-016", "Will add the notification today. @SYN-018", 1, 1), (6, "SYN-020", "Added the comment and the test.", 1, 0)]),
        },
        "SYN-019": {
            "class": "free_rider", "scenario": "nothing in sprint 1; sprint 2 task finished by a teammate; sprint 3 one tiny commit; then leaves",
            "S04-S1": S(
                [T("T1", "Patient registration", "Register and update patients.",
                   ["Register patient", "Update profile", "Validate email"], 5, 3, "To Do", [0, 0, 0], 1)],
                [], Q("weak", 1, "(no code this sprint)", "How is a patient saved?", "With the repository save I think."), 0.0, 0.0),
            "S04-S2": S(
                [T("T1", "Patient registration", "Register and update patients.",
                   ["Register patient", "Update profile", "Validate email"], 5, 3, "Done", [0, 1, 0], 2,
                   """@PostMapping public Patient register(@RequestBody Patient p) { return patients.save(p); }   // written by a teammate""",
                   by="SYN-018", carried="S04-S1-SYN-019-T1")],
                [], Q("weak", 2, "(registration endpoint written by a teammate)", "What validates the email?", "I don't know, the annotation maybe."), 0.0, 0.0),
            "S04-S3": S(
                [T("T1", "Write patient tests", "Unit tests for the patient controller.",
                   ["Register test", "Update test", "Duplicate email test"], 3, 3, "Partially Done", [1, 0, 0], 2,
                   """@Test void registerReturnsPatient() { assertNotNull(controller.register(new Patient("A", "a@x.lk"))); }""")],
                [(12, 20, "patient controller test", "T1", [(JT("PatientControllerTest.java"), "test", 15, 0)])],
                Q("weak", 2, "registerReturnsPatient", "What does assertNotNull prove here?", "That it returned something."), 1.0, 0.5, prs=[(13, "Patient test", True)]),
        },
        "SYN-020": {
            "class": "no_specific_pattern", "scenario": "hard algorithmic tasks with little code; reliable but slow; sprint 4 an easy task with a lot of code",
            "S04-S1": S(
                [T("T1", "Overlap detection for back-to-back bookings", "Detect when a requested appointment overlaps another for the same doctor.",
                   ["Appointments have a duration", "Overlap detected including partial overlaps", "Adjacent slots do not overlap"], 8, 5, "Done", [1, 1, 1], 5,
                   """static boolean overlaps(Appointment a, LocalDateTime start, Duration d) {
    LocalDateTime aEnd = a.getStart().plus(a.getDuration()), end = start.plus(d);
    return start.isBefore(aEnd) && a.getStart().isBefore(end);   // adjacent slots: end == start is not an overlap
}""")],
                [(3, 14, "duration field", "T1", [(J("model/Appointment.java"), "code", 7, 0)]),
                 (6, 11, "overlap check", "T1", [(J("service/AppointmentService.java"), "code", 16, 0)]),
                 (9, 15, "overlap tests with partial and adjacent cases", "T1", [(JT("OverlapTest.java"), "test", 52, 0)])],
                Q("strong", 5, "overlaps compares start with the other end and the other start with the end", "Why isBefore on both and not <=?",
                  "Two appointments that touch, one ending at 10:00 and one starting at 10:00, are not overlapping. Strict isBefore treats that as free. I wrote a test for exactly that."),
                0.95, 0.95, prs=[(10, "Overlap detection", True)]),
            "S04-S2": S(
                [T("T1", "Merge overlapping unavailable intervals", "Combine leave, lunch and training blocks into non-overlapping intervals.",
                   ["Sort intervals by start", "Merge overlapping and touching ones", "Result has no overlaps", "Handles an empty list"], 8, 5, "Done", [1, 1, 1, 1], 5,
                   """static List<Interval> merge(List<Interval> in) {
    List<Interval> sorted = in.stream().sorted(comparing(Interval::start)).toList(), out = new ArrayList<>();
    for (Interval i : sorted) {
        if (!out.isEmpty() && !i.start().isAfter(out.get(out.size() - 1).end())) out.set(out.size() - 1, out.get(out.size() - 1).merge(i));
        else out.add(i);
    }
    return out;
}""")],
                [(4, 15, "interval record and merge", "T1", [(J("service/SlotService.java"), "code", 33, 0)]),
                 (8, 11, "merge tests", "T1", [(JT("SlotServiceTest.java"), "test", 44, 0)])],
                Q("strong", 5, "merge sorts by start and extends the last interval", "What is the time complexity?",
                  "O(n log n) for the sort, the loop after it is linear."),
                0.95, 0.95, prs=[(9, "Interval merge", True)]),
            "S04-S3": S(
                [T("T1", "Waiting list when a slot is taken", "Join a waiting list; the first person is offered a cancelled slot.",
                   ["Join the list for a doctor and day", "On cancel the first waiting patient is offered the slot", "Offer expires after 15 minutes", "A patient is not on the list twice"], 8, 5, "Partially Done", [1, 0, 0, 1], 2,
                   """public void join(long patientId, long doctorId, LocalDate day) {
    if (waiting.existsByPatientIdAndDoctorIdAndDay(patientId, doctorId, day)) return;
    waiting.save(new WaitingEntry(patientId, doctorId, day, Instant.now()));
}   // offering and expiry not implemented""")],
                [(8, 14, "waiting list entity and join", "T1", [(J("service/AppointmentService.java"), "code", 24, 0), (J("model/Appointment.java"), "code", 12, 0)]),
                 (12, 11, "no duplicate entries", "T1", [(J("service/AppointmentService.java"), "code", 5, 0)])],
                Q("partial", 3, "join returns silently if the patient is already waiting", "Why return instead of throwing?",
                  "So joining twice is harmless. But the caller does not know it was a duplicate."),
                0.9, 0.9, prs=[(13, "Waiting list", True)]),
            "S04-S4": S(
                [T("T1", "Admin export to CSV", "Export all appointments of a month as CSV.",
                   ["GET /staff/export?month=", "Header row", "Escapes commas in names"], 3, 2, "Done", [1, 1, 1], 4,
                   """public String csv(YearMonth m) {
    StringBuilder sb = new StringBuilder("id,patient,doctor,start,status\\n");
    for (Appointment a : appointments.inMonth(m.atDay(1), m.atEndOfMonth()))
        sb.append(a.getId()).append(',').append(esc(a.getPatient().getName())).append(',').append(esc(a.getDoctor().getName())).append(',').append(a.getStart()).append(',').append(a.getStatus()).append('\\n');
    return sb.toString();
}"""),
                 T("T2", "Seat/room legend", "Label all statuses with colours on the staff page.",
                   ["Legend component", "Colour per status"], 2, 1, "Done", [1, 1], 3, "BOOKED=green CANCELLED=grey NO_SHOW=red")],
                [(1, 10, "csv export", "T1", [(J("controller/AppointmentController.java"), "code", 47, 0)]),
                 (1, 15, "csv escape helper", "T1", [(J("service/AppointmentService.java"), "code", 18, 0)]),
                 (2, 11, "inMonth query", "T1", [(J("repository/AppointmentRepository.java"), "code", 6, 0)]),
                 (3, 10, "export test", "T1", [(JT("AppointmentServiceTest.java"), "test", 36, 0)]),
                 (4, 16, "status legend constants", "T2", [(J("model/Appointment.java"), "code", 9, 0)]),
                 (5, 11, "controller cleanup", None, [(J("controller/AppointmentController.java"), "code", 14, 21)])],
                Q("good", 4, "csv escapes names containing commas", "What does esc do with a double quote?",
                  "It should double it and wrap the field in quotes. I tested a comma, not a quote."),
                0.9, 0.9, prs=[(6, "CSV export", True)]),
        },
    },
}
