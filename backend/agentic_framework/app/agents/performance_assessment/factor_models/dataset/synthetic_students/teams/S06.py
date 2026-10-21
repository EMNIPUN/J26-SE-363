"""Team S06: Retail inventory and point of sale (Go API + React admin). Four sprints. Students: one who carries the team,
a late React rusher, a coordinator-reviewer, a high-volume writer of easy CRUD, and a student who starts strong and fades."""
from _kit import T, Q, S

TEAM = {
    "team": "S06", "domain": "Retail inventory and POS", "stack": "Go API and React admin",
    "sprint_starts": {"S06-S1": "2026-01-26", "S06-S2": "2026-02-09", "S06-S3": "2026-02-23", "S06-S4": "2026-03-09"},
    "edges": [
        ("api/main.go", "api/handlers/products.go"), ("api/main.go", "api/handlers/sales.go"), ("api/main.go", "api/handlers/suppliers.go"),
        ("api/main.go", "api/handlers/reports.go"), ("api/main.go", "api/auth/jwt.go"), ("api/main.go", "api/store/db.go"),
        ("api/handlers/products.go", "api/store/products.go"), ("api/handlers/products.go", "api/models/product.go"),
        ("api/handlers/sales.go", "api/store/sales.go"), ("api/handlers/sales.go", "api/store/products.go"), ("api/handlers/sales.go", "api/models/sale.go"),
        ("api/handlers/suppliers.go", "api/store/suppliers.go"), ("api/handlers/suppliers.go", "api/models/supplier.go"),
        ("api/handlers/reports.go", "api/store/sales.go"), ("api/handlers/reports.go", "api/store/products.go"),
        ("api/store/products.go", "api/store/db.go"), ("api/store/products.go", "api/models/product.go"), ("api/store/sales.go", "api/store/db.go"),
        ("api/store/sales.go", "api/models/sale.go"), ("api/store/suppliers.go", "api/store/db.go"), ("api/store/suppliers.go", "api/models/supplier.go"),
        ("api/models/sale.go", "api/models/product.go"),
        ("admin/src/App.jsx", "admin/src/pages/Products.jsx"), ("admin/src/App.jsx", "admin/src/pages/Sales.jsx"), ("admin/src/App.jsx", "admin/src/pages/Reports.jsx"),
        ("admin/src/pages/Products.jsx", "admin/src/api.js"), ("admin/src/pages/Sales.jsx", "admin/src/api.js"), ("admin/src/pages/Reports.jsx", "admin/src/api.js"),
    ],
    "students": {
        "SYN-026": {
            "class": "consistent_deep_contributor", "scenario": "carries the team: about half of all backend work, steady; weakest on tests and on explaining decisions",
            "S06-S1": S(
                [T("T1", "Product catalogue API", "CRUD for products with SKU, price and stock.",
                   ["Create, read, update, delete products", "SKU is unique", "Stock cannot go negative", "List supports search by name"], 8, 5, "Done", [1, 1, 1, 1], 5,
                   """func (s *ProductStore) Create(ctx context.Context, p *models.Product) error {
	_, err := s.db.ExecContext(ctx, `INSERT INTO products (sku, name, price, stock) VALUES ($1,$2,$3,$4)`, p.SKU, p.Name, p.Price, p.Stock)
	var pe *pq.Error
	if errors.As(err, &pe) && pe.Code == "23505" {
		return ErrDuplicateSKU
	}
	return err
}"""),
                 T("T2", "Authentication with JWT", "Cashiers and managers log in; managers only for admin routes.",
                   ["Login returns a token", "Token carries the role", "Admin routes need manager"], 5, 3, "Done", [1, 1, 1], 4,
                   """func Require(role string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			c, err := parse(r.Header.Get("Authorization"))
			if err != nil || (role != "" && c.Role != role) {
				http.Error(w, "forbidden", http.StatusForbidden)
				return
			}
			next.ServeHTTP(w, r.WithContext(withClaims(r.Context(), c)))
		})
	}
}""")],
                [(0, 9, "product model and schema", "T1", [("api/models/product.go", "code", 31, 0), ("api/store/db.go", "code", 42, 0)]),
                 (0, 15, "product store", "T1", [("api/store/products.go", "code", 96, 0)]),
                 (1, 10, "product handlers", "T1", [("api/handlers/products.go", "code", 118, 0)]),
                 (1, 16, "router and main", "T1", [("api/main.go", "code", 54, 0)]),
                 (2, 11, "duplicate sku error", "T1", [("api/store/products.go", "code", 12, 3)]),
                 (3, 10, "search by name", "T1", [("api/store/products.go", "code", 17, 2), ("api/handlers/products.go", "code", 8, 0)]),
                 (4, 14, "jwt auth", "T2", [("api/auth/jwt.go", "code", 71, 0)]),
                 (5, 11, "role middleware", "T2", [("api/auth/jwt.go", "code", 29, 4), ("api/main.go", "code", 9, 2)]),
                 (6, 15, "stock never negative check", "T1", [("api/store/products.go", "code", 14, 2)]),
                 (8, 10, "product store test", "T1", [("api/store/products_test.go", "test", 44, 0)]),
                 (9, 16, "login handler", "T2", [("api/handlers/products.go", "code", 22, 0)]),
                 (11, 11, "fix claims context key", "T2", [("api/auth/jwt.go", "code", 6, 6)]),
                 (12, 14, "env config", None, [("api/main.go", "code", 14, 3)])],
                Q("good", 4, "Create maps a unique violation to ErrDuplicateSKU", "Why match the Postgres error code instead of checking first?",
                  "A check then insert has a race. Letting the database reject it and mapping code 23505 is safe even with concurrent requests."),
                0.9, 0.95, prs=[(6, "Product API", True), (13, "Auth", True)]),
            "S06-S2": S(
                [T("T1", "Point of sale: create a sale", "Cashier adds items and completes a sale; stock decreases.",
                   ["A sale has lines with quantity and price", "Completing a sale reduces stock", "Refuse a sale when stock is not enough", "Everything happens in one transaction"], 13, 6, "Done", [1, 1, 1, 1], 5,
                   """func (s *SaleStore) Complete(ctx context.Context, sale *models.Sale) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil { return err }
	defer tx.Rollback()
	for _, l := range sale.Lines {
		res, err := tx.ExecContext(ctx, `UPDATE products SET stock = stock - $1 WHERE id = $2 AND stock >= $1`, l.Qty, l.ProductID)
		if err != nil { return err }
		if n, _ := res.RowsAffected(); n == 0 { return ErrInsufficientStock }
	}
	if err := insertSale(ctx, tx, sale); err != nil { return err }
	return tx.Commit()
}""")],
                [(0, 10, "sale model", "T1", [("api/models/sale.go", "code", 38, 0)]),
                 (0, 16, "sale store transaction", "T1", [("api/store/sales.go", "code", 87, 0)]),
                 (1, 11, "sale handler", "T1", [("api/handlers/sales.go", "code", 76, 0)]),
                 (2, 14, "conditional stock update", "T1", [("api/store/sales.go", "code", 12, 8)]),
                 (3, 10, "insufficient stock error mapping", "T1", [("api/handlers/sales.go", "code", 15, 2)]),
                 (4, 15, "sale totals", "T1", [("api/models/sale.go", "code", 18, 0)]),
                 (6, 11, "sale store tests", "T1", [("api/store/sales_test.go", "test", 71, 0)]),
                 (7, 14, "rollback test", "T1", [("api/store/sales_test.go", "test", 24, 0)]),
                 (8, 10, "discount field", "T1", [("api/models/sale.go", "code", 9, 1), ("api/store/sales.go", "code", 11, 2)]),
                 (10, 15, "idempotency key", "T1", [("api/handlers/sales.go", "code", 27, 3)]),
                 (12, 11, "fix rounding in totals", "T1", [("api/models/sale.go", "code", 5, 5)]),
                 (13, 10, "handler cleanup", None, [("api/handlers/sales.go", "code", 8, 16)])],
                Q("strong", 5, "Complete decrements stock only where stock is enough, inside a transaction", "Why check RowsAffected?",
                  "If the stock was too low the UPDATE matches no row and RowsAffected is zero. That is how I detect it atomically; the defer Rollback undoes any earlier lines."),
                0.95, 0.95, prs=[(5, "Sales", True), (13, "Sales fixes", True)]),
            "S06-S3": S(
                [T("T1", "Daily sales report", "Totals per day with top five products.",
                   ["Total sales per day", "Top five products by quantity", "Date range filter", "Cached for one minute"], 8, 4, "Partially Done", [1, 1, 1, 0], 4,
                   """const topProducts = `SELECT p.name, SUM(l.qty) AS qty FROM sale_lines l JOIN products p ON p.id = l.product_id
 WHERE l.created_at >= $1 AND l.created_at < $2 GROUP BY p.name ORDER BY qty DESC LIMIT 5`"""),
                 T("T2", "Low stock alerts", "List products below their reorder level.",
                   ["Reorder level on product", "Endpoint lists low stock", "Sorted by shortage"], 3, 2, "Done", [1, 1, 1], 4,
                   """SELECT * FROM products WHERE stock < reorder_level ORDER BY (reorder_level - stock) DESC""")],
                [(0, 11, "report queries", "T1", [("api/store/sales.go", "code", 53, 0)]),
                 (1, 15, "report handler", "T1", [("api/handlers/reports.go", "code", 64, 0)]),
                 (2, 10, "date range filter", "T1", [("api/handlers/reports.go", "code", 19, 2)]),
                 (4, 14, "reorder level column", "T2", [("api/models/product.go", "code", 6, 0), ("api/store/products.go", "code", 21, 0)]),
                 (5, 11, "low stock handler", "T2", [("api/handlers/products.go", "code", 24, 0)]),
                 (7, 15, "report tests", "T1", [("api/store/sales_test.go", "test", 42, 0)]),
                 (9, 10, "timezone for daily buckets", "T1", [("api/store/sales.go", "code", 7, 4)]),
                 (11, 14, "low stock test", "T2", [("api/store/products_test.go", "test", 25, 0)])],
                Q("good", 4, "the report query groups sale lines by product name", "What goes wrong if two products share a name?",
                  "They would be merged into one row. I should group by product id and select the name."),
                0.9, 0.95, prs=[(8, "Reports", True), (12, "Low stock", True)]),
            "S06-S4": S(
                [T("T1", "Barcode lookup", "Find a product by scanning its barcode.",
                   ["GET /products/barcode/{code}", "404 for unknown code", "Index on barcode"], 3, 2, "Done", [1, 1, 1], 4,
                   """CREATE UNIQUE INDEX idx_products_barcode ON products (barcode) WHERE barcode IS NOT NULL;"""),
                 T("T2", "Supplier orders", "Create purchase orders to restock.",
                   ["Supplier CRUD", "Purchase order with lines", "Receiving an order increases stock"], 8, 5, "Partially Done", [1, 1, 0], 3,
                   """func (s *SupplierStore) Create(ctx context.Context, sp *models.Supplier) error {
	return s.db.QueryRowContext(ctx, `INSERT INTO suppliers (name, phone) VALUES ($1,$2) RETURNING id`, sp.Name, sp.Phone).Scan(&sp.ID)
}   // receiving an order is not implemented""")],
                [(0, 10, "barcode column and index", "T1", [("api/models/product.go", "code", 4, 0), ("api/store/products.go", "code", 13, 0)]),
                 (1, 15, "barcode handler", "T1", [("api/handlers/products.go", "code", 17, 0)]),
                 (3, 11, "supplier model and store", "T2", [("api/models/supplier.go", "code", 22, 0), ("api/store/suppliers.go", "code", 58, 0)]),
                 (4, 16, "supplier handlers", "T2", [("api/handlers/suppliers.go", "code", 66, 0)]),
                 (6, 10, "purchase order model", "T2", [("api/models/supplier.go", "code", 28, 0)]),
                 (8, 14, "barcode test", "T1", [("api/store/products_test.go", "test", 19, 0)]),
                 (10, 11, "wire supplier routes", "T2", [("api/main.go", "code", 8, 0)])],
                Q("good", 4, "the barcode index is unique only where barcode is not null", "Why the WHERE clause?",
                  "Many products have no barcode. Without it all the NULLs would count as duplicates in some databases."),
                0.9, 0.95, prs=[(5, "Barcode", True), (11, "Suppliers", True)]),
        },
        "SYN-027": {
            "class": "last_minute_rusher", "scenario": "React admin pages built in the last days; one is half finished each sprint",
            "S06-S1": S(
                [T("T1", "Products admin page", "A table of products with create and edit.",
                   ["Table of products from the API", "Create form", "Edit in place", "Delete with confirmation"], 8, 4, "Partially Done", [1, 1, 0, 0], 2,
                   """export default function Products() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get('/products').then(r => setRows(r.data)); }, []);
  return <table>{rows.map(p => <tr key={p.id}><td>{p.sku}</td><td>{p.name}</td><td>{p.price}</td></tr>)}</table>;
}""")],
                [(11, 20, "products table", "T1", [("admin/src/pages/Products.jsx", "code", 87, 0), ("admin/src/api.js", "code", 22, 0)]),
                 (12, 23, "create form", "T1", [("admin/src/pages/Products.jsx", "code", 54, 6)]),
                 (13, 18, "routes", "T1", [("admin/src/App.jsx", "code", 24, 0)])],
                Q("partial", 3, "Products fetches the list on mount", "What does api.get return?", "The response, and .data has the list."), 0.8, 0.9, prs=[(13, "Products page", True)]),
            "S06-S2": S(
                [T("T1", "Sales screen", "Cashier screen to scan items and complete a sale.",
                   ["Add items by SKU", "Running total", "Complete sale button", "Error when stock is too low"], 8, 5, "Partially Done", [1, 1, 1, 0], 3,
                   """const complete = async () => { await api.post('/sales', { lines }); setLines([]); };
// a 409 from the API is not caught""")],
                [(12, 14, "sales screen skeleton", "T1", [("admin/src/pages/Sales.jsx", "code", 72, 0)]),
                 (12, 22, "running total", "T1", [("admin/src/pages/Sales.jsx", "code", 19, 3)]),
                 (13, 11, "complete sale call", "T1", [("admin/src/pages/Sales.jsx", "code", 13, 0)]),
                 (13, 21, "route", "T1", [("admin/src/App.jsx", "code", 5, 0)])],
                Q("good", 4, "complete posts the lines and clears them", "What if the post fails?",
                  "The lines are cleared only after await, so a throw skips setLines. But there is no message, so the cashier does not know."), 0.8, 0.9,
                prs=[(13, "Sales screen", True)]),
            "S06-S3": S(
                [T("T1", "Reports page", "Charts for daily sales and top products.",
                   ["Daily totals chart", "Top products list", "Date range picker"], 5, 3, "Done", [1, 1, 0], 3,
                   """<LineChart data={days}><XAxis dataKey="day" /><YAxis /><Line dataKey="total" /></LineChart>""")],
                [(11, 21, "reports page", "T1", [("admin/src/pages/Reports.jsx", "code", 96, 0)]),
                 (12, 19, "top products list", "T1", [("admin/src/pages/Reports.jsx", "code", 27, 3)]),
                 (13, 12, "nav link", "T1", [("admin/src/App.jsx", "code", 6, 0)])],
                Q("partial", 3, "Reports draws a line chart from the days array", "Where do the days come from?", "From the report endpoint, one object per day."), 0.8, 0.9,
                prs=[(13, "Reports page", True)]),
            "S06-S4": S(
                [T("T1", "Low stock banner", "Show a banner when products are below reorder level.",
                   ["Banner on every page", "Shows count", "Links to the list"], 3, 2, "Done", [1, 1, 1], 4,
                   """{low > 0 && <div className="banner">{low} products low on stock. <Link to="/products?low=1">View</Link></div>}"""),
                 T("T2", "Error toasts", "Show API errors as toasts.",
                   ["Toast component", "Axios interceptor shows message"], 3, 2, "Partially Done", [1, 0], 3,
                   """api.interceptors.response.use(r => r, e => { console.error(e); return Promise.reject(e); });   // toast not shown yet""")],
                [(9, 22, "low stock banner", "T1", [("admin/src/App.jsx", "code", 21, 2)]),
                 (11, 13, "interceptor", "T2", [("admin/src/api.js", "code", 8, 0)]),
                 (12, 20, "toast component", "T2", [("admin/src/App.jsx", "code", 28, 0)]),
                 (13, 22, "last styling", None, [("admin/src/App.jsx", "code", 12, 6)])],
                Q("good", 4, "the interceptor returns Promise.reject so callers still see the error", "Why not swallow the error in the interceptor?",
                  "The page may need to react to it too, for example stop a spinner."), 0.85, 0.9, prs=[(13, "Banner and toasts", True)]),
        },
        "SYN-028": {
            "class": "reviewer_coordinator", "scenario": "reviews every PR, keeps the board and merges; moderate coding in sprints 2 and 3; sprint 4 stretched thin so reviews get shorter",
            "S06-S1": S(
                [T("T1", "CI and linting", "GitHub Actions for tests and golangci-lint.",
                   ["Tests run on pull requests", "Lint step", "Status check required"], 3, 3, "Done", [1, 1, 1], 4,
                   "- run: go test ./...\n- uses: golangci/golangci-lint-action@v6")],
                [(0, 10, "ci workflow", "T1", [(".github/workflows/ci.yml", "config_or_docs", 29, 0)]),
                 (1, 14, "readme with run steps", "T1", [("README.md", "config_or_docs", 40, 0)]),
                 (5, 15, "docker compose for postgres", "T1", [("docker-compose.yml", "config_or_docs", 18, 0)])],
                Q("good", 4, "CI runs go test on every pull request", "What does a required status check do?", "It blocks merging until CI passes."), 0.95, 0.85,
                mfo=3,
                reviews=[(6, "SYN-026", "COMMENTED", "Create maps the unique violation correctly, but the handler returns 500 for ErrDuplicateSKU. Map it to 409 with a message so the admin page can show it.", "substantive"),
                         (13, "SYN-026", "APPROVED", "JWT parse returns an error for an expired token but the middleware answers 403. Expired should be 401 so the client can refresh. Not blocking.", "substantive"),
                         (13, "SYN-027", "COMMENTED", "The products table has no way to edit or delete yet, the acceptance criteria list both. Is that planned for next sprint?", "substantive")],
                comments=[(7, "SYN-026", "Will map it to 409. @SYN-028 thanks", 1, 1)]),
            "S06-S2": S(
                [T("T1", "Suppliers and categories lookup tables", "Small lookup tables for the product form.",
                   ["Category table", "Supplier name list endpoint"], 3, 2, "Done", [1, 1], 4,
                   """func (s *Store) Categories(ctx context.Context) ([]string, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT name FROM categories ORDER BY name`)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []string
	for rows.Next() { var n string; if err := rows.Scan(&n); err != nil { return nil, err }; out = append(out, n) }
	return out, rows.Err()
}""")],
                [(2, 10, "categories store", "T1", [("api/store/products.go", "code", 26, 0)]),
                 (3, 15, "categories handler", "T1", [("api/handlers/products.go", "code", 18, 0)]),
                 (8, 11, "categories test", "T1", [("api/store/products_test.go", "test", 24, 0)])],
                Q("good", 4, "Categories returns rows.Err after the loop", "Why check rows.Err?", "Because rows.Next returns false on an error too, and the error is only available afterwards."), 0.95, 0.85,
                mfo=5,
                reviews=[(2, "SYN-026", "CHANGES_REQUESTED", "Complete() starts a transaction but the idempotency check for a repeated request is not there. A double click would create two sales. Add a unique key per sale and return the first result for a repeat.", "substantive"),
                         (5, "SYN-026", "APPROVED", "The conditional update with RowsAffected is a clean way to avoid overselling, test for rollback covers it.", "substantive"),
                         (12, "SYN-027", "COMMENTED", "The sales screen does not catch a 409. Show the message from the API, a cashier will not read the console.", "substantive"),
                         (13, "SYN-029", "COMMENTED", "The supplier, customer and category handlers repeat the same decode, validate and encode code. Extract a small helper function for the JSON decode and error response, otherwise a bug fix has to be copied into every handler.", "substantive"),
                         (13, "SYN-030", "APPROVED", "ok", "approval")],
                comments=[(3, "SYN-026", "Added the key, please look again @SYN-028", 1, 1), (13, "SYN-027", "Will do.", 1, 0)]),
            "S06-S3": S(
                [T("T1", "Stocktake import", "Upload a CSV from the shelf count and adjust stock.",
                   ["CSV with sku and counted quantity", "Differences shown before applying", "Apply adjusts stock in one transaction"], 5, 4, "Partially Done", [1, 1, 0], 3,
                   """func parseCount(r io.Reader) (map[string]int, error) {
	rd := csv.NewReader(r)
	out := map[string]int{}
	for {
		rec, err := rd.Read()
		if err == io.EOF { return out, nil }
		if err != nil { return nil, err }
		n, err := strconv.Atoi(rec[1])
		if err != nil { return nil, fmt.Errorf("bad quantity for %s: %w", rec[0], err) }
		out[rec[0]] = n
	}
}""")],
                [(1, 11, "csv parser", "T1", [("api/handlers/products.go", "code", 31, 0)]),
                 (2, 15, "diff preview", "T1", [("api/handlers/products.go", "code", 24, 0)]),
                 (4, 10, "parser test", "T1", [("api/handlers/products_test.go", "test", 29, 0)]),
                 (9, 14, "header row skipped", "T1", [("api/handlers/products.go", "code", 3, 1)])],
                Q("good", 4, "parseCount returns an error naming the SKU with a bad quantity", "Why wrap with %w?", "So callers can use errors.Is or errors.As on the original error."), 0.95, 0.85,
                mfo=4, prs=[(10, "Stocktake import", True)],
                reviews=[(3, "SYN-026", "COMMENTED", "The report groups by product name. Two products with the same name will be merged, group by id and return the name. Also cache only the last minute as in the criteria, right now nothing is cached.", "substantive"),
                         (6, "SYN-029", "APPROVED", "Supplier phone should be validated, but fine for now.", "brief"),
                         (8, "SYN-030", "COMMENTED", "Is the stock adjustment audited somewhere? I cannot see who changed it.", "brief"),
                         (12, "SYN-027", "APPROVED", "Reports page works, the date picker is missing though.", "brief")],
                comments=[(4, "SYN-026", "Will group by id. @SYN-028", 1, 1)]),
            "S06-S4": S(
                [T("T1", "Release notes and demo data", "Seed script and release notes.",
                   ["Seed script", "Release notes"], 2, 2, "Done", [1, 1], 3, "go run ./cmd/seed -n 200")],
                [(8, 11, "seed script", "T1", [("api/store/db.go", "code", 33, 0)]),
                 (11, 15, "release notes", "T1", [("docs/release-notes.md", "config_or_docs", 29, 0)])],
                Q("partial", 3, "seed inserts 200 random products", "Does seed run twice safely?", "No, it would fail on duplicate SKUs."), 0.95, 0.85,
                mfo=3,
                reviews=[(5, "SYN-026", "APPROVED", "ok", "approval"),
                         (9, "SYN-027", "COMMENTED", "Looks fine.", "brief"),
                         (12, "SYN-030", "APPROVED", "good", "approval")]),
        },
        "SYN-029": {
            "class": "no_specific_pattern", "scenario": "high volume of easy work: many CRUD handlers copied with small changes; lots of lines, low complexity, little review",
            "S06-S1": S(
                [T("T1", "Supplier CRUD", "Create, read, update, delete suppliers.",
                   ["Four endpoints", "Name required", "Phone format checked"], 2, 2, "Done", [1, 1, 0], 3,
                   """func (h *SupplierHandler) Create(w http.ResponseWriter, r *http.Request) {
	var s models.Supplier
	if err := json.NewDecoder(r.Body).Decode(&s); err != nil { http.Error(w, "bad json", 400); return }
	if s.Name == "" { http.Error(w, "name required", 400); return }
	if err := h.store.Create(r.Context(), &s); err != nil { http.Error(w, err.Error(), 500); return }
	json.NewEncoder(w).Encode(s)
}""")],
                [(0, 15, "supplier model", "T1", [("api/models/supplier.go", "code", 18, 0)]),
                 (1, 11, "supplier store", "T1", [("api/store/suppliers.go", "code", 142, 0)]),
                 (2, 14, "supplier handlers", "T1", [("api/handlers/suppliers.go", "code", 188, 0)]),
                 (4, 10, "supplier routes", "T1", [("api/main.go", "code", 12, 0)]),
                 (7, 15, "validation", "T1", [("api/handlers/suppliers.go", "code", 24, 3)])],
                Q("partial", 3, "Create decodes JSON, checks the name, then stores", "Why does the handler return err.Error() as the body?",
                  "It was quick for debugging. It could leak internal details."), 0.95, 0.9, prs=[(8, "Supplier CRUD", True)]),
            "S06-S2": S(
                [T("T1", "Customer CRUD", "Create, read, update, delete customers.",
                   ["Four endpoints", "Email required", "Search by phone"], 2, 2, "Done", [1, 1, 0], 3,
                   """// same shape as the supplier handlers, copied and adapted"""),
                 T("T2", "Category CRUD", "Create, read, update, delete categories.",
                   ["Four endpoints", "Unique name"], 2, 2, "Done", [1, 1], 3, "// same shape again")],
                [(1, 11, "customer model and store", "T1", [("api/store/suppliers.go", "code", 131, 0), ("api/models/supplier.go", "code", 26, 0)]),
                 (2, 14, "customer handlers", "T1", [("api/handlers/suppliers.go", "code", 176, 0)]),
                 (3, 10, "category store", "T2", [("api/store/products.go", "code", 108, 0)]),
                 (3, 16, "category handlers", "T2", [("api/handlers/products.go", "code", 152, 0)]),
                 (5, 15, "routes", "T2", [("api/main.go", "code", 18, 0)]),
                 (9, 11, "tests for customers", "T1", [("api/store/suppliers_test.go", "test", 84, 0)])],
                Q("partial", 3, "customer handlers follow the supplier handlers", "What would you extract from these handlers?",
                  "The decode and error parts. They are repeated in every handler."), 0.9, 0.9, prs=[(6, "Customers and categories", True)]),
            "S06-S3": S(
                [T("T1", "Purchase history per customer", "List a customer's past sales.",
                   ["Endpoint by customer id", "Newest first", "Includes line items"], 3, 2, "Done", [1, 1, 1], 4,
                   """SELECT s.id, s.created_at, l.product_id, l.qty FROM sales s JOIN sale_lines l ON l.sale_id = s.id WHERE s.customer_id = $1 ORDER BY s.created_at DESC""")],
                [(2, 12, "history query", "T1", [("api/store/sales.go", "code", 38, 0)]),
                 (3, 15, "history handler", "T1", [("api/handlers/sales.go", "code", 55, 0)]),
                 (6, 11, "history test", "T1", [("api/store/sales_test.go", "test", 41, 0)]),
                 (9, 14, "extract JSON helper", None, [("api/handlers/suppliers.go", "code", 12, 74), ("api/handlers/products.go", "code", 9, 61)])],
                Q("good", 4, "history joins sales and sale lines for one customer", "Why order by created_at descending?", "The newest purchases are the most useful at the top."), 0.9, 0.9,
                prs=[(10, "History and helper", True)]),
            "S06-S4": S(
                [T("T1", "Export products to CSV", "Download the product list as CSV.",
                   ["GET /products/export", "Header row", "UTF-8 with BOM for Excel"], 2, 2, "Done", [1, 1, 0], 3,
                   """w.Header().Set("Content-Type", "text/csv")
cw := csv.NewWriter(w)
cw.Write([]string{"sku", "name", "price", "stock"})
for _, p := range ps { cw.Write([]string{p.SKU, p.Name, fmt.Sprint(p.Price), fmt.Sprint(p.Stock)}) }
cw.Flush()""")],
                [(2, 13, "export handler", "T1", [("api/handlers/products.go", "code", 34, 0)]),
                 (7, 15, "export test", "T1", [("api/handlers/products_test.go", "test", 28, 0)])],
                Q("good", 4, "export writes with csv.Writer and flushes", "What happens if you forget Flush?", "The last buffered rows are never written."), 0.9, 0.9, prs=[(8, "Export", True)]),
        },
        "SYN-030": {
            "class": "no_specific_pattern", "scenario": "strong start, then fades: good first sprint, weaker second, almost nothing third, leaves before sprint 4",
            "S06-S1": S(
                [T("T1", "Sales database schema and migrations", "Tables for sales and sale lines with migrations.",
                   ["sales and sale_lines tables", "Foreign keys and indexes", "Migration tool configured", "Rollback scripts"], 5, 4, "Done", [1, 1, 1, 1], 5,
                   """CREATE TABLE sale_lines (
  id BIGSERIAL PRIMARY KEY,
  sale_id BIGINT NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  qty INT NOT NULL CHECK (qty > 0),
  unit_price NUMERIC(10,2) NOT NULL
);
CREATE INDEX idx_sale_lines_sale ON sale_lines(sale_id);""")],
                [(0, 11, "initial schema", "T1", [("db/migrations/001_init.sql", "config_or_docs", 64, 0)]),
                 (1, 14, "sales tables", "T1", [("db/migrations/002_sales.sql", "config_or_docs", 41, 0)]),
                 (2, 10, "migration runner", "T1", [("api/store/db.go", "code", 38, 0)]),
                 (3, 15, "down migrations", "T1", [("db/migrations/002_sales.down.sql", "config_or_docs", 9, 0)]),
                 (5, 11, "indexes", "T1", [("db/migrations/003_indexes.sql", "config_or_docs", 12, 0)]),
                 (6, 16, "migration tests", "T1", [("api/store/db_test.go", "test", 33, 0)]),
                 (9, 10, "fix check constraint", "T1", [("db/migrations/002_sales.sql", "config_or_docs", 2, 2)])],
                Q("strong", 5, "sale_lines.qty has CHECK (qty > 0)", "Why put the rule in the database too?",
                  "Application code can have bugs or be bypassed by a script. The database is the last guard."), 0.9, 0.95, prs=[(7, "Schema", True), (10, "Constraint fix", True)]),
            "S06-S2": S(
                [T("T1", "Receipt generation", "Create a printable receipt for a sale.",
                   ["Receipt shows lines and total", "Shop name and date", "Printable layout"], 5, 3, "Partially Done", [1, 1, 0], 3,
                   """func Receipt(s *models.Sale) string {
	var b strings.Builder
	fmt.Fprintf(&b, "SHOP\\n%s\\n", s.CreatedAt.Format("2006-01-02 15:04"))
	for _, l := range s.Lines { fmt.Fprintf(&b, "%-20s %3d %8.2f\\n", l.Name, l.Qty, l.Price*float64(l.Qty)) }
	fmt.Fprintf(&b, "TOTAL %8.2f\\n", s.Total())
	return b.String()
}""")],
                [(3, 15, "receipt text", "T1", [("api/models/sale.go", "code", 31, 0)]),
                 (7, 11, "receipt endpoint", "T1", [("api/handlers/sales.go", "code", 17, 0)]),
                 (10, 14, "receipt test", "T1", [("api/models/sale_test.go", "test", 22, 0)])],
                Q("good", 4, "Receipt formats each line with fixed width columns", "What happens with a long product name?",
                  "The %-20s pads but does not cut, so a long name pushes the numbers right."), 0.85, 0.9, prs=[(11, "Receipt", True)]),
            "S06-S3": S(
                [T("T1", "Stock audit log", "Record who changed stock and why.",
                   ["audit table", "Every adjustment logged", "Admin can view the log"], 5, 3, "To Do", [0, 0, 0], 1)],
                [(13, 21, "audit table sketch", None, [("db/migrations/004_audit.sql", "config_or_docs", 9, 0)])],
                Q("weak", 2, "audit table migration", "Which actions are logged?", "Stock adjustments, but nothing writes to it yet."), 1.0, 0.0),
        },
    },
}
