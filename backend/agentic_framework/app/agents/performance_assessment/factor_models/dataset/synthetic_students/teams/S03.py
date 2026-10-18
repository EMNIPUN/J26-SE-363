"""Team S03: Food delivery mobile app (Flutter/Dart). Three sprints. Students: steady cart/state logic, late UI work,
two-burst worker, a free rider who joins in sprint 2, and a granular committer (many tiny commits)."""
from _kit import T, Q, S

TEAM = {
    "team": "S03", "domain": "Food delivery (mobile)", "stack": "Flutter",
    "sprint_starts": {"S03-S1": "2026-03-02", "S03-S2": "2026-03-16", "S03-S3": "2026-03-30"},
    "edges": [
        ("lib/main.dart", "lib/screens/home.dart"), ("lib/main.dart", "lib/screens/menu.dart"), ("lib/main.dart", "lib/screens/cart.dart"),
        ("lib/main.dart", "lib/screens/checkout.dart"), ("lib/main.dart", "lib/screens/orders.dart"), ("lib/main.dart", "lib/state/cart.dart"),
        ("lib/screens/home.dart", "lib/services/api.dart"), ("lib/screens/home.dart", "lib/models/restaurant.dart"),
        ("lib/screens/menu.dart", "lib/services/api.dart"), ("lib/screens/menu.dart", "lib/state/cart.dart"), ("lib/screens/menu.dart", "lib/models/menu_item.dart"),
        ("lib/screens/cart.dart", "lib/state/cart.dart"), ("lib/screens/checkout.dart", "lib/state/cart.dart"), ("lib/screens/checkout.dart", "lib/services/api.dart"),
        ("lib/screens/orders.dart", "lib/services/api.dart"), ("lib/screens/orders.dart", "lib/models/order.dart"),
        ("lib/services/api.dart", "lib/models/restaurant.dart"), ("lib/services/api.dart", "lib/models/menu_item.dart"), ("lib/services/api.dart", "lib/models/order.dart"),
        ("lib/state/cart.dart", "lib/models/menu_item.dart"), ("lib/state/cart.dart", "lib/services/pricing.dart"), ("lib/services/pricing.dart", "lib/models/menu_item.dart"),
        ("lib/screens/checkout.dart", "lib/services/pricing.dart"),
    ],
    "students": {
        "SYN-011": {
            "class": "consistent_deep_contributor", "scenario": "owns the cart state and pricing; works most days; tests present but one rule untested",
            "S03-S1": S(
                [T("T1", "Cart state", "Add, remove and change quantity of items in the cart.",
                   ["Add an item", "Increase or decrease quantity", "Removing the last unit removes the line", "Cart total updates"], 5, 4, "Done", [1, 1, 1, 1], 5,
                   """class CartState extends ChangeNotifier {
  final Map<String, CartLine> _lines = {};
  void add(MenuItem item) { _lines.update(item.id, (l) => l.copyWith(qty: l.qty + 1), ifAbsent: () => CartLine(item, 1)); notifyListeners(); }
  void remove(MenuItem item) {
    final l = _lines[item.id]; if (l == null) return;
    l.qty <= 1 ? _lines.remove(item.id) : _lines[item.id] = l.copyWith(qty: l.qty - 1);
    notifyListeners();
  }
  double get total => _lines.values.fold(0, (s, l) => s + l.item.price * l.qty);
}"""),
                 T("T2", "Delivery fee and tax", "Compute delivery fee by distance and add 8% tax.",
                   ["Fee is 150 up to 3 km and 40 per extra km", "Tax of 8% on food only", "Rounded to two decimals"], 3, 3, "Done", [1, 0, 1], 3,
                   """double deliveryFee(double km) => km <= 3 ? 150 : 150 + (km - 3).ceil() * 40;
double tax(double food) => double.parse((food * 0.08).toStringAsFixed(2));   // applied to total incl. fee in checkout, should be food only""")],
                [(0, 10, "menu item model", "T1", [("lib/models/menu_item.dart", "code", 22, 0)]),
                 (1, 15, "cart state", "T1", [("lib/state/cart.dart", "code", 47, 0)]),
                 (2, 11, "quantity change", "T1", [("lib/state/cart.dart", "code", 15, 3)]),
                 (3, 14, "cart tests", "T1", [("test/cart_test.dart", "test", 52, 0)]),
                 (5, 10, "pricing service", "T2", [("lib/services/pricing.dart", "code", 29, 0)]),
                 (6, 16, "pricing tests", "T2", [("test/pricing_test.dart", "test", 31, 0)]),
                 (8, 11, "remove last unit removes line", "T1", [("lib/state/cart.dart", "code", 6, 2), ("test/cart_test.dart", "test", 9, 0)]),
                 (10, 15, "tax rounding", "T2", [("lib/services/pricing.dart", "code", 5, 2)])],
                Q("strong", 5, "CartState.remove removes the line when quantity reaches one", "Why call notifyListeners after every change?",
                  "Widgets listening to the cart rebuild only when notified. If I forget it the badge keeps the old number."),
                0.9, 0.95, prs=[(4, "Cart state", True), (11, "Pricing", True)]),
            "S03-S2": S(
                [T("T1", "Promo codes", "Apply a promo code for a percentage discount.",
                   ["Enter a code in checkout", "Unknown code shows an error", "Discount is applied to food total", "A code cannot be used after its expiry date"], 5, 4, "Partially Done", [1, 1, 1, 0], 3,
                   """double applyPromo(double food, Promo? p) {
  if (p == null) return food;
  return food * (1 - p.percent / 100);   // expiry is stored on Promo but not checked"""),
                 T("T2", "Fix tax base", "Tax applies to food only.",
                   ["Tax excludes delivery fee", "Test updated"], 1, 1, "Done", [1, 1], 5,
                   """final taxable = cart.total;      // food only
final grand = taxable + tax(taxable) + deliveryFee(km);""", carried="S03-S1-SYN-011-T2")],
                [(0, 10, "tax base fix", "T2", [("lib/screens/checkout.dart", "code", 4, 4), ("test/pricing_test.dart", "test", 8, 2)]),
                 (1, 14, "promo model", "T1", [("lib/services/pricing.dart", "code", 24, 0)]),
                 (3, 11, "promo input in checkout", "T1", [("lib/screens/checkout.dart", "code", 28, 3)]),
                 (4, 15, "unknown code error", "T1", [("lib/screens/checkout.dart", "code", 12, 1)]),
                 (7, 10, "promo tests", "T1", [("test/pricing_test.dart", "test", 34, 0)]),
                 (9, 14, "refactor totals into pricing", None, [("lib/services/pricing.dart", "code", 21, 6), ("lib/state/cart.dart", "code", 3, 12)]),
                 (11, 16, "docs for promo format", None, [("README.md", "config_or_docs", 14, 0)])],
                Q("good", 4, "applyPromo multiplies by one minus the percent", "What does the promo code ignore today?",
                  "The expiry date. It is on the model but I never compare it with today."),
                0.9, 0.9, prs=[(5, "Promo codes", True), (12, "Totals refactor", True)]),
            "S03-S3": S(
                [T("T1", "Order history persistence", "Keep the last 20 orders offline.",
                   ["Orders saved locally after checkout", "History opens without network", "Only 20 newest kept"], 5, 4, "Done", [1, 1, 1], 4,
                   """Future<void> save(Order o) async {
  final box = await Hive.openBox<Order>('orders');
  await box.add(o);
  while (box.length > 20) { await box.deleteAt(0); }
}"""),
                 T("T2", "Reorder button", "Add the items of a past order to the cart.",
                   ["Reorder button on each past order", "Unavailable items are skipped", "User is told which were skipped"], 3, 3, "Partially Done", [1, 1, 0], 3,
                   """void reorder(Order o, CartState cart, Set<String> available) {
  for (final l in o.lines) { if (available.contains(l.item.id)) { for (var i = 0; i < l.qty; i++) cart.add(l.item); } }
}   // skipped items are dropped silently""")],
                [(0, 10, "hive box for orders", "T1", [("lib/services/api.dart", "code", 26, 3)]),
                 (1, 15, "keep last 20", "T1", [("lib/services/api.dart", "code", 8, 1)]),
                 (3, 11, "history reads local box", "T1", [("lib/screens/orders.dart", "code", 19, 5)]),
                 (4, 16, "storage tests", "T1", [("test/orders_test.dart", "test", 37, 0)]),
                 (7, 10, "reorder logic", "T2", [("lib/state/cart.dart", "code", 18, 0)]),
                 (9, 14, "reorder button", "T2", [("lib/screens/orders.dart", "code", 11, 0)]),
                 (11, 10, "fix box type registration", "T1", [("lib/main.dart", "code", 3, 0)])],
                Q("good", 4, "save deletes the oldest order while more than 20 exist", "Why a while loop instead of an if?",
                  "If the box somehow has more than 21 entries one delete is not enough. The loop trims it down to 20."),
                0.9, 0.9, prs=[(5, "Order history", True), (12, "Reorder", True)]),
        },
        "SYN-012": {
            "class": "last_minute_rusher", "scenario": "screens done in the final two days; UI works but error and empty states are missing",
            "S03-S1": S(
                [T("T1", "Home screen with restaurant list", "List restaurants with rating and delivery time.",
                   ["Fetches restaurants", "Shows name, rating and delivery time", "Pull to refresh", "Empty state"], 5, 3, "Done", [1, 1, 1, 0], 3,
                   """class HomeScreen extends StatelessWidget {
  Widget build(BuildContext c) => FutureBuilder<List<Restaurant>>(
    future: Api.restaurants(),
    builder: (c, s) => s.hasData ? RefreshIndicator(onRefresh: () async => setState(() {}), child: ListView(children: s.data!.map((r) => ListTile(title: Text(r.name), subtitle: Text('${r.rating} · ${r.eta} min'))).toList())) : const CircularProgressIndicator());
}"""),
                 T("T2", "Menu screen", "Show a restaurant's menu with add buttons.",
                   ["Loads menu items", "Add button adds to cart", "Shows price"], 3, 2, "Partially Done", [1, 0, 1], 2,
                   """class MenuScreen extends StatelessWidget {
  Widget build(BuildContext c) => ListView(children: items.map((i) => ListTile(title: Text(i.name), trailing: Text('Rs ${i.price}'))).toList());
}   // no add button yet""")],
                [(11, 19, "home screen", "T1", [("lib/screens/home.dart", "code", 83, 0)]),
                 (12, 13, "api service", "T1", [("lib/services/api.dart", "code", 46, 0), ("lib/models/restaurant.dart", "code", 21, 0)]),
                 (12, 22, "menu screen", "T2", [("lib/screens/menu.dart", "code", 71, 0)]),
                 (13, 15, "refresh indicator", "T1", [("lib/screens/home.dart", "code", 14, 3)]),
                 (13, 22, "main routes", None, [("lib/main.dart", "code", 34, 0)])],
                Q("partial", 3, "FutureBuilder shows a spinner until the data arrives", "What happens if the request fails?",
                  "I think it keeps spinning. I did not add the error part."), 0.75, 0.9, prs=[(13, "Home and menu screens", True)]),
            "S03-S2": S(
                [T("T1", "Cart and checkout screens", "Show the cart and let the user place the order.",
                   ["Cart lists lines with quantity", "Checkout shows totals", "Place order calls the API", "Failure shows a message"], 8, 5, "Partially Done", [1, 1, 1, 0], 3,
                   """ElevatedButton(onPressed: () async { await Api.placeOrder(cart.lines); cart.clear(); Navigator.pop(c); }, child: const Text('Place order'))
// a failed request throws and the app shows the red error screen"""),
                 T("T2", "Menu add button", "Finish the add button on the menu.",
                   ["Add button on each item", "Cart badge updates"], 2, 1, "Done", [1, 1], 4,
                   """trailing: IconButton(icon: const Icon(Icons.add), onPressed: () => context.read<CartState>().add(i)),""", carried="S03-S1-SYN-012-T2")],
                [(12, 12, "add button on menu items", "T2", [("lib/screens/menu.dart", "code", 18, 4)]),
                 (12, 20, "cart screen", "T1", [("lib/screens/cart.dart", "code", 77, 0)]),
                 (13, 10, "checkout screen", "T1", [("lib/screens/checkout.dart", "code", 94, 0)]),
                 (13, 18, "wire place order", "T1", [("lib/screens/checkout.dart", "code", 21, 6)]),
                 (13, 23, "badge on app bar", "T2", [("lib/screens/home.dart", "code", 13, 0)])],
                Q("good", 4, "the add button reads CartState from context", "Why context.read and not context.watch in onPressed?",
                  "read just fetches it once. watch would rebuild and is not allowed inside a callback."), 0.8, 0.9,
                prs=[(13, "Cart and checkout", True)],
                reviews=[(13, "SYN-011", "COMMENTED", "ok", "approval")]),
            "S03-S3": S(
                [T("T1", "Orders screen with status", "Show orders and their delivery status.",
                   ["List of past orders", "Status chip per order", "Tap to see the items"], 5, 3, "Done", [1, 1, 0], 3,
                   """ListTile(title: Text('#${o.id}'), subtitle: Text(o.status), trailing: Chip(label: Text(o.status)))
// tapping an order does nothing"""),
                 T("T2", "Empty and error states", "Show a friendly message when lists are empty or loading fails.",
                   ["Empty cart message", "Home shows retry on error"], 2, 2, "Partially Done", [1, 0], 2,
                   """if (cart.lines.isEmpty) return const Center(child: Text('Your cart is empty'));""")],
                [(10, 21, "orders screen", "T1", [("lib/screens/orders.dart", "code", 62, 14)]),
                 (11, 23, "status chips", "T1", [("lib/screens/orders.dart", "code", 15, 2)]),
                 (12, 20, "empty cart message", "T2", [("lib/screens/cart.dart", "code", 9, 0)]),
                 (13, 22, "styling", None, [("lib/screens/home.dart", "code", 17, 8), ("lib/screens/menu.dart", "code", 11, 4)])],
                Q("partial", 3, "empty cart returns a centred message", "Where is the retry for a failed home request?",
                  "Not done. Only the empty cart message is added."), 0.8, 0.9, prs=[(13, "Orders and empty states", True)]),
        },
        "SYN-013": {
            "class": "burst_worker", "scenario": "two bursts per sprint with a quiet week between; good bursts, sprint 3 only one burst",
            "S03-S1": S(
                [T("T1", "Authentication screens", "Login and sign up with email.",
                   ["Sign up form", "Login form", "Token saved securely", "Validation errors shown"], 8, 5, "Done", [1, 1, 1, 0], 4,
                   """Future<void> login(String email, String pw) async {
  final r = await http.post(Uri.parse('$base/login'), body: {'email': email, 'password': pw});
  if (r.statusCode != 200) throw AuthError(r.body);
  await storage.write(key: 'token', value: jsonDecode(r.body)['token']);
}""")],
                [(0, 10, "login screen", "T1", [("lib/screens/home.dart", "code", 64, 0)]),
                 (0, 15, "sign up form", "T1", [("lib/screens/home.dart", "code", 71, 6)]),
                 (1, 11, "auth service", "T1", [("lib/services/api.dart", "code", 58, 0)]),
                 (1, 19, "secure storage", "T1", [("lib/services/api.dart", "code", 12, 2)]),
                 (2, 14, "navigate after login", "T1", [("lib/main.dart", "code", 19, 3)]),
                 (10, 10, "validation messages", "T1", [("lib/screens/home.dart", "code", 38, 7)]),
                 (10, 16, "auth tests", "T1", [("test/auth_test.dart", "test", 47, 0)]),
                 (11, 13, "fix token key", "T1", [("lib/services/api.dart", "code", 3, 3)])],
                Q("good", 4, "login stores the token in secure storage", "Why secure storage and not shared preferences?",
                  "Shared preferences is plain text on the device. Secure storage uses the keychain or keystore."), 0.8, 0.9,
                prs=[(3, "Authentication", True), (11, "Validation and tests", True)]),
            "S03-S2": S(
                [T("T1", "Live order tracking", "Poll the order status every 10 seconds on the tracking screen.",
                   ["Screen polls GET /orders/{id}", "Stops polling when delivered", "Shows rider name", "Handles network loss"], 8, 5, "Partially Done", [1, 1, 1, 0], 3,
                   """late Timer _t;
void start(String id) {
  _t = Timer.periodic(const Duration(seconds: 10), (_) async {
    final o = await Api.order(id);
    setState(() => order = o);
    if (o.status == 'delivered') _t.cancel();
  });
}   // exception from Api.order cancels nothing and is uncaught"""),
                 T("T2", "Rate the order", "Five-star rating after delivery.",
                   ["Star picker", "Rating sent to API"], 2, 2, "To Do", [0, 0], 1)],
                [(1, 10, "tracking screen", "T1", [("lib/screens/orders.dart", "code", 88, 12)]),
                 (1, 16, "polling timer", "T1", [("lib/screens/orders.dart", "code", 26, 4)]),
                 (2, 11, "stop when delivered", "T1", [("lib/screens/orders.dart", "code", 7, 1)]),
                 (2, 17, "rider name", "T1", [("lib/models/order.dart", "code", 11, 0), ("lib/screens/orders.dart", "code", 9, 0)]),
                 (3, 10, "dispose timer", "T1", [("lib/screens/orders.dart", "code", 5, 0)])],
                Q("good", 4, "tracking uses Timer.periodic and cancels on delivered", "What if the screen closes while the timer runs?",
                  "dispose should cancel the timer. I added that in the last commit, otherwise it would keep polling."), 0.85, 0.9,
                prs=[(4, "Order tracking", True)]),
            "S03-S3": S(
                [T("T1", "Push notifications for order updates", "Send a push when the status changes.",
                   ["Device token registered", "Notification on each status change", "Tapping opens the order"], 8, 5, "Partially Done", [1, 1, 0], 3,
                   """Future<void> register() async {
  final token = await FirebaseMessaging.instance.getToken();
  await Api.registerDevice(token!);
}
FirebaseMessaging.onMessage.listen((m) => showLocal(m.notification!.title!));""")],
                [(0, 10, "firebase messaging setup", "T1", [("lib/main.dart", "code", 24, 2), ("lib/services/api.dart", "code", 15, 0)]),
                 (0, 16, "register device token", "T1", [("lib/services/api.dart", "code", 21, 0)]),
                 (1, 11, "foreground handler", "T1", [("lib/main.dart", "code", 28, 4)]),
                 (1, 20, "local notification display", "T1", [("lib/screens/orders.dart", "code", 22, 0)])],
                Q("partial", 3, "onMessage listens to foreground push messages", "What handles a push while the app is closed?",
                  "A background handler is needed. I only did the foreground one."), 0.85, 0.9, prs=[(2, "Push notifications", True)]),
        },
        "SYN-014": {
            "class": "free_rider", "scenario": "joins in sprint 2; one small file; blames the schedule; sprint 3 tidies docs only",
            "S03-S2": S(
                [T("T1", "Restaurant search", "Search restaurants by name or cuisine.",
                   ["Search box on home", "Matches name or cuisine", "Debounced input"], 3, 3, "Partially Done", [1, 0, 0], 2,
                   """List<Restaurant> filter(List<Restaurant> all, String q) =>
    all.where((r) => r.name.toLowerCase().contains(q.toLowerCase())).toList();""")],
                [(11, 21, "restaurant filter function", "T1", [("lib/models/restaurant.dart", "code", 14, 0)]),
                 (13, 22, "readme typo", None, [("README.md", "config_or_docs", 2, 2)])],
                Q("weak", 2, "filter matches the restaurant name", "How does the search handle cuisine?",
                  "It does not yet, only the name."), 0.8, 0.4, prs=[(13, "Search helper", False)]),
            "S03-S3": S(
                [T("T1", "Restaurant search UI", "Finish search on the home screen.",
                   ["Search box on home", "Matches name or cuisine", "Debounced input"], 3, 3, "To Do", [0, 0, 0], 1, carried="S03-S2-SYN-014-T1"),
                 T("T2", "User guide", "Short guide for ordering food in the app.",
                   ["Steps with screenshots", "Linked from README"], 1, 1, "Done", [1, 0], 3, "# How to order\n1. Pick a restaurant\n2. Add items\n3. Check out")],
                [(12, 20, "user guide", "T2", [("docs/user-guide.md", "config_or_docs", 33, 0)]),
                 (13, 18, "readme link", "T2", [("README.md", "config_or_docs", 3, 0)])],
                Q("weak", 2, "(no code this sprint)", "Where would the debounce go?", "In the search box I think."), 1.0, 0.0),
        },
        "SYN-015": {
            "class": "no_specific_pattern", "scenario": "granular committer: very many tiny commits, modest total change; some rework",
            "S03-S1": S(
                [T("T1", "Restaurant and menu models", "Dart models parsed from JSON.",
                   ["Restaurant fromJson", "MenuItem fromJson", "Order fromJson", "Missing fields do not crash"], 3, 4, "Done", [1, 1, 1, 0], 4,
                   """factory MenuItem.fromJson(Map<String, dynamic> j) => MenuItem(id: j['id'], name: j['name'], price: (j['price'] as num).toDouble());
// a null description crashes: j['description'] as String"""),
                 T("T2", "Theme and typography", "App colours and text styles.",
                   ["Primary colour set", "Dark mode"], 2, 2, "Partially Done", [1, 0], 3,
                   """ThemeData(colorSchemeSeed: const Color(0xFFE4572E), useMaterial3: true)""")],
                [(0, 9, "restaurant model", "T1", [("lib/models/restaurant.dart", "code", 9, 0)]),
                 (0, 10, "restaurant fromJson", "T1", [("lib/models/restaurant.dart", "code", 8, 0)]),
                 (0, 11, "menu item model", "T1", [("lib/models/menu_item.dart", "code", 7, 0)]),
                 (1, 10, "menu item fromJson", "T1", [("lib/models/menu_item.dart", "code", 6, 0)]),
                 (1, 14, "order model", "T1", [("lib/models/order.dart", "code", 11, 0)]),
                 (2, 9, "order fromJson", "T1", [("lib/models/order.dart", "code", 9, 0)]),
                 (2, 10, "rename field", "T1", [("lib/models/order.dart", "code", 1, 1)]),
                 (3, 15, "theme", "T2", [("lib/main.dart", "code", 6, 0)]),
                 (3, 16, "theme colour", "T2", [("lib/main.dart", "code", 1, 1)]),
                 (4, 10, "text styles", "T2", [("lib/main.dart", "code", 8, 0)]),
                 (4, 11, "fix import", "T1", [("lib/models/menu_item.dart", "code", 1, 1)]),
                 (5, 14, "unit test restaurant", "T1", [("test/models_test.dart", "test", 14, 0)]),
                 (5, 15, "unit test menu item", "T1", [("test/models_test.dart", "test", 12, 0)]),
                 (6, 10, "price as double", "T1", [("lib/models/menu_item.dart", "code", 2, 1)]),
                 (7, 11, "restaurant rating default", "T1", [("lib/models/restaurant.dart", "code", 2, 1)]),
                 (8, 16, "unit test order", "T1", [("test/models_test.dart", "test", 13, 0)]),
                 (9, 10, "format", None, [("lib/models/order.dart", "code", 3, 3)]),
                 (10, 14, "dark theme attempt", "T2", [("lib/main.dart", "code", 5, 2)]),
                 (10, 15, "revert dark theme", "T2", [("lib/main.dart", "code", 1, 5)]),
                 (12, 11, "readme dart version", None, [("README.md", "config_or_docs", 2, 0)])],
                Q("good", 4, "MenuItem.fromJson converts price with num.toDouble", "Why cast to num first?",
                  "The JSON can give an int like 450 or a double like 450.5. num handles both, then toDouble makes it uniform."),
                0.8, 0.95, prs=[(6, "Models", True), (12, "Theme", True)]),
            "S03-S2": S(
                [T("T1", "Offline cache of menus", "Cache the last loaded menu for each restaurant.",
                   ["Menu saved after load", "Menu shown from cache when offline", "Cache older than 1 day ignored"], 5, 4, "Partially Done", [1, 1, 0], 3,
                   """Future<List<MenuItem>> menu(String id) async {
  try { final items = await fetch(id); await cache.put(id, items); return items; }
  catch (_) { return cache.get(id) ?? []; }
}   // no timestamp check""")],
                [(0, 10, "cache box", "T1", [("lib/services/api.dart", "code", 10, 0)]),
                 (0, 11, "save menu after fetch", "T1", [("lib/services/api.dart", "code", 6, 1)]),
                 (1, 15, "read from cache on error", "T1", [("lib/services/api.dart", "code", 5, 0)]),
                 (1, 16, "log cache hit", "T1", [("lib/services/api.dart", "code", 2, 0)]),
                 (2, 10, "cache test", "T1", [("test/cache_test.dart", "test", 22, 0)]),
                 (3, 14, "fix cache key", "T1", [("lib/services/api.dart", "code", 1, 1)]),
                 (4, 9, "remove log", "T1", [("lib/services/api.dart", "code", 0, 2)]),
                 (6, 11, "offline banner", "T1", [("lib/screens/menu.dart", "code", 13, 0)]),
                 (8, 15, "banner colour", "T1", [("lib/screens/menu.dart", "code", 1, 1)]),
                 (9, 10, "cache test for offline", "T1", [("test/cache_test.dart", "test", 18, 0)])],
                Q("good", 4, "menu falls back to the cache when fetch throws", "What is the weakness of catch (_)?",
                  "It hides every error, even a bug in parsing. It should only catch network errors."), 0.85, 0.9,
                prs=[(5, "Menu cache", True)]),
            "S03-S3": S(
                [T("T1", "Accessibility pass", "Labels and sizes for screen readers.",
                   ["Semantic labels on buttons", "Minimum tap size 48", "Contrast checked"], 3, 3, "Partially Done", [1, 0, 0], 2,
                   """IconButton(tooltip: 'Add to cart', icon: const Icon(Icons.add), onPressed: onAdd)""")],
                [(2, 15, "tooltips on icon buttons", "T1", [("lib/screens/menu.dart", "code", 3, 1)]),
                 (3, 14, "semantic label on cart badge", "T1", [("lib/screens/home.dart", "code", 2, 0)]),
                 (8, 10, "tap target size", "T1", [("lib/screens/cart.dart", "code", 2, 1)])],
                Q("partial", 3, "tooltip doubles as the semantic label", "What is checked by Semantics?",
                  "What a screen reader reads out."), 0.9, 0.9, prs=[(9, "Accessibility", True)]),
        },
    },
}
