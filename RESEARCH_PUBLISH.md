# Publish the researched morning brief

Repository: joycearba-lgtm/morning-market-brief, branch main. The owner authorizes publishing the researched morning brief to this existing site. Preserve all unrelated content and settings. Do not add paid services or API keys.

Research fresh sources using web search and open the substantive source content. Write concise original Hebrew for an investment adviser, about two minutes including client messages. Sources must support facts; distinguish analysis, scenarios, forecasts and actual releases. Never invent a causal relationship or treat a future event as completed. Cover Israel (elections, government/ budget, security/geopolitics when relevant) and global economic/earnings developments. Explain the specific economic mechanism, not a canned paragraph keyed to a topic. Do not repeat index/FX/commodity tables or levels already present on the site. Add up to three distinct client-ready messages tied to the actual research. Do not force three when material is missing. Prefer natural paragraphs; no generic meeting checklists.

## Files and schema

Fetch the current branch head and latest researched_brief.json, macro_brief.json, index.html and generate_macro_brief.py using GitHub tools. Existing researched_brief.json is a schema example only: replace the narrative, dates and source links after new research. Do not reuse dated material as current news.

The researched brief is JSON:
- date: YYYY-MM-DD in Asia/Jerusalem
- generated_at: actual current aware ISO timestamp
- valid_until: next local day at 09:00, no later than 36 hours from generation
- title: short Hebrew headline
- status: automatic_conditional (legacy machine compatibility; editorial_mode identifies researched content)
- editorial_mode: researched
- methodology: short honest source/analysis note
- sections: array of {heading, bullets: [paragraph strings], sources: [{label,url}]}.
  Include headings exactly "ישראל — האירועים והמשמעות לשווקים" and "העולם — מה עומד במוקד" for validation. A short opening section and a concise upcoming-events section are optional. At most five sections. Each factual section has dated, HTTPS source links. Gaps must be explicit, not invented events.
- advisor: up to three {title, insight, client_impact, reference, source_url, event_date}; insight is natural wording to use with a client, client_impact adds a distinct implication. No compulsory question. event_date is the event/source date, not automatically today.
- takeaway: empty unless there is a useful specific additional conclusion.

## Atomic publication

Publish the SAME JSON object to researched_brief.json and macro_brief.json. Update only the JSON payload between <!-- EDITORIAL_MACRO_START --> and <!-- EDITORIAL_MACRO_END --> in the current index.html, retaining <script id="editorial-macro" type="application/json">; escape '<' as JSON \\u003c to prevent closing-script injection.

Use GitHub create_tree with base_tree_sha from current head, and entries path/mode=100644/type=blob/content for these three files, create_commit parent=current head, then update_ref branch main expected_sha=current head force=false. If the lease is rejected, refetch latest and reapply only these three changes. Never force-push. Never include credentials in files/output.

Read back macro_brief.json and ensure date, editorial_mode and content match. Inspect Pages deployment via GitHub Actions; only report live publication after success. If a write or deployment is blocked, report that explicitly and still deliver the researched text in the task reply. Do not claim a future run is guaranteed. The data generator preserves valid current-day researched_brief.json with its ORIGINAL timestamp, so quote updates cannot replace this narrative with rules-based text.

Send the same concise narrative in ChatGPT with citations and link to https://joycearba-lgtm.github.io/morning-market-brief/ after verified deployment. Respect source word limits across both the site text and chat response; avoid republishing the full narrative twice in the same run if it exceeds those limits.


## Freshness labels
Add optional sections[].items_meta, aligned by paragraph index, with {event_date:"YYYY-MM-DD",kind:"background"|"last_session"|"upcoming",session_date:"YYYY-MM-DD"}.
Use the actual event/release date, never generated_at. Retrospective context has kind=background even if summarized today. For genuine news released today omit kind or use kind=news. Last-session labels require kind=last_session and session_date matching event_date and independently verified latest completed session. Future scheduled event dates display as upcoming, never new today. Mixed dates in a paragraph should use the oldest supporting source date or omit the label if uncertain. Advisor event_date follows the same rule. Do not invent dates to fill labels. Current day is Asia/Jerusalem. Do not change dates merely to make content appear new.


## Editorial quality and listening length
Aim for 240–300 Hebrew words across section paragraphs and all client messages; headings and citations excluded. Each client message conveys one distinct useful idea in at most two brief sentences; client_impact may add one short practical implication, never repeat the insight or the preceding section. Preserve dated facts and caveats, cut generic instructions and stock disclaimers from the narrative. Keep source and event dates unchanged when merely editing wording.
Before new research, read the previous brief and compare its underlying events with today's evidence. Prioritize genuine developments since that version, clearly identify unchanged background, and do not claim a change or cause without evidence. If no material new information exists, say so concisely. This comparison uses the current saved brief; no new archive is needed.
Use natural spoken Hebrew, short complete sentences and explicit logical connections. The speech adapter handles company names, acronyms and percentages; keep website text in readable standard financial Hebrew. Do not sacrifice factual nuance to reach a word quota.

## Daily headline
The title is displayed as the headline inside the morning summary card. Write one clear, specific Hebrew headline of about 6–12 words conveying that day's main economic story. It must be supported by the researched body, not imply causation or certainty absent from sources, and should change only when the underlying story changes. Avoid generic prefixes like סקירת הבוקר, clickbait, redundant dates and repeated numbers. Never invent an event merely to create a new headline.


