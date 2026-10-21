"""Team S01: Campus Event Booking (Node/Express API + React). Five students, two sprints, written one by one.

Conventions (read by ../materialize.py):
  commit  = (day 0-13, hour, message, task key or None, [(path, kind, lines_added, lines_deleted), ...])
  review  = (day, pr_author, state, text, tier)       tier: substantive | brief | approval
  comment = (day, pr_author, text, is_reply, mentions)  discussion comments on pull requests
  pr      = (day, title, merged)
  Task keys are local to the student's sprint (T1, T2, ...). `met[i]` is 1 when the code below satisfies criterion i.
  `rating` is the 1-5 fulfilment of the task as it would be judged from the code (criteria met, completeness).
Each student has a class and a scenario, and at least one flaw: nobody is perfect.
"""

TEAM = {
    "team": "S01",
    "domain": "Campus event booking",
    "stack": "Node/Express API and React web app",
    "sprint_starts": {"S01-S1": "2026-02-02", "S01-S2": "2026-02-16"},
    "edges": [  # importer -> imported
        ("api/server.js", "api/routes/events.js"), ("api/server.js", "api/routes/bookings.js"), ("api/server.js", "api/routes/auth.js"),
        ("api/routes/events.js", "api/controllers/eventController.js"), ("api/routes/events.js", "api/middleware/auth.js"),
        ("api/routes/bookings.js", "api/controllers/bookingController.js"), ("api/routes/bookings.js", "api/middleware/auth.js"),
        ("api/routes/bookings.js", "api/middleware/validate.js"), ("api/routes/auth.js", "api/controllers/authController.js"),
        ("api/controllers/eventController.js", "api/models/Event.js"),
        ("api/controllers/bookingController.js", "api/models/Booking.js"), ("api/controllers/bookingController.js", "api/models/Event.js"),
        ("api/controllers/bookingController.js", "api/utils/capacity.js"), ("api/controllers/bookingController.js", "api/utils/email.js"),
        ("api/controllers/authController.js", "api/models/User.js"), ("api/middleware/auth.js", "api/models/User.js"),
        ("api/utils/capacity.js", "api/models/Booking.js"),
        ("api/tests/booking.test.js", "api/controllers/bookingController.js"),
        ("web/src/App.jsx", "web/src/pages/EventList.jsx"), ("web/src/App.jsx", "web/src/pages/EventDetail.jsx"),
        ("web/src/App.jsx", "web/src/pages/BookingForm.jsx"), ("web/src/App.jsx", "web/src/pages/MyBookings.jsx"),
        ("web/src/App.jsx", "web/src/pages/AdminDashboard.jsx"), ("web/src/App.jsx", "web/src/components/Navbar.jsx"),
        ("web/src/pages/EventList.jsx", "web/src/api/client.js"), ("web/src/pages/EventList.jsx", "web/src/components/EventCard.jsx"),
        ("web/src/pages/EventDetail.jsx", "web/src/api/client.js"), ("web/src/pages/BookingForm.jsx", "web/src/api/client.js"),
        ("web/src/pages/MyBookings.jsx", "web/src/api/client.js"), ("web/src/pages/AdminDashboard.jsx", "web/src/api/client.js"),
        ("web/src/pages/AdminDashboard.jsx", "web/src/components/EventCard.jsx"),
    ],
    "students": {
        # ------------------------------------------------------------------------------------------------------------------
        "SYN-001": {
            "class": "consistent_deep_contributor", "scenario": "solid backend coder who never reviews; one task left partial",
            "S01-S1": {
                "tasks": [
                    dict(key="T1", title="Booking model and create-booking endpoint", desc="Store a booking for an event and a user and expose POST /bookings.",
                         ac=["POST /bookings stores event, user and seats", "Requests without a logged-in user are rejected", "Returns 201 with the created booking"],
                         sp=5, sub=4, status="Done", met=[1, 1, 1], rating=4,
                         code="""// api/controllers/bookingController.js
exports.createBooking = async (req, res) => {
  const { eventId, seats } = req.body;
  if (!req.user) return res.status(401).json({ error: 'login required' });
  const booking = await Booking.create({ event: eventId, user: req.user.id, seats });
  res.status(201).json(booking);
};"""),
                    dict(key="T2", title="Seat capacity check", desc="A booking must not take more seats than are left for the event.",
                         ac=["Reject a booking that asks for more seats than are left", "Seats left are calculated from existing bookings", "Return 409 with a clear message"],
                         sp=3, sub=3, status="Done", met=[1, 1, 0], rating=3,
                         code="""// api/utils/capacity.js
exports.seatsLeft = async (event) => {
  const booked = await Booking.aggregate([
    { $match: { event: event._id } },
    { $group: { _id: null, total: { $sum: '$seats' } } },
  ]);
  return event.capacity - (booked[0]?.total || 0);
};
// controller: if (seats > left) return res.status(400).json({ error: 'not enough seats' });"""),
                    dict(key="T3", title="Cancel a booking", desc="Let a user cancel their own booking and give the seats back.",
                         ac=["DELETE /bookings/:id cancels the user's own booking", "A booking cannot be cancelled after the event has started", "Seats are released"],
                         sp=3, sub=3, status="Partially Done", met=[1, 0, 1], rating=3,
                         code="""exports.cancelBooking = async (req, res) => {
  const booking = await Booking.findOne({ _id: req.params.id, user: req.user.id });
  if (!booking) return res.status(404).json({ error: 'not found' });
  await booking.deleteOne();            // seats are freed because they are derived from bookings
  res.status(204).end();
};   // TODO: refuse once event.startsAt has passed"""),
                ],
                "commits": [
                    (0, 10, "add Booking model", "T1", [("api/models/Booking.js", "code", 28, 0)]),
                    (0, 15, "booking route and controller skeleton", "T1", [("api/routes/bookings.js", "code", 14, 0), ("api/controllers/bookingController.js", "code", 22, 0)]),
                    (1, 11, "create booking endpoint", "T1", [("api/controllers/bookingController.js", "code", 35, 4)]),
                    (2, 14, "login required for bookings", "T1", [("api/controllers/bookingController.js", "code", 9, 2), ("api/middleware/auth.js", "code", 6, 0)]),
                    (2, 16, "temporary login endpoint so bookings can be tested", None, [("api/controllers/authController.js", "code", 24, 0)]),
                    (3, 10, "seats left calculation", "T2", [("api/utils/capacity.js", "code", 31, 0)]),
                    (4, 16, "use the capacity check when booking", "T2", [("api/controllers/bookingController.js", "code", 18, 5), ("api/utils/capacity.js", "code", 7, 3)]),
                    (6, 11, "tests for create booking and capacity", "T2", [("api/tests/booking.test.js", "test", 64, 0)]),
                    (7, 15, "cancel booking handler", "T3", [("api/controllers/bookingController.js", "code", 26, 0), ("api/routes/bookings.js", "code", 3, 0)]),
                    (9, 10, "fix capacity off by one", "T2", [("api/utils/capacity.js", "code", 4, 4), ("api/tests/booking.test.js", "test", 12, 2)]),
                    (10, 17, "release seats on cancel", "T3", [("api/controllers/bookingController.js", "code", 11, 2)]),
                ],
                "reviews": [], "comments": [(6, "SYN-001", "Thanks, the 400 should be a 409; I will change it next sprint.", 1, 0)],
                "prs": [(5, "Booking create and capacity check", True), (11, "Cancel booking", True)],
                "quiz": dict(tier="good", rating=4, snippet="seatsLeft: event.capacity minus the sum of seats over bookings",
                             question="Why are seats left computed from the bookings instead of stored on the event?",
                             answer="So the number cannot get out of sync when a booking is cancelled. It is slower for big events, and two requests at the same moment can still both pass the check."),
                "ko": dict(survival=0.85, primary_owner=0.9),
            },
            "S01-S2": {
                "tasks": [
                    dict(key="T1", title="Booking confirmation email", desc="Send an email to the user when a booking is created.",
                         ac=["An email is sent after a booking is stored", "The email lists event name, date and seats", "A failure to send does not undo the booking"],
                         sp=3, sub=3, status="Done", met=[1, 1, 1], rating=4,
                         code="""// api/utils/email.js
exports.sendConfirmation = async (user, event, booking) => {
  try {
    await transporter.sendMail({ to: user.email, subject: `Booked: ${event.name}`,
      text: `${booking.seats} seat(s) for ${event.name} on ${event.startsAt.toDateString()}` });
  } catch (err) { console.error('confirmation email failed', err.message); }
};"""),
                    dict(key="T2", title="List my bookings", desc="GET /bookings/mine returns the logged-in user's bookings with the event details.",
                         ac=["Returns only the current user's bookings", "Each booking includes event name and date", "Newest first"],
                         sp=2, sub=2, status="Done", met=[1, 1, 1], rating=5,
                         code="""exports.myBookings = async (req, res) => {
  const list = await Booking.find({ user: req.user.id }).populate('event', 'name startsAt').sort({ createdAt: -1 });
  res.json(list);
};"""),
                    dict(key="T3", title="Paginate bookings", desc="Add page and limit to the bookings list.",
                         ac=["page and limit query parameters are honoured", "The response includes the total count"],
                         sp=2, sub=2, status="To Do", met=[0, 0], rating=1, code=""),
                ],
                "commits": [
                    (0, 11, "email helper", "T1", [("api/utils/email.js", "code", 29, 0)]),
                    (1, 14, "send confirmation after booking", "T1", [("api/controllers/bookingController.js", "code", 8, 1), ("api/utils/email.js", "code", 5, 1)]),
                    (3, 10, "my bookings endpoint", "T2", [("api/controllers/bookingController.js", "code", 14, 0), ("api/routes/bookings.js", "code", 2, 0)]),
                    (4, 15, "sort and populate my bookings", "T2", [("api/controllers/bookingController.js", "code", 5, 2)]),
                    (7, 10, "tests for email failure and my bookings", "T1", [("api/tests/booking.test.js", "test", 41, 0)]),
                    (8, 16, "cleanup", None, [("api/controllers/bookingController.js", "code", 6, 11)]),
                    (11, 13, "docs for booking endpoints", None, [("README.md", "config_or_docs", 38, 0)]),
                ],
                "reviews": [], "comments": [],
                "prs": [(4, "Confirmation email", True), (9, "My bookings", True)],
                "quiz": dict(tier="strong", rating=5, snippet="sendConfirmation catches mail errors",
                             question="Why does sendConfirmation catch its own errors?",
                             answer="The booking is already saved. If the mail server is down the user should still have the booking, so I log the failure and do not throw."),
                "ko": dict(survival=0.9, primary_owner=0.95),
            },
        },
        # ------------------------------------------------------------------------------------------------------------------
        "SYN-002": {
            "class": "last_minute_rusher", "scenario": "big but late: everything in the last four days; one task incomplete",
            "S01-S1": {
                "tasks": [
                    dict(key="T1", title="Event list page", desc="Show upcoming events as cards with name, date and seats left.",
                         ac=["Fetches events from the API", "Shows name, date and seats left on each card", "Shows a message when there are no events"],
                         sp=3, sub=3, status="Done", met=[1, 1, 0], rating=3,
                         code="""export default function EventList() {
  const [events, setEvents] = useState([]);
  useEffect(() => { api.get('/events').then(r => setEvents(r.data)); }, []);
  return <div className="grid">{events.map(e => <EventCard key={e._id} event={e} />)}</div>;
}"""),
                    dict(key="T2", title="Event detail page", desc="Show one event with its description and a book button.",
                         ac=["Loads one event by id", "Shows description, venue and date", "Has a Book button that opens the booking form"],
                         sp=3, sub=2, status="Done", met=[1, 1, 1], rating=4,
                         code="""export default function EventDetail() {
  const { id } = useParams();
  const [event, setEvent] = useState(null);
  useEffect(() => { api.get(`/events/${id}`).then(r => setEvent(r.data)); }, [id]);
  if (!event) return <p>Loading…</p>;
  return (<><h1>{event.name}</h1><p>{event.description}</p><Link to={`/book/${id}`}>Book</Link></>);
}"""),
                    dict(key="T3", title="Booking form", desc="A form to choose the number of seats and submit a booking.",
                         ac=["Seats input accepts 1 to 10", "Submitting calls POST /bookings", "Shows an error message when the API rejects the booking"],
                         sp=5, sub=4, status="Partially Done", met=[0, 1, 0], rating=2,
                         code="""export default function BookingForm() {
  const [seats, setSeats] = useState(1);
  const submit = async (e) => { e.preventDefault(); await api.post('/bookings', { eventId: id, seats }); navigate('/mine'); };
  return <form onSubmit={submit}><input type="number" value={seats} onChange={e => setSeats(e.target.value)} /><button>Book</button></form>;
}   // no limit on seats and no error handling yet"""),
                ],
                "commits": [
                    (10, 20, "event list page", "T1", [("web/src/pages/EventList.jsx", "code", 96, 0), ("web/src/components/EventCard.jsx", "code", 44, 0)]),
                    (10, 23, "styles for cards", "T1", [("web/src/components/EventCard.jsx", "code", 58, 6), ("web/src/App.jsx", "code", 22, 0)]),
                    (11, 14, "event detail", "T2", [("web/src/pages/EventDetail.jsx", "code", 88, 0)]),
                    (11, 21, "api client", "T2", [("web/src/api/client.js", "code", 31, 0)]),
                    (11, 23, "route for detail page", "T2", [("web/src/App.jsx", "code", 9, 0)]),
                    (12, 13, "booking form first version", "T3", [("web/src/pages/BookingForm.jsx", "code", 72, 0)]),
                    (12, 22, "wire up form to api", "T3", [("web/src/pages/BookingForm.jsx", "code", 19, 8)]),
                    (13, 9, "fix list page crash when empty", "T1", [("web/src/pages/EventList.jsx", "code", 12, 4)]),
                    (13, 18, "more styles", None, [("web/src/components/EventCard.jsx", "code", 33, 14), ("web/src/App.jsx", "code", 17, 9)]),
                    (13, 23, "last fixes before demo", None, [("web/src/pages/EventDetail.jsx", "code", 21, 12), ("web/src/pages/BookingForm.jsx", "code", 8, 3)]),
                ],
                "reviews": [], "comments": [],
                "prs": [(13, "Event list, detail and booking form", True)],
                "quiz": dict(tier="partial", rating=3, snippet="EventList fetches with useEffect and passes events to EventCard",
                             question="What does the empty dependency array in useEffect do in EventList?",
                             answer="It makes it run once when the page opens. I think without it the list would reload all the time."),
                "ko": dict(survival=0.6, primary_owner=0.8),
            },
            "S01-S2": {
                "tasks": [
                    dict(key="T1", title="My bookings page", desc="List the user's bookings with a cancel button.",
                         ac=["Loads GET /bookings/mine", "Shows event name, date and seats", "Cancel button calls DELETE and refreshes the list"],
                         sp=3, sub=3, status="Done", met=[1, 1, 1], rating=4,
                         code="""export default function MyBookings() {
  const [list, setList] = useState([]);
  const load = () => api.get('/bookings/mine').then(r => setList(r.data));
  useEffect(load, []);
  const cancel = async (id) => { await api.delete(`/bookings/${id}`); load(); };
  return list.map(b => <li key={b._id}>{b.event.name} x{b.seats} <button onClick={() => cancel(b._id)}>Cancel</button></li>);
}"""),
                    dict(key="T2", title="Navbar and routes", desc="A navigation bar and routes for all pages.",
                         ac=["Links to events and my bookings", "Shows login state", "Unknown routes show a not-found page"],
                         sp=2, sub=2, status="Done", met=[1, 1, 0], rating=3,
                         code="""export default function Navbar({ user }) {
  return <nav><Link to="/">Events</Link>{user ? <Link to="/mine">My bookings</Link> : <Link to="/login">Log in</Link>}</nav>;
}"""),
                    dict(key="T3", title="Filter events by date", desc="Let the user filter the event list by a date range.",
                         ac=["Two date inputs on the list page", "List only shows events inside the range"],
                         sp=2, sub=2, status="Partially Done", met=[1, 0], rating=2,
                         code="""const [from, setFrom] = useState('');
<input type="date" value={from} onChange={e => setFrom(e.target.value)} />
// range filtering not written yet"""),
                ],
                "commits": [
                    (6, 22, "my bookings page", "T1", [("web/src/pages/MyBookings.jsx", "code", 64, 0)]),
                    (7, 19, "cancel button", "T1", [("web/src/pages/MyBookings.jsx", "code", 17, 3)]),
                    (9, 23, "navbar", "T2", [("web/src/components/Navbar.jsx", "code", 37, 0), ("web/src/App.jsx", "code", 14, 2)]),
                    (12, 11, "date filter inputs", "T3", [("web/src/pages/EventList.jsx", "code", 21, 0)]),
                    (12, 22, "routes cleanup", "T2", [("web/src/App.jsx", "code", 16, 7)]),
                    (13, 17, "styling pass", None, [("web/src/components/Navbar.jsx", "code", 18, 4), ("web/src/pages/MyBookings.jsx", "code", 11, 2)]),
                ],
                "reviews": [(13, "SYN-005", "COMMENTED", "ok", "approval")], "comments": [],
                "prs": [(9, "My bookings page", True), (13, "Navbar, routes and filter", True)],
                "quiz": dict(tier="good", rating=4, snippet="MyBookings reloads the list after cancelling",
                             question="Why does cancel call load() again instead of editing the list in place?",
                             answer="So the page always shows what the server has. If the cancel failed I would not remove the row by mistake. Editing in place would be faster though."),
                "ko": dict(survival=0.8, primary_owner=0.9),
            },
        },
        # ------------------------------------------------------------------------------------------------------------------
        "SYN-003": {
            "class": "reviewer_coordinator", "scenario": "reviewer who also writes a little code; one review is only 'looks good'",
            "S01-S1": {
                "tasks": [
                    dict(key="T1", title="Event model and CRUD controller", desc="Store events and expose create, list, get, update and delete.",
                         ac=["Event has name, description, venue, startsAt and capacity", "GET /events lists upcoming events", "Only admins can create, update or delete"],
                         sp=3, sub=3, status="Done", met=[1, 1, 0], rating=3,
                         code="""// api/models/Event.js
const EventSchema = new Schema({ name: String, description: String, venue: String, startsAt: Date, capacity: Number });
// api/controllers/eventController.js
exports.list = async (req, res) => res.json(await Event.find({ startsAt: { $gte: new Date() } }).sort('startsAt'));
exports.create = async (req, res) => res.status(201).json(await Event.create(req.body));   // admin check not added"""),
                ],
                "commits": [
                    (1, 11, "event model", "T1", [("api/models/Event.js", "code", 21, 0)]),
                    (2, 15, "event controller list and create", "T1", [("api/controllers/eventController.js", "code", 44, 0), ("api/routes/events.js", "code", 12, 0)]),
                    (5, 10, "update and delete event", "T1", [("api/controllers/eventController.js", "code", 22, 3)]),
                ],
                "reviews": [
                    (5, "SYN-001", "COMMENTED", "In createBooking you check the seats and then insert in two separate steps, so two requests at the same moment can both pass the check and overbook the event. Wrap the check and the insert in a transaction or use one atomic update.", "substantive"),
                    (6, "SYN-001", "APPROVED", "The 400 for 'not enough seats' should be a 409 conflict, the client treats 4xx differently. Otherwise capacity.js reads clearly and the off-by-one test is good.", "substantive"),
                    (9, "SYN-005", "CHANGES_REQUESTED", "The admin list reloads every time the form changes because the effect depends on form state. Move the fetch to the event id only, and add an error state for a failed delete.", "substantive"),
                    (12, "SYN-002", "COMMENTED", "The booking form lets seats go to any number, the API will reject it but the user sees nothing. Please add a max of 10 and show the error from the response.", "substantive"),
                    (12, "SYN-005", "APPROVED", "looks good", "approval"),
                ],
                "comments": [(7, "SYN-001", "Agreed on the 409. @SYN-001 can you also return the seats left in the body?", 1, 1), (10, "SYN-005", "Fixed the effect dependency, thanks for catching it.", 0, 0)],
                "prs": [(6, "Event model and CRUD", True)],
                "merged_for_others": 3,
                "quiz": dict(tier="good", rating=4, snippet="eventController.list filters events from now on and sorts by start date",
                             question="Why does list filter on startsAt >= now?",
                             answer="Past events should not be bookable, so the public list only needs upcoming ones. An admin view would need a separate query to see old events."),
                "ko": dict(survival=0.7, primary_owner=0.85),
            },
            "S01-S2": {
                "tasks": [
                    dict(key="T1", title="Auth middleware and request validation", desc="Check the token on protected routes and validate booking input.",
                         ac=["Rejects requests without a valid token", "Attaches the user to req.user", "Validates seats is an integer from 1 to 10"],
                         sp=3, sub=3, status="Done", met=[1, 1, 1], rating=4,
                         code="""// api/middleware/auth.js
module.exports = async (req, res, next) => {
  const token = (req.headers.authorization || '').replace('Bearer ', '');
  try { req.user = await User.findById(jwt.verify(token, process.env.JWT_SECRET).id); next(); }
  catch { res.status(401).json({ error: 'invalid token' }); }
};
// api/middleware/validate.js
exports.seats = (req, res, next) => (Number.isInteger(req.body.seats) && req.body.seats >= 1 && req.body.seats <= 10) ? next() : res.status(400).json({ error: 'seats must be 1-10' });"""),
                    dict(key="T2", title="Event API tests", desc="Tests for listing and creating events.",
                         ac=["Test for GET /events returns only upcoming events", "Test that a non-admin cannot create an event", "Tests run in CI"],
                         sp=2, sub=2, status="Partially Done", met=[1, 0, 0], rating=2,
                         code="""it('lists only upcoming events', async () => {
  await Event.create([{ name: 'past', startsAt: new Date(2020, 0, 1) }, { name: 'next', startsAt: new Date(Date.now() + 864e5) }]);
  const res = await request(app).get('/events');
  expect(res.body.map(e => e.name)).toEqual(['next']);
});"""),
                ],
                "commits": [
                    (2, 11, "auth middleware", "T1", [("api/middleware/auth.js", "code", 18, 0)]),
                    (3, 14, "validate seats", "T1", [("api/middleware/validate.js", "code", 14, 0), ("api/routes/bookings.js", "code", 2, 0)]),
                    (8, 10, "event list test", "T2", [("api/tests/event.test.js", "test", 36, 0)]),
                    (11, 16, "fix token parsing when header is missing", "T1", [("api/middleware/auth.js", "code", 5, 2)]),
                ],
                "reviews": [
                    (5, "SYN-001", "APPROVED", "Email helper is clear. One thing: the subject uses event.name without escaping, a name with a line break would break the mail header, so strip newlines before sending.", "substantive"),
                    (8, "SYN-005", "COMMENTED", "The lock you take in bookSeats is released only on the success path. If the insert throws, the lock stays and the next booking waits until the timeout. Release it in a finally block.", "substantive"),
                    (10, "SYN-002", "COMMENTED", "MyBookings calls load() after every cancel, which is fine, but if the cancel request fails the user gets no message. Show the error.", "brief"),
                    (12, "SYN-004", "APPROVED", "ok", "approval"),
                ],
                "comments": [(9, "SYN-005", "Good catch on the finally block. @SYN-003 could you re-check after my next push?", 1, 1)],
                "prs": [(4, "Auth middleware and validation", True)],
                "merged_for_others": 2,
                "quiz": dict(tier="partial", rating=3, snippet="auth middleware verifies the JWT and loads the user",
                             question="Why does the middleware load the user from the database instead of trusting the token payload?",
                             answer="I think the token could be old. So we read the user again to be sure they still exist."),
                "ko": dict(survival=0.9, primary_owner=0.8),
            },
        },
        # ------------------------------------------------------------------------------------------------------------------
        "SYN-004": {
            "class": "free_rider", "scenario": "assigned task finished by a teammate; token contribution; slight improvement in sprint 2",
            "S01-S1": {
                "tasks": [
                    dict(key="T1", title="Login and register endpoints", desc="Create users with hashed passwords and log them in with a token.",
                         ac=["Register stores a hashed password", "Login returns a JWT for correct credentials", "Wrong password returns 401"],
                         sp=5, sub=4, status="Done", by="SYN-001", met=[0, 1, 1], rating=2,
                         code="""// written by a teammate, not the assignee
exports.login = async (req, res) => {
  const user = await User.findOne({ email: req.body.email });
  if (!user || !(await bcrypt.compare(req.body.password, user.password))) return res.status(401).json({ error: 'bad credentials' });
  res.json({ token: jwt.sign({ id: user.id }, process.env.JWT_SECRET) });
};"""),
                    dict(key="T2", title="Seed data script", desc="A script that inserts sample events for development.",
                         ac=["npm run seed inserts at least five events", "Running it twice does not duplicate events"],
                         sp=2, sub=1, status="To Do", met=[0, 0], rating=1, code=""),
                ],
                "commits": [(12, 22, "update readme", None, [("README.md", "config_or_docs", 6, 1)])],
                "reviews": [], "comments": [], "prs": [],
                "quiz": dict(tier="weak", rating=2, snippet="(no code of their own this sprint)", question="Explain how login checks a password.",
                             answer="It compares it with the one in the database."),
                "ko": dict(survival=1.0, primary_owner=0.0),
            },
            "S01-S2": {
                "tasks": [
                    dict(key="T1", title="Admin dashboard stub", desc="A page for admins listing events with edit and delete buttons.",
                         ac=["Lists all events including past ones", "Edit and delete buttons per row", "Only visible to admins"],
                         sp=3, sub=3, status="Partially Done", met=[1, 0, 0], rating=2,
                         code="""export default function AdminDashboard() {
  const [events, setEvents] = useState([]);
  useEffect(() => { api.get('/events').then(r => setEvents(r.data)); }, []);
  return <table>{events.map(e => <tr key={e._id}><td>{e.name}</td><td><button>Edit</button><button>Delete</button></td></tr>)}</table>;
}   // buttons do nothing, no admin check; list route only returns upcoming events"""),
                ],
                "commits": [
                    (11, 21, "admin page", "T1", [("web/src/pages/AdminDashboard.jsx", "code", 52, 0)]),
                    (13, 19, "table styles", "T1", [("web/src/pages/AdminDashboard.jsx", "code", 28, 5), ("web/src/components/EventCard.jsx", "code", 4, 0)]),
                ],
                "reviews": [], "comments": [], "prs": [(13, "Admin dashboard stub", True)],
                "quiz": dict(tier="partial", rating=3, snippet="AdminDashboard fetches events and renders a table",
                             question="Why does the dashboard not show past events yet?",
                             answer="Because the API only gives future events. I did not change it."),
                "ko": dict(survival=0.5, primary_owner=0.6),
            },
        },
        # ------------------------------------------------------------------------------------------------------------------
        "SYN-005": {
            "class": "burst_worker", "scenario": "two bursts in sprint 1; in sprint 2 a hard concurrency task with little code",
            "S01-S1": {
                "tasks": [
                    dict(key="T1", title="Admin event management UI", desc="Forms to create, edit and delete events for admins.",
                         ac=["Create form posts a new event", "Edit form loads and updates an event", "Delete asks for confirmation", "Errors from the API are shown"],
                         sp=5, sub=4, status="Done", met=[1, 1, 1, 0], rating=3,
                         code="""export default function EventForm({ event, onSaved }) {
  const [form, setForm] = useState(event || { name: '', venue: '', startsAt: '', capacity: 50 });
  const save = async (e) => { e.preventDefault(); event ? await api.put(`/events/${event._id}`, form) : await api.post('/events', form); onSaved(); };
  return <form onSubmit={save}>{['name', 'venue', 'startsAt', 'capacity'].map(f => <input key={f} value={form[f]} onChange={e => setForm({ ...form, [f]: e.target.value })} />)}<button>Save</button></form>;
}
const remove = async (id) => { if (window.confirm('Delete this event?')) { await api.delete(`/events/${id}`); reload(); } };"""),
                    dict(key="T2", title="Admin role check", desc="Only users with role admin may call the event write endpoints.",
                         ac=["Non-admin gets 403 on create, update and delete", "Admin role stored on the user"],
                         sp=2, sub=2, status="Partially Done", met=[0, 1], rating=2,
                         code="""// api/models/User.js: role: { type: String, default: 'user' }
// check in the UI only: {user.role === 'admin' && <AdminLink />}"""),
                ],
                "commits": [
                    (1, 10, "event form", "T1", [("web/src/pages/AdminDashboard.jsx", "code", 118, 0), ("web/src/api/client.js", "code", 8, 0)]),
                    (1, 18, "edit and delete", "T1", [("web/src/pages/AdminDashboard.jsx", "code", 86, 12)]),
                    (2, 12, "validation messages", "T1", [("web/src/pages/AdminDashboard.jsx", "code", 41, 9), ("web/src/components/EventCard.jsx", "code", 17, 2)]),
                    (2, 21, "role on user model", "T2", [("api/models/User.js", "code", 6, 0)]),
                    (10, 15, "fix delete confirm", "T1", [("web/src/pages/AdminDashboard.jsx", "code", 9, 5)]),
                    (10, 19, "hide admin link for users", "T2", [("web/src/components/Navbar.jsx", "code", 7, 0)]),
                ],
                "reviews": [(9, "SYN-003", "COMMENTED", "The role is only checked in the UI. Anyone can still call DELETE /events/:id with a token, so the 403 has to be enforced in the controller or middleware, not hidden in the navbar.", "substantive")],
                "comments": [],
                "prs": [(3, "Admin event UI", True), (11, "Hide admin link", True)],
                "quiz": dict(tier="good", rating=4, snippet="EventForm posts or puts depending on whether an event was passed in",
                             question="What decides whether EventForm creates or updates?",
                             answer="Whether the event prop is set. With an event it calls put with its id, without one it posts a new one."),
                "ko": dict(survival=0.75, primary_owner=0.85),
            },
            "S01-S2": {
                "tasks": [
                    dict(key="T1", title="Prevent double booking under concurrent requests", desc="Two users booking the last seats at the same moment must not overbook an event.",
                         ac=["The seat check and the insert happen atomically", "Concurrent requests for the last seats: only one succeeds", "A test that fires parallel requests", "A lock or transaction is always released"],
                         sp=8, sub=5, status="Partially Done", met=[1, 1, 0, 1], rating=3,
                         code="""exports.bookSeats = async ({ eventId, userId, seats }) => {
  const session = await mongoose.startSession();
  try {
    let booking;
    await session.withTransaction(async () => {
      const event = await Event.findOneAndUpdate(
        { _id: eventId, seatsLeft: { $gte: seats } }, { $inc: { seatsLeft: -seats } }, { session, new: true });
      if (!event) throw new SeatsTaken();
      [booking] = await Booking.create([{ event: eventId, user: userId, seats }], { session });
    });
    return booking;
  } finally { await session.endSession(); }
};   // parallel-request test still missing"""),
                ],
                "commits": [
                    (4, 15, "seatsLeft counter on event and atomic decrement", "T1", [("api/models/Event.js", "code", 9, 1), ("api/controllers/bookingController.js", "code", 31, 14), ("api/utils/capacity.js", "code", 6, 18)]),
                    (5, 11, "wrap booking in a transaction", "T1", [("api/controllers/bookingController.js", "code", 24, 19), ("api/models/Booking.js", "code", 5, 0)]),
                    (11, 16, "release session in finally, review fix", "T1", [("api/controllers/bookingController.js", "code", 7, 4)]),
                    (12, 12, "migrate existing events to have seatsLeft", "T1", [("api/models/Event.js", "code", 11, 2), ("api/utils/capacity.js", "code", 3, 3)]),
                ],
                "reviews": [(7, "SYN-001", "COMMENTED", "The new seatsLeft counter means cancelBooking has to add the seats back, otherwise cancelled seats are lost for good. Please update the cancel handler and add a test for it.", "substantive"),
                            (10, "SYN-002", "APPROVED", "nice", "approval")],
                "comments": [(11, "SYN-003", "Thanks @SYN-003, the finally block is in.", 1, 1)],
                "prs": [(6, "Atomic booking", True)],
                "quiz": dict(tier="strong", rating=5, snippet="bookSeats decrements seatsLeft only if enough remain, inside a transaction",
                             question="Why decrement with a condition instead of reading seatsLeft first?",
                             answer="A read then a write leaves a gap where another request can take the seats. The conditional update does the check and the change in one step, so only one request can win the last seats."),
                "ko": dict(survival=0.9, primary_owner=0.95),
            },
        },
    },
}
