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
`Today` (default) · `Events` · `News` · `Explore` · `Community`

("Do" was the first label and was rejected. "Explore" covers the mix better
than a pure place-word like "Places", since the section holds guides and
plans as well as outings and dining.)

## Visual decisions (chosen from live A/B on the real build)
| | |
|---|---|
| Today block | **Plain** — the same card as everything else. An earlier version filled it solid dark; it carried so much of the page's weight that every accent read as loud. |
| Palette | **Azure** — chosen over citrus / meadow / lagoon / coral / violet / ink+sun. |
| Ground | **Pure white**, with cards carrying a faint azure tint. |
| Cards | Separate by **tone, not outline** — no border, no shadow. |
| Blue intensity | **Subtle** — chosen over medium and strong. The card tint is a ~6% wash off white, so the page reads as white and the blue lives in the accent, not the surfaces. |

Two colour bugs found by the user and fixed:

- The brand mark was a **dark navy square with a blue letter**, so the one
  place the brand colour should be unmistakable read as dark. Now a solid blue
  square with a white letter.
- `--cool` (secondary links, e.g. "All news") was still **teal `#0e7490`** from
  an earlier candidate palette, so two different hues were doing the same job.
  Moved into the blue family in both light and dark.

Two traps found while implementing, both worth remembering:

1. **Do not get tinted cards by setting `--rule` to match `--surface`.** That is
   how the throwaway demo did it, and it works for cards — but `--rule` also
   draws the buttons, the search field, the filter pills, the footer and the
   tab bar, so it silently strips the border off every control on the site.
   The border is removed on `.card` / `.today-block` specifically instead.
2. **`--chrome` exists so the top bar and tab bar stay pure white** while
   content cards tint. Without it the chrome picks up the tint and the page
   is no longer white where the user actually looks first.

Dark mode is hand-built, not inverted: the page is deep navy and the cards are
*lighter* than the page, so the tint relationship flips rather than reversing
into something muddy.

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
