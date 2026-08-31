# LocalSpot redesign (branch `redesign-2026`)

## Goal
Turn LocalSpot from a **filterable directory** into a **daily habit**: a page
a resident opens each morning to see what is happening in their town today.

## Decisions (agreed 2026-08-31)
| Question | Decision |
|---|---|
| Events | **Keep all data and every `/events/<slug>/` page.** Replace the filter-browser UI with a daily digest. |
| Dining | **Cut as a top-level tab.** Data retained, demoted into "Do". |
| Community | **Moderated board** — residents submit, Matthew approves. No accounts. |
| Local facts | Weather + civic + history/landmarks + schools & sports (all four). |

## Hard constraints
1. **URLs must not change.** 176 pages earn impressions; the 8/29 CTR work
   verified all 241 slugs byte-identical on purpose. Preserve:
   - `/<area>/` · `/<area>/events/<slug>/` · `/<area>/guides/<slug>/`
   - `/<area>/this-weekend/` · `/<area>/events.ics` · `/<area>/sitemap.xml`
2. **Pipeline contract** (`pipeline/inject.py`) — the template must keep every
   `{{PLACEHOLDER}}` and every `const <name>Data = [...];` injection point.
3. **postprocess.py contract** — `#landing-page` and `#main-app` marker classes,
   and a global `renderContent()`.
4. Structured data (Event JSON-LD + `offers`) must survive — it is what makes
   the pages eligible for rich results.

## Architecture change
The app used **Tailwind CDN → prebuilt `assets/app.css`**, while event pages,
guide pages and the weekend page each carried their own ad-hoc inline CSS. So
the site had four unrelated looks.

Replaced with one hand-authored design system, `assets/localspot.css`, shared by
all four generators. No build step, no CDN, no JIT compile in the browser.

## Nav
`Today` (default) · `Events` · `News` · `Do` · `Community`

## Verification
- Both areas build clean (`python pipeline/run.py --all`).
- **URL preservation confirmed empirically**: the new Phoenixville sitemap was
  diffed against the live one — 132 URLs each, zero added, zero removed.
- CSS href depth checked from every generated page type (app, event, guides
  index, guide page, this-weekend) — all resolve.
- Desktop breakpoint measured: 1080px centered container, desktop nav on,
  tab bar off, two-column grid, no horizontal overflow.

## Still to do
- Create `community_token.txt` above the docroot on Hostinger, or moderation
  stays disabled (503 by design).
- The guide hero images are Unsplash placeholders and one 404s.
- `assets/app.css` (old Tailwind build) is now unused; delete once master is
  merged, not before — the legacy PHP builder still references it.
