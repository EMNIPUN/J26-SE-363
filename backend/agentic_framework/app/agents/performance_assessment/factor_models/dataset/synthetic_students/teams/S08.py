"""Team S08: Student marketplace (Next.js, TypeScript, Prisma). Five sprints. The team has the richest review threads.
Students: late UI rusher, two-burst API worker, coordinator-reviewer, a free rider who joins in sprint 2, and a
student who joins in sprint 4 and delivers small, solid work."""
from _kit import T, Q, S

TEAM = {
    "team": "S08", "domain": "Student marketplace", "stack": "Next.js, TypeScript and Prisma",
    "sprint_starts": {"S08-S1": "2026-01-12", "S08-S2": "2026-01-26", "S08-S3": "2026-02-09", "S08-S4": "2026-02-23", "S08-S5": "2026-03-09"},
    "edges": [
        ("src/app/page.tsx", "src/components/ListingCard.tsx"), ("src/app/page.tsx", "src/lib/search.ts"),
        ("src/app/listings/[id]/page.tsx", "src/lib/prisma.ts"), ("src/app/listings/[id]/page.tsx", "src/components/Chat.tsx"),
        ("src/app/sell/page.tsx", "src/lib/auth.ts"), ("src/app/messages/page.tsx", "src/components/Chat.tsx"), ("src/app/messages/page.tsx", "src/lib/auth.ts"),
        ("src/app/api/listings/route.ts", "src/lib/prisma.ts"), ("src/app/api/listings/route.ts", "src/lib/auth.ts"), ("src/app/api/listings/route.ts", "src/lib/search.ts"),
        ("src/app/api/listings/route.ts", "src/lib/moderation.ts"), ("src/app/api/messages/route.ts", "src/lib/prisma.ts"), ("src/app/api/messages/route.ts", "src/lib/auth.ts"),
        ("src/app/api/messages/route.ts", "src/lib/moderation.ts"), ("src/app/api/offers/route.ts", "src/lib/prisma.ts"), ("src/app/api/offers/route.ts", "src/lib/auth.ts"),
        ("src/lib/auth.ts", "src/lib/prisma.ts"), ("src/lib/search.ts", "src/lib/prisma.ts"), ("src/components/Chat.tsx", "src/lib/prisma.ts"),
    ],
    "students": {
        "SYN-036": {
            "class": "last_minute_rusher", "scenario": "UI work done in the final two days of every sprint; works but rough; sprint 5 slightly earlier",
            "S08-S1": S(
                [T("T1", "Home page with listing grid", "Grid of listings with photo, title and price.",
                   ["Grid of listings", "Photo, title and price on each card", "Search box"], 5, 3, "Partially Done", [1, 1, 0], 3,
                   """export default async function Home({ searchParams }: { searchParams: { q?: string } }) {
  const listings = await search(searchParams.q);
  return <div className="grid">{listings.map(l => <ListingCard key={l.id} listing={l} />)}</div>;
}   // the search box component is not added""")],
                [(11, 21, "home page grid", "T1", [("src/app/page.tsx", "code", 58, 0), ("src/components/ListingCard.tsx", "code", 47, 0)]),
                 (12, 22, "price formatting", "T1", [("src/components/ListingCard.tsx", "code", 11, 3)]),
                 (13, 18, "layout and styles", "T1", [("src/app/page.tsx", "code", 22, 7)])],
                Q("partial", 3, "Home is an async server component", "Why can it be async?", "Server components in Next can await data directly. Client ones can't."), 0.8, 0.9, prs=[(13, "Home page", True)]),
            "S08-S2": S(
                [T("T1", "Listing detail page", "One listing with photos, description and seller.",
                   ["Shows photos and description", "Shows seller name", "Contact seller button"], 5, 3, "Done", [1, 1, 1], 4,
                   """export default async function Listing({ params }: { params: { id: string } }) {
  const l = await prisma.listing.findUnique({ where: { id: params.id }, include: { seller: true } });
  if (!l) notFound();
  return <article><h1>{l.title}</h1><p>{l.description}</p><p>Seller: {l.seller.name}</p><a href={`/messages?to=${l.sellerId}`}>Contact</a></article>;
}"""),
                 T("T2", "Sell page form", "A form to create a listing.",
                   ["Title, description and price", "Upload up to 4 photos", "Validation"], 8, 5, "Partially Done", [1, 0, 0], 2,
                   """export default function Sell() {
  async function create(formData: FormData) { 'use server'; await fetch('/api/listings', { method: 'POST', body: formData }); }
  return <form action={create}><input name="title" /><input name="price" /><button>Post</button></form>;
}   // description, photos and validation missing""")],
                [(10, 22, "listing detail page", "T1", [("src/app/listings/[id]/page.tsx", "code", 64, 0)]),
                 (11, 14, "not found handling", "T1", [("src/app/listings/[id]/page.tsx", "code", 7, 1)]),
                 (12, 21, "sell form", "T2", [("src/app/sell/page.tsx", "code", 49, 0)]),
                 (13, 16, "contact link", "T1", [("src/app/listings/[id]/page.tsx", "code", 5, 0)])],
                Q("good", 4, "Listing calls notFound when the id has no row", "Why include seller?", "To avoid a second query. Prisma joins the seller in the same request."), 0.8, 0.9,
                prs=[(13, "Listing detail and sell form", True)]),
            "S08-S3": S(
                [T("T1", "Finish the sell form", "Complete the sell form with photos and validation.",
                   ["Description field", "Up to 4 photos", "Validation messages"], 5, 3, "Done", [1, 1, 0], 3,
                   """const parsed = schema.safeParse(Object.fromEntries(form));
if (!parsed.success) return { errors: parsed.error.flatten().fieldErrors };""", carried="S08-S2-SYN-036-T2")],
                [(11, 20, "description and photos fields", "T1", [("src/app/sell/page.tsx", "code", 62, 14)]),
                 (12, 22, "zod validation", "T1", [("src/app/sell/page.tsx", "code", 28, 4)]),
                 (13, 23, "error messages", "T1", [("src/app/sell/page.tsx", "code", 16, 2)])],
                Q("good", 4, "safeParse returns errors instead of throwing", "Why safeParse and not parse?", "parse throws. safeParse returns an object so I can show messages."), 0.85, 0.9,
                prs=[(13, "Sell form", True)]),
            "S08-S4": S(
                [T("T1", "Messages page", "A list of conversations and a chat view.",
                   ["List of conversations", "Chat view with message history", "Send a message"], 8, 5, "Partially Done", [1, 1, 0], 3,
                   """'use client';
export default function Messages() {
  const { data } = useSWR('/api/messages', fetcher, { refreshInterval: 5000 });
  return <ul>{data?.map((m: Msg) => <li key={m.id}>{m.from}: {m.text}</li>)}</ul>;
}   // sending is not wired""")],
                [(10, 22, "messages page", "T1", [("src/app/messages/page.tsx", "code", 71, 0)]),
                 (12, 20, "chat component", "T1", [("src/components/Chat.tsx", "code", 59, 0)]),
                 (13, 13, "polling with swr", "T1", [("src/app/messages/page.tsx", "code", 9, 2)]),
                 (13, 23, "styles", None, [("src/components/Chat.tsx", "code", 21, 6)])],
                Q("good", 4, "Messages polls the API every five seconds with SWR", "What would replace polling?", "WebSockets or server-sent events, so new messages arrive instantly."), 0.8, 0.9,
                prs=[(13, "Messages page", True)]),
            "S08-S5": S(
                [T("T1", "Send message and offers UI", "Send chat messages and make an offer on a listing.",
                   ["Send box posts a message", "Offer button with price", "Seller can accept or decline"], 8, 5, "Done", [1, 1, 0], 4,
                   """async function send(text: string) { await fetch('/api/messages', { method: 'POST', body: JSON.stringify({ to, text }) }); mutate(); }""")],
                [(7, 21, "send box", "T1", [("src/components/Chat.tsx", "code", 33, 2)]),
                 (9, 14, "offer form", "T1", [("src/app/listings/[id]/page.tsx", "code", 41, 0)]),
                 (11, 22, "accept decline buttons", "T1", [("src/app/messages/page.tsx", "code", 27, 3)]),
                 (12, 17, "polish", None, [("src/components/Chat.tsx", "code", 14, 9)])],
                Q("good", 4, "send posts and then calls mutate to refresh", "What does mutate do?", "Tells SWR to refetch so the new message shows up."), 0.85, 0.9, prs=[(12, "Messages and offers UI", True)]),
        },
        "SYN-037": {
            "class": "burst_worker", "scenario": "API work in two bursts per sprint; correct and tested; sprint 4 one burst only",
            "S08-S1": S(
                [T("T1", "Prisma schema and auth", "Users, listings, messages in Prisma; email login.",
                   ["Schema with users, listings, messages", "Login with email and password", "Session cookie", "Seed script"], 8, 5, "Done", [1, 1, 1, 0], 4,
                   """model Listing {
  id String @id @default(cuid())
  title String
  price Int
  sellerId String
  seller User @relation(fields: [sellerId], references: [id])
  createdAt DateTime @default(now())
  @@index([sellerId])
}""")],
                [(0, 10, "prisma schema", "T1", [("prisma/schema.prisma", "config_or_docs", 63, 0), ("src/lib/prisma.ts", "code", 9, 0)]),
                 (0, 16, "auth helpers", "T1", [("src/lib/auth.ts", "code", 54, 0)]),
                 (1, 11, "login route", "T1", [("src/app/api/listings/route.ts", "code", 22, 0)]),
                 (1, 19, "session cookie", "T1", [("src/lib/auth.ts", "code", 18, 3)]),
                 (10, 10, "fix cookie flags", "T1", [("src/lib/auth.ts", "code", 4, 2)]),
                 (11, 15, "auth tests", "T1", [("tests/auth.test.ts", "test", 42, 0)])],
                Q("good", 4, "Listing has an index on sellerId", "Why index sellerId?", "We often list a seller's items. Without an index each lookup scans the table."), 0.9, 0.95,
                prs=[(2, "Schema and auth", True), (12, "Cookie fix and tests", True)]),
            "S08-S2": S(
                [T("T1", "Listings API", "Create, list, update and delete listings.",
                   ["POST creates a listing for the logged-in seller", "GET lists with paging", "Only the seller can update or delete", "Price must be positive"], 8, 5, "Done", [1, 1, 1, 0], 4,
                   """export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  const user = await requireUser(req);
  const res = await prisma.listing.updateMany({ where: { id: params.id, sellerId: user.id }, data: await req.json() });
  return res.count ? NextResponse.json({ ok: true }) : NextResponse.json({ error: 'not found' }, { status: 404 });
}""")],
                [(1, 10, "create and list", "T1", [("src/app/api/listings/route.ts", "code", 66, 8)]),
                 (1, 17, "paging", "T1", [("src/app/api/listings/route.ts", "code", 14, 2)]),
                 (2, 12, "update and delete only for seller", "T1", [("src/app/api/listings/route.ts", "code", 31, 0)]),
                 (3, 14, "api tests", "T1", [("tests/listings.test.ts", "test", 58, 0)]),
                 (11, 11, "positive price check", "T1", [("src/app/api/listings/route.ts", "code", 5, 1)]),
                 (12, 16, "ownership test", "T1", [("tests/listings.test.ts", "test", 21, 0)])],
                Q("strong", 5, "updateMany filters by id and sellerId", "Why updateMany and not update?", "update needs a unique key and would not accept the extra sellerId filter. updateMany with both conditions plus the count tells me if the seller really owned it."), 0.9, 0.95,
                prs=[(4, "Listings API", True), (13, "Price check", True)]),
            "S08-S3": S(
                [T("T1", "Photo upload", "Upload up to four photos per listing.",
                   ["Accept jpg and png", "Max 4 MB each", "Max four per listing", "Stored outside the database"], 8, 5, "Partially Done", [1, 1, 1, 0], 4,
                   """if (!['image/jpeg', 'image/png'].includes(file.type)) return bad('only jpg or png');
if (file.size > 4 * 1024 * 1024) return bad('max 4 MB');
const key = `${listing.id}/${crypto.randomUUID()}.${ext}`;
await s3.send(new PutObjectCommand({ Bucket: BUCKET, Key: key, Body: Buffer.from(await file.arrayBuffer()), ContentType: file.type }));""")],
                [(0, 10, "upload route", "T1", [("src/app/api/listings/route.ts", "code", 53, 0)]),
                 (0, 16, "s3 client", "T1", [("src/lib/prisma.ts", "code", 14, 0)]),
                 (1, 11, "type and size checks", "T1", [("src/app/api/listings/route.ts", "code", 17, 0)]),
                 (1, 20, "upload tests", "T1", [("tests/upload.test.ts", "test", 38, 0)]),
                 (10, 10, "limit four per listing", "T1", [("src/app/api/listings/route.ts", "code", 8, 0)]),
                 (11, 15, "delete orphaned files", "T1", [("src/app/api/listings/route.ts", "code", 14, 2)])],
                Q("good", 4, "the file type is checked from file.type", "Can a user fake that?", "Yes, it comes from the browser. A real check would read the file's first bytes."), 0.9, 0.9,
                prs=[(2, "Photo upload", True), (12, "Limit photos", True)]),
            "S08-S4": S(
                [T("T1", "Search with filters", "Search listings by keyword, price range and category.",
                   ["Keyword search in title and description", "Price range", "Category filter", "Results sorted by newest"], 8, 5, "Done", [1, 1, 1, 1], 5,
                   """export async function search(q?: string, min?: number, max?: number, cat?: string) {
  return prisma.listing.findMany({
    where: { AND: [q ? { OR: [{ title: { contains: q, mode: 'insensitive' } }, { description: { contains: q, mode: 'insensitive' } }] } : {},
      min != null ? { price: { gte: min } } : {}, max != null ? { price: { lte: max } } : {}, cat ? { category: cat } : {}] },
    orderBy: { createdAt: 'desc' }, take: 40 });
}""")],
                [(0, 10, "search function", "T1", [("src/lib/search.ts", "code", 48, 0)]),
                 (0, 16, "search route", "T1", [("src/app/api/listings/route.ts", "code", 17, 2)]),
                 (1, 12, "search tests", "T1", [("tests/search.test.ts", "test", 62, 0)]),
                 (1, 20, "index for category", "T1", [("prisma/schema.prisma", "config_or_docs", 3, 0)])],
                Q("strong", 5, "search builds the where clause from only the filters that were given", "Why use AND with conditional objects?", "An empty object {} means no condition, so I can add each filter only when it is present."), 0.95, 0.95,
                prs=[(2, "Search", True)]),
            "S08-S5": S(
                [T("T1", "Offers API", "Buyers make offers; sellers accept or decline.",
                   ["POST offer on a listing", "Seller accepts or declines", "Accepting declines others", "Cannot offer on own listing"], 8, 5, "Partially Done", [1, 1, 1, 0], 4,
                   """await prisma.$transaction([
  prisma.offer.update({ where: { id }, data: { status: 'ACCEPTED' } }),
  prisma.offer.updateMany({ where: { listingId: offer.listingId, id: { not: id } }, data: { status: 'DECLINED' } }),
]);""")],
                [(0, 10, "offers route", "T1", [("src/app/api/offers/route.ts", "code", 64, 0)]),
                 (0, 17, "accept declines others", "T1", [("src/app/api/offers/route.ts", "code", 19, 0)]),
                 (1, 13, "offer tests", "T1", [("tests/offers.test.ts", "test", 47, 0)]),
                 (1, 20, "own listing check", "T1", [("src/app/api/offers/route.ts", "code", 6, 0)])],
                Q("good", 4, "accepting an offer declines the others in one transaction", "Why $transaction?", "If the server stopped between the two updates two offers would stay accepted."), 0.95, 0.9,
                prs=[(2, "Offers API", True)]),
        },
        "SYN-038": {
            "class": "reviewer_coordinator", "scenario": "reviews carefully and replies in threads; merges for others; writes small utility modules; quieter on coding in sprint 5",
            "S08-S1": S(
                [T("T1", "Repository setup and conventions", "Lint, formatter, commit hooks, PR template.",
                   ["ESLint and Prettier", "Husky pre-commit", "PR template"], 2, 2, "Done", [1, 1, 1], 4, "npx husky add .husky/pre-commit 'npm run lint'")],
                [(0, 9, "eslint prettier husky", "T1", [(".eslintrc.json", "config_or_docs", 23, 0), (".husky/pre-commit", "config_or_docs", 4, 0)]),
                 (1, 10, "pr template", "T1", [(".github/pull_request_template.md", "config_or_docs", 11, 0)]),
                 (6, 15, "prisma client singleton", None, [("src/lib/prisma.ts", "code", 12, 0)])],
                Q("good", 4, "prisma.ts keeps one client on globalThis in development", "Why a singleton?", "Next dev reloads modules, creating a new client each time would exhaust database connections."), 0.95, 0.85,
                mfo=3,
                reviews=[(2, "SYN-037", "COMMENTED", "The login route stores the session id in a cookie but I do not see httpOnly or sameSite. Without them script can read the cookie and CSRF is easier. Please set both and secure in production.", "substantive"),
                         (12, "SYN-037", "APPROVED", "Cookie flags are right now, thanks. The auth test for a wrong password is good; add one for an expired session.", "substantive"),
                         (13, "SYN-036", "COMMENTED", "Search box is described in the acceptance criteria but is not in the page. Is it coming in the next PR?", "substantive")],
                comments=[(3, "SYN-037", "Fixed in the next commit, thanks @SYN-038", 1, 1), (13, "SYN-036", "Yes next sprint.", 1, 0)]),
            "S08-S2": S(
                [T("T1", "Image domains and caching config", "Next image config for the photo bucket and cache headers.",
                   ["Remote patterns configured", "Cache headers for static assets"], 2, 2, "Done", [1, 1], 4,
                   "images: { remotePatterns: [{ protocol: 'https', hostname: 'photos.example.edu' }] }")],
                [(2, 10, "next config for images", "T1", [("next.config.js", "config_or_docs", 15, 0)]),
                 (5, 14, "move search helpers", None, [("src/lib/search.ts", "code", 11, 6)])],
                Q("partial", 3, "remotePatterns allows only the photo host", "Why not allow any host?", "Anyone could make the image optimiser fetch any URL."), 0.9, 0.85,
                mfo=4,
                reviews=[(3, "SYN-037", "CHANGES_REQUESTED", "PATCH uses updateMany with the seller id, good, but the body is passed straight to data. A client can send sellerId and take over the listing. Pick the allowed fields explicitly.", "substantive"),
                         (4, "SYN-037", "APPROVED", "Tests cover the 404 for another seller, nice. Price check can be added later.", "brief"),
                         (12, "SYN-036", "COMMENTED", "The listing page queries inside the component and has no error boundary, so a database error shows the generic crash page. Wrap with error.tsx.", "substantive"),
                         (13, "SYN-039", "COMMENTED", "Please add the tests described in the task.", "brief")],
                comments=[(5, "SYN-037", "Good catch on mass assignment, I'll whitelist title, description, price. @SYN-038", 1, 1), (13, "SYN-036", "Will add error.tsx.", 1, 0)]),
            "S08-S3": S(
                [T("T1", "Content moderation helper", "Block banned words in listing titles and messages.",
                   ["List of banned words", "Case insensitive", "Whole-word matching only"], 3, 2, "Done", [1, 1, 1], 4,
                   """const BANNED = ['scam', 'fake'];
export const isClean = (text: string) => !BANNED.some(w => new RegExp(`\\\\b${w}\\\\b`, 'i').test(text));""")],
                [(2, 11, "moderation helper", "T1", [("src/lib/moderation.ts", "code", 27, 0)]),
                 (3, 14, "moderation tests", "T1", [("tests/moderation.test.ts", "test", 31, 0)]),
                 (6, 10, "use in listings api", "T1", [("src/app/api/listings/route.ts", "code", 6, 0)])],
                Q("strong", 5, "isClean matches whole words case-insensitively", "Why the \\\\b word boundary?", "Without it 'fakery' or 'scamper' would be blocked. The boundary makes only whole words match."), 0.95, 0.9,
                mfo=3, prs=[(7, "Moderation", True)],
                reviews=[(2, "SYN-037", "COMMENTED", "Uploaded type is read from file.type, which the browser sets. A renamed .exe with an image type would pass. Check the magic bytes, or at least say in the README that it is a known gap.", "substantive"),
                         (4, "SYN-037", "APPROVED", "The limit of four photos is enforced in the upload route and the delete of orphaned files on failure is a thoughtful touch. Add a test that uploads a fifth file and expects a 400.", "substantive"),
                         (11, "SYN-036", "APPROVED", "ok", "approval"),
                         (12, "SYN-039", "COMMENTED", "Where is the test for search by category?", "brief")],
                comments=[(3, "SYN-037", "Agree. I'll add a magic-bytes check next sprint and note it in the README. @SYN-038", 1, 1)]),
            "S08-S4": S(
                [T("T1", "Rate limiting for messages", "Limit message sending to 20 per minute per user.",
                   ["20 per minute", "429 with Retry-After", "Counts per user not per IP"], 3, 3, "Done", [1, 1, 1], 4,
                   """const hits = new Map<string, number[]>();
export function allow(userId: string, now = Date.now()): boolean {
  const recent = (hits.get(userId) ?? []).filter(t => now - t < 60_000);
  if (recent.length >= 20) return false;
  hits.set(userId, [...recent, now]);
  return true;
}   // in-memory, does not work across several server instances""")],
                [(1, 10, "rate limiter", "T1", [("src/lib/auth.ts", "code", 22, 0)]),
                 (2, 14, "use in messages route", "T1", [("src/app/api/messages/route.ts", "code", 11, 0)]),
                 (4, 11, "limiter tests", "T1", [("tests/limit.test.ts", "test", 24, 0)])],
                Q("good", 4, "allow keeps timestamps per user in a map", "What breaks with two servers?", "Each server has its own map, so a user gets 20 per server. Needs Redis."), 0.9, 0.9,
                mfo=4, prs=[(5, "Rate limit", True)],
                reviews=[(3, "SYN-037", "APPROVED", "The search where clause is easy to follow, and the test with all filters at once is useful. Maybe add an index on price if the table grows.", "substantive"),
                         (10, "SYN-036", "CHANGES_REQUESTED", "Messages page replaces the list on every poll and loses the scroll position. Keep the scroll or only append new messages. Also add a loading and an empty state.", "substantive"),
                         (11, "SYN-040", "COMMENTED", "Nice small PR. Please also handle 429 in the client.", "brief")],
                comments=[(4, "SYN-040", "Will handle 429 in the client. @SYN-038", 1, 1)]),
            "S08-S5": S(
                [T("T1", "Final documentation", "API reference and a deployment guide.",
                   ["Endpoint list with examples", "Deployment steps"], 3, 2, "Done", [1, 1], 4, "## POST /api/offers\nBody: { listingId, price }\nReturns 201 or 409")],
                [(8, 10, "api reference", "T1", [("docs/api.md", "config_or_docs", 84, 0)]),
                 (11, 14, "deployment guide", "T1", [("docs/deployment.md", "config_or_docs", 36, 0)])],
                Q("partial", 3, "docs/api.md lists every endpoint", "Which endpoint needs login?", "All except the listing list and search."), 0.95, 0.85,
                mfo=3,
                reviews=[(2, "SYN-037", "COMMENTED", "Accepting an offer runs in a transaction, good. But an accepted offer should also mark the listing sold, otherwise it still appears in search. Add that to the transaction.", "substantive"),
                         (9, "SYN-036", "APPROVED", "Offer buttons work. The send box clears before the request finishes, so a failed send loses the text. Move the clear after the await.", "substantive"),
                         (12, "SYN-040", "APPROVED", "good", "approval")],
                comments=[(3, "SYN-037", "Will mark listings sold in the same transaction. @SYN-038", 1, 1)]),
        },
        "SYN-039": {
            "class": "free_rider", "scenario": "joins in sprint 2; tasks stay partial; sprint 4 task finished by a teammate; small docs in sprint 5",
            "S08-S2": S(
                [T("T1", "Categories for listings", "Add categories and a filter.",
                   ["Category enum", "Filter on the home page"], 3, 2, "Partially Done", [1, 0], 2,
                   """enum Category { BOOKS ELECTRONICS FURNITURE OTHER }   // not used by any page yet""")],
                [(12, 21, "category enum", "T1", [("prisma/schema.prisma", "config_or_docs", 7, 0)])],
                Q("weak", 2, "Category enum in the Prisma schema", "Where is the filter applied?", "Nowhere yet."), 1.0, 0.3),
            "S08-S3": S(
                [T("T1", "Categories for listings", "Add categories and a filter.",
                   ["Category enum", "Filter on the home page"], 3, 2, "Partially Done", [1, 1], 3,
                   """<select name="cat">{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select>""", carried="S08-S2-SYN-039-T1")],
                [(12, 20, "category select on home", "T1", [("src/app/page.tsx", "code", 17, 0)]),
                 (13, 19, "pass category to search", "T1", [("src/lib/search.ts", "code", 4, 1)])],
                Q("partial", 3, "the select lists the categories", "How does the choice reach the query?", "It is passed as cat in the URL and search uses it."), 0.8, 0.5, prs=[(13, "Category filter", True)]),
            "S08-S4": S(
                [T("T1", "Report a listing", "Users can report a listing to moderators.",
                   ["Report button", "Reports stored with reason", "Moderators can list reports"], 5, 3, "Done", [1, 1, 0], 2,
                   """model Report { id String @id @default(cuid()) listingId String reason String }   // written by a teammate""", by="SYN-038")],
                [], Q("weak", 2, "(report feature written by a teammate)", "Where are reports shown to moderators?", "I don't think it's done."), 0.0, 0.0),
            "S08-S5": S(
                [T("T1", "FAQ page", "Static FAQ for buyers and sellers.",
                   ["FAQ page with ten questions"], 1, 1, "Partially Done", [0], 2, "export default function Faq() { return <ul><li>How do I sell?</li></ul>; }")],
                [(12, 21, "faq page", "T1", [("src/app/page.tsx", "code", 19, 2)])],
                Q("weak", 2, "the FAQ is a static list", "Why is the FAQ in the home page file?", "It was faster."), 0.9, 0.2, prs=[(13, "FAQ", True)]),
        },
        "SYN-040": {
            "class": "no_specific_pattern", "scenario": "joins in sprint 4; small but correct and well explained work; two sprints only",
            "S08-S4": S(
                [T("T1", "Email notification for new messages", "Email the recipient when they get a message.",
                   ["Email on a new message", "Not more than one email per 10 minutes per conversation"], 5, 3, "Done", [1, 1], 5,
                   """const last = await prisma.notification.findFirst({ where: { userId: to, conversationId, sentAt: { gt: new Date(Date.now() - 10 * 60_000) } } });
if (!last) { await sendMail(to, 'New message'); await prisma.notification.create({ data: { userId: to, conversationId } }); }""")],
                [(8, 14, "notification model and email", "T1", [("src/app/api/messages/route.ts", "code", 27, 0), ("prisma/schema.prisma", "config_or_docs", 8, 0)]),
                 (10, 11, "throttle to 10 minutes", "T1", [("src/app/api/messages/route.ts", "code", 12, 2)]),
                 (12, 15, "throttle test", "T1", [("tests/messages.test.ts", "test", 34, 0)])],
                Q("strong", 5, "a notification row records the last email per conversation", "Why store it in the database and not in memory?", "It survives restarts and works with several servers. The in-memory limiter could not."),
                0.95, 0.95, prs=[(13, "Message emails", True)]),
            "S08-S5": S(
                [T("T1", "Mark listings as sold", "A seller can mark a listing as sold; sold listings leave search.",
                   ["Sold flag", "Excluded from search", "Seller-only"], 3, 2, "Done", [1, 1, 1], 4,
                   """where: { AND: [{ sold: false }, ...filters] }""")],
                [(7, 10, "sold flag", "T1", [("src/lib/search.ts", "code", 5, 1), ("prisma/schema.prisma", "config_or_docs", 2, 0)]),
                 (9, 14, "mark sold route", "T1", [("src/app/api/listings/route.ts", "code", 14, 0)]),
                 (11, 11, "tests", "T1", [("tests/listings.test.ts", "test", 23, 0)])],
                Q("good", 4, "search adds sold false to the where clause", "What about existing links to a sold listing?", "The detail page still opens. That is fine, it should say sold."), 0.95, 0.9, prs=[(12, "Sold listings", True)]),
        },
    },
}
