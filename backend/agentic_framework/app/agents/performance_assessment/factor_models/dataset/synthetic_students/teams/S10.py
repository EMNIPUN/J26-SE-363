"""Team S10: IoT sensor dashboard (Flask API + Vue). Four sprints. Students: steady ingestion developer with an integration
setback, late Vue rusher, two-burst data-pipeline developer, a free rider who copies tutorial code, and an average student
with no standout factor (the 'middle' archetype)."""
from _kit import T, Q, S

TEAM = {
    "team": "S10", "domain": "IoT sensor dashboard", "stack": "Flask and Vue",
    "sprint_starts": {"S10-S1": "2026-01-19", "S10-S2": "2026-02-02", "S10-S3": "2026-02-16", "S10-S4": "2026-03-02"},
    "edges": [
        ("server/app.py", "server/routes/readings.py"), ("server/app.py", "server/routes/devices.py"), ("server/app.py", "server/routes/alerts.py"),
        ("server/app.py", "server/mqtt_client.py"), ("server/app.py", "server/db.py"),
        ("server/routes/readings.py", "server/services/ingest.py"), ("server/routes/readings.py", "server/services/aggregate.py"),
        ("server/routes/devices.py", "server/models.py"), ("server/routes/alerts.py", "server/services/alerts.py"),
        ("server/services/ingest.py", "server/models.py"), ("server/services/ingest.py", "server/services/alerts.py"),
        ("server/services/aggregate.py", "server/models.py"), ("server/services/alerts.py", "server/models.py"),
        ("server/mqtt_client.py", "server/services/ingest.py"), ("server/models.py", "server/db.py"),
        ("web/src/main.js", "web/src/views/Dashboard.vue"), ("web/src/main.js", "web/src/views/DeviceList.vue"), ("web/src/main.js", "web/src/views/AlertsView.vue"),
        ("web/src/views/Dashboard.vue", "web/src/components/Chart.vue"), ("web/src/views/Dashboard.vue", "web/src/api.js"),
        ("web/src/views/DeviceList.vue", "web/src/api.js"), ("web/src/views/AlertsView.vue", "web/src/api.js"),
    ],
    "students": {
        "SYN-046": {
            "class": "consistent_deep_contributor", "scenario": "ingestion and tests all sprint; sprint 4 has an integration setback with reverts but still steady effort",
            "S10-S1": S(
                [T("T1", "Receive sensor readings", "Accept temperature and humidity readings from devices.",
                   ["POST /readings with device id, temperature, humidity, timestamp", "Unknown device rejected", "Timestamp defaults to now", "Values outside plausible range rejected"], 8, 5, "Done", [1, 1, 1, 0], 4,
                   """def ingest(payload: dict) -> Reading:
    device = Device.query.get(payload["device_id"])
    if device is None:
        raise UnknownDevice(payload["device_id"])
    r = Reading(device_id=device.id, temperature=payload["temperature"], humidity=payload["humidity"],
                taken_at=payload.get("timestamp") or datetime.utcnow())
    db.session.add(r); db.session.commit()
    return r   # plausibility range not checked""")],
                [(0, 10, "models", "T1", [("server/models.py", "code", 38, 0), ("server/db.py", "code", 11, 0)]),
                 (1, 14, "ingest service", "T1", [("server/services/ingest.py", "code", 32, 0)]),
                 (2, 11, "readings route", "T1", [("server/routes/readings.py", "code", 27, 0), ("server/app.py", "code", 22, 0)]),
                 (3, 15, "unknown device", "T1", [("server/services/ingest.py", "code", 8, 0), ("server/routes/readings.py", "code", 6, 0)]),
                 (5, 10, "ingest tests", "T1", [("tests/test_ingest.py", "test", 52, 0)]),
                 (8, 14, "timestamp default", "T1", [("server/services/ingest.py", "code", 4, 1)]),
                 (10, 11, "fixtures", "T1", [("tests/conftest.py", "test", 25, 0)])],
                Q("good", 4, "ingest rejects unknown devices with UnknownDevice", "Why a custom exception instead of returning None?", "The route can translate it into a 404 and the service stays free of HTTP."), 0.9, 0.95,
                prs=[(6, "Ingest", True), (11, "Fixtures", True)]),
            "S10-S2": S(
                [T("T1", "MQTT subscription", "Receive readings over MQTT as well as HTTP.",
                   ["Subscribe to sensors/+/reading", "Parse JSON payload", "Reconnect on connection loss", "Bad payloads logged not crashing"], 8, 5, "Done", [1, 1, 1, 1], 5,
                   """def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
        payload["device_id"] = msg.topic.split("/")[1]
        ingest(payload)
    except (ValueError, KeyError, UnknownDevice) as e:
        log.warning("bad message on %s: %s", msg.topic, e)"""),
                 T("T2", "Plausibility range check", "Reject impossible values.",
                   ["Temperature between -40 and 85", "Humidity between 0 and 100"], 2, 2, "Done", [1, 1], 5,
                   """if not -40 <= payload["temperature"] <= 85 or not 0 <= payload["humidity"] <= 100:
    raise ImplausibleReading(payload)""", carried="S10-S1-SYN-046-T1")],
                [(0, 10, "range check", "T2", [("server/services/ingest.py", "code", 10, 0), ("tests/test_ingest.py", "test", 18, 0)]),
                 (1, 15, "mqtt client", "T1", [("server/mqtt_client.py", "code", 44, 0)]),
                 (3, 11, "parse and route payload", "T1", [("server/mqtt_client.py", "code", 17, 3)]),
                 (4, 14, "reconnect handling", "T1", [("server/mqtt_client.py", "code", 15, 0)]),
                 (6, 10, "mqtt tests", "T1", [("tests/test_mqtt.py", "test", 46, 0)]),
                 (9, 15, "log bad messages", "T1", [("server/mqtt_client.py", "code", 6, 2)]),
                 (11, 11, "wire to app startup", "T1", [("server/app.py", "code", 7, 0)])],
                Q("strong", 5, "on_message catches parse errors and logs a warning", "Why catch these exceptions here?", "An exception in a paho callback thread can kill the loop. One bad payload must not stop all ingestion."), 0.9, 0.95,
                prs=[(5, "Range check", True), (12, "MQTT", True)]),
            "S10-S3": S(
                [T("T1", "Hourly aggregates", "Average, min and max per device per hour.",
                   ["Hourly buckets", "Average min max", "Computed on demand with a date range", "Efficient for 100k readings"], 8, 5, "Done", [1, 1, 1, 0], 4,
                   """rows = (db.session.query(func.date_trunc('hour', Reading.taken_at).label('h'), func.avg(Reading.temperature), func.min(Reading.temperature), func.max(Reading.temperature))
        .filter(Reading.device_id == device_id, Reading.taken_at.between(start, end)).group_by('h').order_by('h').all())"""),
                 T("T2", "Index on readings", "Speed up range queries.",
                   ["Composite index device and time"], 2, 1, "Done", [1], 4, "Index('ix_reading_dev_time', Reading.device_id, Reading.taken_at)")],
                [(0, 10, "aggregate service", "T1", [("server/services/aggregate.py", "code", 41, 0)]),
                 (1, 15, "aggregate route", "T1", [("server/routes/readings.py", "code", 22, 0)]),
                 (3, 11, "range filter", "T1", [("server/services/aggregate.py", "code", 7, 2)]),
                 (5, 14, "aggregate tests", "T1", [("tests/test_aggregate.py", "test", 49, 0)]),
                 (8, 10, "composite index", "T2", [("server/models.py", "code", 4, 0)]),
                 (10, 15, "performance test with 100k rows", "T1", [("tests/test_aggregate.py", "test", 26, 0)]),
                 (12, 11, "fix empty range", "T1", [("server/services/aggregate.py", "code", 3, 1)])],
                Q("good", 4, "aggregates group by date_trunc('hour')", "Does that work on SQLite?", "No, date_trunc is Postgres. Our tests use SQLite for speed, so the aggregate tests only pass because I used a fixture database that is Postgres."), 0.9, 0.95,
                prs=[(6, "Aggregates", True), (13, "Empty range fix", True)]),
            "S10-S4": S(
                [T("T1", "Integrate ingestion with alerts", "A new reading triggers alert checks.",
                   ["Alert rules evaluated on ingest", "Alert stored once per breach", "Ingest still fast", "Existing tests still pass"], 8, 5, "Partially Done", [1, 1, 0, 1], 3,
                   """def ingest(payload):
    r = _store(payload)
    alerts.check(r)      # called synchronously: slow rule lookups now block every reading""")],
                [(0, 10, "call alerts from ingest", "T1", [("server/services/ingest.py", "code", 12, 1)]),
                 (1, 15, "alert once per breach", "T1", [("server/services/alerts.py", "code", 16, 0)]),
                 (2, 11, "revert synchronous call", "T1", [("server/services/ingest.py", "code", 1, 12)]),
                 (4, 14, "queue alert checks", "T1", [("server/services/ingest.py", "code", 19, 0)]),
                 (6, 10, "revert queue, deadlocks tests", "T1", [("server/services/ingest.py", "code", 4, 19)]),
                 (8, 15, "retry with thread pool", "T1", [("server/services/ingest.py", "code", 17, 0)]),
                 (10, 11, "fix tests", "T1", [("tests/test_ingest.py", "test", 22, 9)])],
                Q("good", 4, "the alert check runs in a thread pool after the reading is stored", "Why not inside the same request?", "Rule lookups were slow and blocked every reading. After the commit the reading is safe even if the alert check fails."), 0.8, 0.9,
                prs=[(11, "Alerts on ingest", True)]),
        },
        "SYN-047": {
            "class": "last_minute_rusher", "scenario": "Vue views built in the last two days each sprint; sprint 3 the biggest delivery but still late",
            "S10-S1": S(
                [T("T1", "Device list view", "Show devices with last reading and status.",
                   ["List of devices", "Last reading per device", "Offline badge after 10 minutes"], 5, 3, "Partially Done", [1, 1, 0], 3,
                   """<li v-for="d in devices" :key="d.id">{{ d.name }}: {{ d.last?.temperature ?? '—' }} °C</li>""")],
                [(11, 21, "device list view", "T1", [("web/src/views/DeviceList.vue", "code", 62, 0), ("web/src/api.js", "code", 19, 0)]),
                 (13, 13, "last reading", "T1", [("web/src/views/DeviceList.vue", "code", 14, 3)]),
                 (13, 22, "router", "T1", [("web/src/main.js", "code", 18, 0)])],
                Q("partial", 3, "the template shows the last temperature or a dash", "What does ?? do?", "Uses the right side if the left is null or undefined."), 0.8, 0.9, prs=[(13, "Device list", True)]),
            "S10-S2": S(
                [T("T1", "Dashboard with a temperature chart", "Line chart of the last 24 hours.",
                   ["Chart of temperature over 24 h", "Choose device", "Auto refresh every minute"], 8, 4, "Partially Done", [1, 1, 0], 3,
                   """const load = async () => { const r = await api.get(`/devices/${id.value}/aggregate?hours=24`); series.value = r.data; };
watch(id, load); onMounted(load);   // no refresh timer""")],
                [(11, 20, "chart component", "T1", [("web/src/components/Chart.vue", "code", 71, 0)]),
                 (12, 22, "dashboard view", "T1", [("web/src/views/Dashboard.vue", "code", 84, 0)]),
                 (13, 14, "device selector", "T1", [("web/src/views/Dashboard.vue", "code", 21, 4)]),
                 (13, 23, "styles", None, [("web/src/views/Dashboard.vue", "code", 25, 10)])],
                Q("good", 4, "the dashboard reloads when the selected device changes", "What does watch(id, load) do?", "Calls load whenever id changes."), 0.8, 0.9, prs=[(13, "Dashboard chart", True)]),
            "S10-S3": S(
                [T("T1", "Alerts view and settings", "Show alerts and edit thresholds.",
                   ["List of alerts", "Edit threshold per device", "Mark alert as read", "Filter unread"], 8, 5, "Done", [1, 1, 1, 0], 4,
                   """<input type="number" v-model.number="rule.max" @change="save(rule)">
const save = (r) => api.put(`/alerts/rules/${r.id}`, r);""")],
                [(10, 22, "alerts view", "T1", [("web/src/views/AlertsView.vue", "code", 94, 0)]),
                 (11, 14, "threshold editor", "T1", [("web/src/views/AlertsView.vue", "code", 41, 0)]),
                 (12, 20, "mark as read", "T1", [("web/src/views/AlertsView.vue", "code", 22, 3)]),
                 (13, 12, "routes", "T1", [("web/src/main.js", "code", 7, 0)]),
                 (13, 22, "final styling", None, [("web/src/views/AlertsView.vue", "code", 19, 8), ("web/src/views/DeviceList.vue", "code", 11, 6)])],
                Q("good", 4, "the threshold input is bound with v-model.number", "Why .number?", "Inputs give strings. .number converts it so the API gets a number."), 0.85, 0.9,
                prs=[(13, "Alerts view", True)]),
            "S10-S4": S(
                [T("T1", "Offline badge and auto refresh", "Show offline devices and refresh data.",
                   ["Offline badge after 10 minutes", "Dashboard refreshes every minute", "Stops refreshing when the tab is hidden"], 5, 3, "Done", [1, 1, 0], 3,
                   """const timer = setInterval(load, 60_000); onUnmounted(() => clearInterval(timer));""", carried="S10-S1-SYN-047-T1")],
                [(9, 21, "offline badge", "T1", [("web/src/views/DeviceList.vue", "code", 16, 0)]),
                 (12, 19, "auto refresh", "T1", [("web/src/views/Dashboard.vue", "code", 11, 0)]),
                 (13, 17, "clear timer on unmount", "T1", [("web/src/views/Dashboard.vue", "code", 3, 0)])],
                Q("good", 4, "the refresh timer is cleared on unmount", "Why clear it?", "Otherwise the old view keeps fetching in the background."), 0.9, 0.9, prs=[(13, "Offline badge and refresh", True)]),
        },
        "SYN-048": {
            "class": "burst_worker", "scenario": "pipeline work in two clear bursts per sprint; sprint 2 one very large burst",
            "S10-S1": S(
                [T("T1", "Device registry", "Register devices with a name, location and API key.",
                   ["Create device with generated key", "List and delete devices", "Key shown once"], 5, 3, "Done", [1, 1, 1], 4,
                   """key = secrets.token_urlsafe(24)
device = Device(name=name, location=location, key_hash=hashlib.sha256(key.encode()).hexdigest())""")],
                [(0, 10, "device model and routes", "T1", [("server/routes/devices.py", "code", 58, 0), ("server/models.py", "code", 17, 0)]),
                 (1, 15, "hashed keys", "T1", [("server/routes/devices.py", "code", 12, 3)]),
                 (10, 10, "delete device", "T1", [("server/routes/devices.py", "code", 14, 0)]),
                 (11, 16, "device tests", "T1", [("tests/test_devices.py", "test", 39, 0)])],
                Q("good", 4, "the device key is stored as a SHA-256 hash", "Why hash the key?", "If the database leaks, nobody can use the keys. We only compare hashes."), 0.9, 0.9, prs=[(2, "Device registry", True), (12, "Device tests", True)]),
            "S10-S2": S(
                [T("T1", "Bulk import of historic data", "Import a CSV of past readings.",
                   ["Upload CSV", "Rows validated like live readings", "Report invalid rows", "Large files in batches"], 8, 5, "Done", [1, 1, 1, 1], 4,
                   """for chunk in pd.read_csv(f, chunksize=5000):
    good = chunk[chunk.temperature.between(-40, 85) & chunk.humidity.between(0, 100)]
    db.session.bulk_insert_mappings(Reading, good.to_dict('records'))
    bad += len(chunk) - len(good)""")],
                [(0, 10, "csv upload route", "T1", [("server/routes/readings.py", "code", 47, 0)]),
                 (0, 14, "batch insert", "T1", [("server/services/ingest.py", "code", 52, 0)]),
                 (0, 19, "validation of rows", "T1", [("server/services/ingest.py", "code", 33, 0)]),
                 (1, 11, "invalid row report", "T1", [("server/routes/readings.py", "code", 28, 0)]),
                 (1, 17, "import tests", "T1", [("tests/test_import.py", "test", 64, 0)]),
                 (2, 12, "chunking", "T1", [("server/services/ingest.py", "code", 15, 5)]),
                 (12, 10, "fix dtype of timestamp", "T1", [("server/services/ingest.py", "code", 3, 2)])],
                Q("good", 4, "the import validates rows in chunks of 5000", "Why chunks?", "A big file would not fit in memory at once, and one bulk insert per chunk is faster than a row at a time."), 0.9, 0.9,
                prs=[(3, "Bulk import", True), (13, "Timestamp fix", True)]),
            "S10-S3": S(
                [T("T1", "Alert rules engine", "Threshold rules with duration (above 30 for 10 minutes).",
                   ["Rule with metric, threshold and minutes", "Alert only when held for the duration", "No duplicate alerts while active", "Clears when back to normal"], 8, 5, "Partially Done", [1, 1, 0, 0], 3,
                   """def breached(rule, readings):
    window = [r for r in readings if r.taken_at >= datetime.utcnow() - timedelta(minutes=rule.minutes)]
    return bool(window) and all(getattr(r, rule.metric) > rule.threshold for r in window)""")],
                [(0, 10, "rule model", "T1", [("server/models.py", "code", 21, 0)]),
                 (0, 16, "breach check", "T1", [("server/services/alerts.py", "code", 39, 0)]),
                 (1, 12, "alert route", "T1", [("server/routes/alerts.py", "code", 31, 0)]),
                 (10, 10, "alert tests", "T1", [("tests/test_alerts.py", "test", 44, 0)]),
                 (11, 15, "duration window fix", "T1", [("server/services/alerts.py", "code", 6, 4)])],
                Q("good", 4, "breached requires all readings in the window to exceed the threshold", "What if the window has just one reading?", "It counts as a breach, which is too eager. It should need enough readings to cover the window."), 0.85, 0.9,
                prs=[(2, "Alert rules", True), (12, "Window fix", True)]),
            "S10-S4": S(
                [T("T1", "Export and backup", "Daily backup of the database and CSV export of readings.",
                   ["Nightly backup", "CSV export for a date range"], 5, 3, "Done", [1, 1], 3,
                   """0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/sensors-$(date +\\%F).sql.gz""")],
                [(0, 10, "csv export", "T1", [("server/routes/readings.py", "code", 33, 0)]),
                 (1, 15, "backup script", "T1", [("scripts/backup.sh", "config_or_docs", 14, 0)]),
                 (11, 10, "export test", "T1", [("tests/test_export.py", "test", 23, 0)])],
                Q("partial", 3, "backup pipes pg_dump into gzip", "How would you restore?", "gunzip and psql, I think."), 0.9, 0.9, prs=[(2, "Export", True), (12, "Export test", True)]),
        },
        "SYN-049": {
            "class": "free_rider", "scenario": "copies tutorial code he cannot explain; one zero sprint; ends with only a README commit",
            "S10-S1": S(
                [T("T1", "Health check endpoint", "GET /health returns status and version.",
                   ["Returns ok", "Returns version"], 1, 1, "Done", [1, 0], 3,
                   """@app.route('/health')
def health(): return {'status': 'ok'}""")],
                [(12, 20, "health endpoint", "T1", [("server/app.py", "code", 6, 0)])],
                Q("weak", 2, "health returns ok", "Where would the version come from?", "A config file maybe."), 1.0, 0.1),
            "S10-S2": S(
                [T("T1", "Device status page", "Show whether a device is online.",
                   ["Online/offline status", "Last seen time"], 3, 2, "Partially Done", [1, 0], 2,
                   """# copied from a Flask tutorial
@app.route('/status/<int:id>')
def status(id): return jsonify(Device.query.get_or_404(id).to_dict())""")],
                [(13, 21, "status endpoint from tutorial", "T1", [("server/routes/devices.py", "code", 143, 0)])],
                Q("weak", 2, "status returns the device dict", "What does get_or_404 do?", "Gets it or gives an error."), 0.4, 0.2, prs=[(13, "Status endpoint", True)]),
            "S10-S3": S(
                [T("T1", "Device status page", "Show whether a device is online.",
                   ["Online/offline status", "Last seen time"], 3, 2, "To Do", [0, 0], 1, carried="S10-S2-SYN-049-T1")],
                [], Q("weak", 1, "(no code this sprint)", "How would last seen be computed?", "From the last reading time."), 0.0, 0.0),
            "S10-S4": S(
                [T("T1", "Project README", "Describe the project and how to run it.",
                   ["Overview", "Run steps"], 1, 1, "Done", [1, 1], 3, "# Sensor dashboard\nRun `flask run` and `npm run dev`.")],
                [(13, 21, "readme", "T1", [("README.md", "config_or_docs", 27, 0)])],
                Q("weak", 2, "README lists flask run and npm run dev", "What port does the API use?", "5000 by default."), 1.0, 0.0),
        },
        "SYN-050": {
            "class": "no_specific_pattern", "scenario": "the average student: moderate commits on most weeks, mostly correct, some rework, occasional review, no strength or weakness",
            "S10-S1": S(
                [T("T1", "Dashboard layout", "Navigation and layout of the dashboard.",
                   ["Navbar", "Routes for devices, dashboard, alerts", "Responsive"], 3, 3, "Done", [1, 1, 0], 3,
                   """<nav><router-link to="/">Dashboard</router-link> <router-link to="/devices">Devices</router-link> <router-link to="/alerts">Alerts</router-link></nav>""")],
                [(1, 11, "navbar", "T1", [("web/src/main.js", "code", 34, 0)]),
                 (4, 15, "routes", "T1", [("web/src/main.js", "code", 16, 2)]),
                 (8, 10, "layout", "T1", [("web/src/views/Dashboard.vue", "code", 41, 0)]),
                 (11, 14, "tweak spacing", "T1", [("web/src/views/Dashboard.vue", "code", 12, 8)])],
                Q("partial", 3, "router-link renders navigation links", "What is the difference from an a tag?", "It does not reload the page."), 0.85, 0.9, prs=[(5, "Layout", True)],
                reviews=[(9, "SYN-046", "COMMENTED", "Looks ok but the ingest function does not check the range yet.", "brief")]),
            "S10-S2": S(
                [T("T1", "Devices API tests", "Tests for listing and creating devices.",
                   ["List test", "Create test", "Delete test"], 3, 3, "Partially Done", [1, 1, 0], 3,
                   """def test_create(client):
    r = client.post('/devices', json={'name': 'a', 'location': 'x'})
    assert r.status_code == 201""")],
                [(2, 11, "list test", "T1", [("tests/test_devices.py", "test", 19, 0)]),
                 (4, 14, "create test", "T1", [("tests/test_devices.py", "test", 17, 0)]),
                 (7, 10, "fix fixture", "T1", [("tests/conftest.py", "test", 8, 4)]),
                 (10, 15, "rename tests", "T1", [("tests/test_devices.py", "test", 5, 5)])],
                Q("good", 4, "create test posts JSON and expects 201", "Why 201 and not 200?", "201 means Created."), 0.9, 0.9, prs=[(11, "Device tests", True)],
                reviews=[(6, "SYN-048", "COMMENTED", "The device key is returned in the list endpoint too, it should be shown only on creation. Please remove it from the list serialisation.", "substantive")],
                comments=[(7, "SYN-048", "Good point, thanks. Will check the serializer.", 1, 0)]),
            "S10-S3": S(
                [T("T1", "Alert history page", "Page with all past alerts.",
                   ["List of past alerts", "Paging", "Filter by device"], 5, 3, "Partially Done", [1, 0, 1], 3,
                   """const alerts = ref([]); onMounted(async () => { alerts.value = (await api.get('/alerts')).data; });   // returns everything, no paging""")],
                [(1, 11, "alert history view", "T1", [("web/src/views/AlertsView.vue", "code", 47, 0)]),
                 (3, 15, "filter by device", "T1", [("web/src/views/AlertsView.vue", "code", 14, 2)]),
                 (6, 10, "route for history", "T1", [("web/src/main.js", "code", 3, 0)]),
                 (9, 14, "api endpoint for history", "T1", [("server/routes/alerts.py", "code", 19, 0)]),
                 (12, 11, "style", None, [("web/src/views/AlertsView.vue", "code", 10, 6)])],
                Q("partial", 3, "the history view fetches all alerts on mount", "What happens with 10,000 alerts?", "It would be slow. Paging is needed."), 0.85, 0.9, prs=[(7, "Alert history", True), (13, "History endpoint", True)]),
            "S10-S4": S(
                [T("T1", "User guide", "Guide for the dashboard.",
                   ["How to read charts", "How to set alerts"], 2, 2, "Done", [1, 1], 4, "docs/user-guide.md with 8 screenshots"),
                 T("T2", "Chart axis labels", "Label axes with units.",
                   ["Axis titles", "Units in tooltips"], 2, 2, "Done", [1, 0], 3, """yAxis: { title: { text: 'Temperature (°C)' } }""")],
                [(2, 11, "user guide", "T1", [("docs/user-guide.md", "config_or_docs", 61, 0)]),
                 (5, 15, "axis titles", "T2", [("web/src/components/Chart.vue", "code", 9, 1)]),
                 (8, 10, "tooltip units", "T2", [("web/src/components/Chart.vue", "code", 6, 2)]),
                 (11, 14, "guide screenshots", "T1", [("docs/user-guide.md", "config_or_docs", 14, 3)])],
                Q("good", 4, "the y axis shows Temperature (°C)", "Why put units on the axis?", "A number without a unit is ambiguous."), 0.9, 0.9, prs=[(12, "Docs and labels", True)],
                reviews=[(10, "SYN-047", "COMMENTED", "Nice, the refresh timer is cleared. Maybe pause it when the tab is hidden as in the task.", "brief"),
                         (11, "SYN-048", "APPROVED", "ok", "approval")]),
        },
    },
}
