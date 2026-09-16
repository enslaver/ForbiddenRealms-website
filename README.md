# Forbidden Realms — website

Static marketing site for the game. No build step, no framework, no dependencies beyond two Google Fonts.

```
index.html          landing page
press.html          press kit (fact sheet, descriptions, logo + screenshot downloads)
assets/css/style.css
assets/js/main.js   nav, scroll reveal, gallery lightbox, sign-up form
assets/img/         logo, emblem, favicons, OG image, hero background
assets/img/gallery/ 1920x1080 screenshots + 800x450 thumbs
assets/video/       per-class idle loops (webm + mp4 + jpg poster), faded behind the class columns
tools/encode_class_loops.py  turns editor captures into those loops
```

## Preview locally

```
python3 -m http.server 8080
# open http://localhost:8080
```

## Deploy (Netlify, free tier)

`netlify.toml` is included (publish dir, www → apex redirect, cache/security headers).

First time:

```
npx netlify-cli login                 # opens browser, authorise once
npx netlify-cli deploy --prod --dir . # creates the site, prints the *.netlify.app URL
```

Every later update: run the same `deploy --prod --dir .` from this directory.

Custom domain: Netlify site → Domain management → add `forbidden-realms.com` and `www`.
At the registrar (No-IP) set:

| Host | Type  | Value |
|------|-------|-------|
| `@`  | A     | `75.2.60.5` |
| `www`| CNAME | `<your-site>.netlify.app` |

Netlify issues the Let's Encrypt cert automatically once DNS resolves (minutes to an hour).

Alternative with no bandwidth cap: Cloudflare Pages (`npx wrangler pages deploy .`), but the apex
domain then requires moving nameservers to Cloudflare, which No-IP doesn't need for Netlify.

## Things to fill in before launch

- **Mailing list**: set `FOLLOW_ENDPOINT` at the top of `assets/js/main.js` to a Buttondown / Mailchimp / Formspree endpoint that accepts `POST {"email": ...}`. Until then the form shows a holding message.
- **Press contact**: `press.html` uses a placeholder `press@forbidden-realms.com (set up the mailbox)` address.
- **Canonical URL / OG image**: the `og:image` meta tags use relative paths; switch to absolute URLs once the domain is known.
- **Store / social links**: none are wired yet. Add them to the footer and the hero CTA when Steam / Discord / YouTube pages exist.
- **Fonts**: Cormorant Garamond and Cormorant SC load from Google Fonts. Self-host them if you want zero third-party requests.

## Class idle loops: prompt to redo after the re-mesh

Paste this into a Claude Code session in the game repo once the new class meshes are in:

> Re-capture the four class idle loops for the website with transparent backgrounds. Ask the
> background Director session for an editor window and take the editor-mutation lock. Load
> /Game/ForbiddenRealms/_Scratch/L_186_ClassCapture, confirm the placed FR_Class_* actors now use
> the new meshes, run place_helpers() from Scripts/editor/capture_class_idle.py, start PIE, and run
> run(out='/tmp/fr_class_capture', alpha=True). Check one a_NNN.exr converts to a clean matte
> (ffmpeg -i a_060.exr -vf format=gbrapf32le,extractplanes=a,negate a.png) before the full run;
> if the HDR alpha is unusable, fall back to alpha=False and keep the screen-blend path. Re-frame
> CAM_DIST / CAM_Z if the new proportions need it. Stop PIE, reload the map with dirty_policy
> discard, release the lock. Then in ../ForbiddenRealms-website run
> python3 tools/encode_class_loops.py /tmp/fr_class_capture, drop the classes__loop--onblack class
> from the four <video> tags in index.html, switch their poster attribute from .jpg to .png, and
> render-check the classes section at 1440 and 640 wide with headless Chrome. Keep the loops
> faint (opacity 0.26, desaturated) and do not touch anything else on the page.


Captured in the editor with `Scripts/editor/capture_class_idle.py` (game repo, CL 970): load
`/Game/ForbiddenRealms/_Scratch/L_186_ClassCapture`, run `place_helpers()`, start PIE, run
`run(out='/tmp/fr_class_capture')`. Then here: `python3 tools/encode_class_loops.py /tmp/fr_class_capture`.
The encoder finds the cleanest loop point, crops to the figure, crushes blacks, and writes
`assets/video/<class>.{webm,mp4,jpg}`. Re-run both steps when the class meshes are replaced.

## Asset provenance

- Logo/emblem cut from `Content/Splash/Splash.png` in the game project (Epic/Unreal badges cropped, background keyed to alpha).
- Screenshots are 2026-09-14 PIE captures of `UC_Catacomb` from `.kilo/captures/1213-qa-texstreaming-flip-verify/` plus one sanctum-arch capture from `0834-clue-chain`. Mild gamma lift applied to the darkest three.
- Copy is drawn from `STORY.md` / `WORLDDESIGN.md` and deliberately stops short of the Act 3 reveal.

[![Netlify Status](https://api.netlify.com/api/v1/badges/ff4f2bb0-b5c3-48a7-b36b-8db298236a7e/deploy-status?branch=dev)](https://app.netlify.com/projects/forbidden-realms/deploys)