## Client conversation substance
Frame each point around a real client concern prompted by the researched event, not a topic label or a generic portfolio checklist. The insight should be ready-to-say Hebrew, explaining the event's investment significance with one clear mechanism. Add a distinct investor implication rather than repeating the insight or the main brief. Examples of reasoning structure: election outcome vs ability to implement fiscal policy; earnings growth vs expectations already priced; energy costs feeding inflation/rate expectations and bond sensitivity. These are examples, not fixed daily topics. Select only what current evidence supports; avoid repeated canned sentences. Label possible effects as conditional, do not promise a market direction, and do not present upcoming earnings as published results. Keep to 2–3 focused sentences per point where possible; no compulsory meeting question or personal investment instruction.


## Main market narrative
The main brief must form a coherent economic narrative, not list disconnected headline-plus-generic-impact pairs. Identify one central tension, explain its distinct local and global channels, and separate dated background from genuine current developments. Recheck fresh sources each run, including political/security/fiscal developments that have concrete economic relevance. Distinguish discussion of potential sanctions or policy proposals from actually enacted measures. Clearly separate observed market reaction from conditional transmission mechanisms; do not invent current price reactions. The main narrative supplies evidence and context; client points translate selected implications into conversation without repeating whole paragraphs. Keep the total concise and avoid duplicating quote tables.


## Opening market picture (required)
Start the opening section's first paragraph with one concise factual sentence describing the actual latest completed trading session: equities in Israel and the US, oil and US bond yields when verified and relevant. Include the reference session date and use qualitative directions rather than repeating index levels or percentage tables. Distinguish bond yields from bond prices; do not describe Israeli or corporate bonds if those data are unavailable. Verify against current market_data.json and dated sources; never assume today's trading calendar or retimestamp prior closes. Then place "פרשנות:" before one separate sentence explaining the main economic significance, not claiming an unverified causal explanation. This opening is shown once in the top summary, under תמונת מצב and המשמעות להשקעות; avoid repeating it in the expanded text. If morning_summary is provided, event must hold the market picture and impact its interpretation; preserve the actual dates of both facts and sources. Keep the events-ahead sentence in a separate section.


## Upcoming large-company earnings calendar
Refresh earnings_calendar.json on every research run and update the matching HTML payload between <!-- EARNINGS_SNAPSHOT_START --> and <!-- EARNINGS_SNAPSHOT_END --> in the latest index.html. Preserve <script id="earnings-snapshot" type="application/json"> and escape '<' as JSON \\u003c. Publish these updates in the same atomic commit as the researched brief. The existing file is a schema example, not an evergreen schedule. The main article and the calendar must agree.

Research official investor-relations announcements for material large companies reporting within 14 days, prioritizing index-heavy technology names and other relevant major firms. Include only dates confirmed by a primary company source; never infer dates from last year, and omit companies whose dates are unconfirmed. Do not list already-published results as upcoming. Separate the date/time of earnings publication from the investor conference call. If exact release time or before/after-market status is not explicitly stated, say it is not specified. A call time alone does not prove the release time. Convert exact announced time zones with America/Los_Angeles, America/New_York or America/Chicago into Asia/Jerusalem using date-aware DST, never a constant offset. If calendar dates differ across zones, include the correct local date in the description.

Schema: {checked_at:actual aware ISO timestamp of verification,items:[{company,ticker,report_date:YYYY-MM-DD,release_window:short Hebrew description,release_at:optional aware ISO timestamp only if exact verified,call_at:optional aware ISO timestamp,expires_at:aware ISO timestamp,confirmed:true,source_url:exact primary HTTPS source}]}. expires_at is release_at when known, otherwise call_at as a conservative end to upcoming status; omit events without a defensible expiry. Keep at most eight major events. Do not add unsupported EPS/revenue estimates. Do not refresh checked_at without checking sources. The UI hides expired events and schedules unverified for more than three days. Update the calendar even on days with no earnings, with an honest empty items list after research.


## User-approved professional client style (supersedes conversational examples)
The user prefers concise professional talking points like an investment-adviser brief, not simplified dialogue scripts in quotation marks. Each title identifies an investment issue and each short paragraph connects evidence to valuation, cash flow, concentration, duration, currency exposure, fiscal policy or risk premium as relevant to that day's actual events. Keep insight and client_impact complementary; they are rendered together as ONE paragraph without repeated "what to say" / "portfolio meaning" labels. Avoid rhetorical filler and generic meeting questions. Target roughly 40–60 Hebrew words per point, no more than three. Numerical claims require dated verified data. If quoting a yield, identify its date, market, maturity and currency; distinguish yield from price movement and do not promise realized return. The current equities/bonds/Israel topics are examples, not daily quotas. Preserve conditional wording for potential effects and avoid individual investment instructions.


## Brief Europe, Asia and oil coverage (required)
Include a concise section "אירופה, אסיה ונפט · בקצרה" with three short paragraphs, one for Europe, one for Asia and one for oil. Keep each to one or two sentences, dated to its actual market session. Cover a broad European benchmark and major Asian markets such as Japan/Hong Kong when their data are verifiable; differentiate mixed regional directions rather than treating all Asia as one market. Distinguish Brent from WTI and futures from spot. If numbers already appear elsewhere, prefer a qualitative summary unless a different benchmark adds value. Cite dated reliable sources per region, and attribute reported drivers instead of inventing causation. No live-market claims outside verified trading hours. Explicitly state if a region's current data cannot be verified. Keep the article to at most five sections so the near-term-events section remains visible; shorten other paragraphs to preserve the concise overall brief. Up to three links per section are supported. Do not alter the recently approved professional client-point style.
