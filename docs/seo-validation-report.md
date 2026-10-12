# Yonsei STL SEO validation report

Audit date: 12 October 2026.

This report compares the repository with fresh responses from `https://yonsei-stl.github.io/`. At the start of the audit, the deployed HTML, `robots.txt`, `sitemap.xml`, `llms.txt`, and publication index were byte-for-byte identical to the repository. Two small HTML cleanups made after that comparison are in the working tree and are not on the public site until the next push.

Passing these checks improves technical discoverability. It does not guarantee indexing, ranking, or citation by Google, Google Scholar, Bing, ChatGPT, Gemini, Claude, Copilot, or Perplexity.

## A. Executive summary

The four published project URLs, the publication index, and the root lab redirect are all live. `robots.txt` and `sitemap.xml` match the repository and do not block search crawlers. Canonical URLs, Highwire citation tags, and `ScholarlyArticle` JSON-LD are present and consistent with the Crossref records used for the four papers. Draft project directories are not in the sitemap or publication index.

What was still wrong:

- SpectraDiff and RM-MLLM contained empty `<sup></sup>` markers, so affiliation numbering was blank.
- SpectraDiff contained a commented reference to a missing `static/images/stl.ico`.

What was fixed in the working tree, and is not yet deployed:

- Removed the empty superscripts.
- Removed the dead icon comment.
- Extended `scripts/build_discovery.py` so `python scripts/build_discovery.py --check` also rejects duplicate registry paths, empty superscripts, and missing local CSS, JavaScript, and image files.

What remains unresolved:

- No `citation_pdf_url` is set, because no legally hostable PDF is in the repository.
- SpectraDiff BibTeX still uses the publisher string `Nalcakan Yagiz`. The visible name is `Yagiz Nalcakan`.
- RM-MLLM’s Crossref issue date is December 2026, while the version-of-record license starts in August 2026.
- Pix2Next’s visible abstract says the FID score improved by 34.81%. The publisher abstract does not use that figure.
- The arXiv RASMD author list differs from the journal and from the project page.
- Quantitative results on SpectraDiff and RM-MLLM are images, not HTML tables.
- `https://stl.yonsei.ac.kr/` does not link to the publication index.
- Google Search Console and Bing Webmaster Tools were not submitted from this audit.

## B. Technical validation

| Component | Status | Evidence | Recommended action |
| --- | --- | --- | --- |
| Published project URLs | PASS | `GET` returned 200 for `/RASMD/`, `/Pix2Next/`, `/SpectraDiff/`, `/RM-MLLM/`, and `/publications/`. Last-Modified `Mon, 12 Oct 2026 03:07:35 GMT`. | None for the URLs. Push the superscript cleanup when ready. |
| Root redirect | PASS | `https://yonsei-stl.github.io/` returned HTTP 200, not a 301. The body is a zero-delay meta refresh, a script assignment, and a link, all to `https://stl.yonsei.ac.kr/`. No redirect loop. | Keep this behavior. HTTP clients that ignore meta refresh stay on the stub page. |
| Directory slash canonicalization | PASS | `GET /RASMD` returned `301` to `https://yonsei-stl.github.io/RASMD/`, then 200. | Keep canonical tags on the trailing-slash URLs. |
| Case-sensitive paths | PASS | `GET /rasmd/` returned 404. | Do not rename directories. |
| `robots.txt` | PASS | Live file matches the repository, 671 bytes, `Content-Type: text/plain`. `User-agent: *` allows `/` and disallows only `/IVIFormer_draft/` and `/MWSC_draft/`. Sitemap URL is `https://yonsei-stl.github.io/sitemap.xml`. | Training access is allowed. Change it only by an explicit lab decision. |
| Search versus training crawlers | WARNING | There is no per-bot block. `OAI-SearchBot`, `Googlebot`, `Claude-SearchBot`, `bingbot`, and `PerplexityBot` are allowed because `*` is allowed. `GPTBot`, `ClaudeBot`, and `Google-Extended` are also allowed. `ChatGPT-User` may ignore `robots.txt`. Blocking `Google-Extended` would not remove the site from Google Search. | Leave the current allow policy unless the lab wants to opt out of training crawlers. |
| Accidental `noindex` on published pages | PASS | Published pages have no `noindex`. Sampled responses had no `X-Robots-Tag`. | None. |
| Draft exposure | WARNING | `/IVIFormer_draft/` and `/MWSC_draft/` return 404. Their `index_old.html` files return 200, include `noindex`, and are disallowed in `robots.txt`. They are still publicly downloadable and are copies of an unrelated 3D Gaussian Splatting page. | Approve deletion of those template copies if they should not remain public. |
| `sitemap.xml` | PASS | Live XML matches the repository and parses. It lists exactly `/publications/`, `/RM-MLLM/`, `/RASMD/`, `/SpectraDiff/`, and `/Pix2Next/`. No draft paths. No `lastmod`, which avoids unreliable dates. URLs match the canonical tags. | Add a paper by editing `data/publications.json` and running `python scripts/build_discovery.py`. |
| `llms.txt` | PASS | Live file matches the repository. It links the publication index, the four project pages, DOIs, arXiv, code, and the RASMD dataset. It does not list drafts. | Do not add `llms-full.txt`. `GET /llms-full.txt` is 404. Google Search ignores `llms.txt`. |
| Publication index | PASS | The page is static HTML. It lists the four published projects, uses one `h1` and one `h2` per paper, and links each title to its original URL. Paper, arXiv, code, and dataset buttons match the project pages. Draft names are absent. Each project page links to `/publications/`. | Link this URL from `stl.yonsei.ac.kr`. That site is outside this repository and currently contains neither `github.io` nor `publications`. |
| Canonical URLs | PASS | Each paper canonical is `https://yonsei-stl.github.io/{Project}/`. The index canonical is `https://yonsei-stl.github.io/publications/`. None point at a DOI. | None. |
| Open Graph and preview images | PASS | `og:image` URLs returned 200: RASMD `teaser.png`, Pix2Next `detailed_architecture.png`, SpectraDiff `method.png`, RM-MLLM `rm_teaser.png`. SpectraDiff does not use the unused 3DGS teaser. | None. |
| JSON-LD syntax | PASS | `python scripts/build_discovery.py --check` parses one `ScholarlyArticle` object per paper and one `CollectionPage` on the index. | Do not treat this as a Google rich-result guarantee. |
| Local assets | PASS | Relative CSS, JavaScript, and images referenced by the published pages exist. The commented SpectraDiff favicon pointed at a missing `stl.ico` and was removed. | None. |
| External publication links | WARNING | Elsevier DOI URLs for RASMD and SpectraDiff resolved with HTTP 200. RM-MLLM’s DOI returned 200. MDPI and ScienceDirect HTML returned 403 to this client, which is bot blocking rather than a removed page. The RASMD detection-v2 zip URL returned 401 because the Hugging Face dataset is gated. The dataset landing page returned 200. | Keep the current links. Do not replace a 403 or 401 with a guessed URL. |
| Lab-site link | FAIL | `https://stl.yonsei.ac.kr/` does not link to `https://yonsei-stl.github.io/publications/`. | Add that link on the lab site. This repository cannot make that edit. |
| Search Console and Bing | NOT VERIFIED | No webmaster account was available. | After the next push, submit `https://yonsei-stl.github.io/sitemap.xml` in both tools. |
| Desktop and mobile layout | NOT VERIFIED | No browser viewport was available. The pages set `viewport`, use Bulma, and include a `max-width: 768px` title and slider rule. The publication index stacks to one column below 700px. | Check the four project pages and `/publications/` on a phone after deploy. |
| Automated regression check | PASS | `.github/workflows/seo-check.yml` runs `python scripts/build_discovery.py --check` on pull requests and pushes to `main`. The check passed after this audit. | Keep using that command before adding a paper. It does not test the live domain. |

## C. Paper-specific findings

Metadata below was checked against Crossref and against the deployed HTML, which matched the repository at the start of the audit. `citation_pdf_url` is intentionally absent on every page. Google Scholar’s inclusion guide asks that a PDF tagged this way live in the same directory as the HTML. No such PDF is in the repository, and the Elsevier publisher PDFs for RASMD and SpectraDiff are not open-access files to commit.

| Paper | Authors and order | Venue and date | DOI | Canonical, citation tags, JSON-LD | PDF tag | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RASMD | Youngwan Jin; Michal Kovac; Yagiz Nalcakan; Incheol Park; Sanghyeop Yeo; Hyeongjin Ju; Shiho Kim | Information Fusion, volume 128, article 103872, 2026/04 | `10.1016/j.inffus.2025.103872` | PASS. Matches visible HTML. | Omitted | PASS, with one version note |
| Pix2Next | Youngwan Jin; Incheol Park; Hanbin Song; Hyeongjin Ju; Yagiz Nalcakan; Shiho Kim | Technologies, volume 13, issue 4, article 154, 2025/04/11 | `10.3390/technologies13040154` | PASS. Incheol Park links to `https://stl.yonsei.ac.kr/`. Yagiz Nalcakan links to `https://ynalcakan.github.io/`. | Omitted. CC BY 4.0 would allow a later same-directory PDF. | NEEDS MANUAL VERIFICATION for the 34.81% FID sentence |
| SpectraDiff | Incheol Park; Youngwan Jin; Yagiz Nalcakan; Hyeongjin Ju; Sanghyeop Yeo; Shiho Kim | Computer Vision and Image Understanding, volume 266, article 104709, 2026/03 | `10.1016/j.cviu.2026.104709` | PASS for the visible author order, including Sanghyeop Yeo. BibTeX still says `Nalcakan Yagiz`, which is how Crossref stores the name. | Omitted. No arXiv PDF was found. | NEEDS MANUAL VERIFICATION for the BibTeX name order |
| RM-MLLM | Hyeongjin Ju; Sanghyeop Yeo; Incheol Park; Youngwan Jin; Yagiz Nalcakan; Shiho Kim | Results in Engineering, volume 32, article 112317, citation date 2026/12 | `10.1016/j.rineng.2026.112317` | PASS. Paper button is the DOI. Code and Data buttons are absent. | Omitted. The version of record is CC BY-NC-ND 4.0. | NEEDS MANUAL VERIFICATION for the printed date and for code or data URLs |

### RASMD

The teaser caption on the deployed page says `RASMD`, not `RAMSD`.

The journal author list, the project page, the page BibTeX, and the Hugging Face dataset citation block match. The dataset card at `https://huggingface.co/datasets/STL-Yonsei/RASMD` cites the same seven authors and DOI `10.1016/j.inffus.2025.103872`.

The arXiv record `https://arxiv.org/abs/2504.07603` is a different version. Its current author line is Youngwan Jin, Michal Kovac, Yagiz Nalcakan, Hyeongjin Ju, Hanbin Song, Sanghyeop Yeo, and Shiho Kim. It includes Hanbin Song and does not include Incheol Park. That is a preprint-versus-journal difference, not a dataset-card error. The project page correctly follows the journal. No author change was made.

Affiliation superscripts `1` and `2` are real and were left in place.

### Pix2Next

The incorrect Incheol Park link is fixed on the deployed page. It points to `https://stl.yonsei.ac.kr/`. The only `ynalcakan.github.io` link is Yagiz Nalcakan’s.

The visible abstract’s “FID score by 34.81%” is not in the publisher abstract, which says the FID score is highly improved and also names IDD-AW. The sentence was left unchanged.

### SpectraDiff

The deployed page does not contain the 3D Gaussian Splatting method paragraph. The replacement paragraph describes the RSOA module, semantic segmentation, residual blocks, and the Spectral Attention Block, which are in the abstract and in `static/images/method.png`.

Empty `<sup></sup>` tags were present on all six authors and on the single affiliation line. They did not encode a real affiliation number, because every author is shown at Seamless Trans-X Lab. Those tags were removed locally. The author names and order were not changed.

The commented favicon link to a missing `stl.ico` was removed.

### RM-MLLM

The deployed Paper button points to `https://doi.org/10.1016/j.rineng.2026.112317`, which returned HTTP 200. There is no Code or Data button and no self-link in place of those resources. No code or dataset URL was invented.

The author names have no superscripts. The affiliation line had an empty `<sup></sup>`, which was removed locally. All six authors remain affiliated with Seamless Trans-X Lab.

The citation date `2026/12` follows the Crossref issue date. The Crossref record was created on 7 August 2026 and the version-of-record license starts on 3 August 2026. Confirm the date printed on the PDF before changing `citation_publication_date`.

## D. Files modified

| File | Why |
| --- | --- |
| `SpectraDiff/index.html` | Removed seven empty `<sup></sup>` tags and a commented link to a missing favicon. Author names, DOI, and the method paragraph were not changed. |
| `RM-MLLM/index.html` | Removed one empty `<sup></sup>` from the affiliation line. The DOI link and author list were not changed. |
| `scripts/build_discovery.py` | The existing checker now rejects duplicate project paths, empty superscripts, and missing local CSS, JavaScript, and image files, including assets used by the publication index. |
| `docs/seo-validation-report.md` | This report. |

No project directory was renamed. `index.html` at the repository root was not edited. `robots.txt`, `sitemap.xml`, `llms.txt`, and `publications/index.html` were not edited.

## E. URL preservation

| URL | HTTP result on 12 October 2026 | Unchanged |
| --- | --- | --- |
| `https://yonsei-stl.github.io/` | 200, meta refresh to `https://stl.yonsei.ac.kr/` | Yes |
| `https://yonsei-stl.github.io/RASMD/` | 200 | Yes |
| `https://yonsei-stl.github.io/Pix2Next/` | 200 | Yes |
| `https://yonsei-stl.github.io/SpectraDiff/` | 200 | Yes |
| `https://yonsei-stl.github.io/RM-MLLM/` | 200 | Yes |
| `https://yonsei-stl.github.io/publications/` | 200 | Yes. This path was added by the SEO work and does not replace a paper URL. |

`/RASMD` without a slash returns 301 to `/RASMD/`. `/RASMD/index.html` remains another 200 URL for the same file. Canonical tags use the trailing-slash form.

The superscript cleanup does not change any public path. It is not on the live site until it is pushed.

## F. Manual actions required

1. Push this working tree when the superscript cleanup should go live. This audit did not commit or deploy it.
2. Verify the GitHub Pages property in Google Search Console and submit `https://yonsei-stl.github.io/sitemap.xml`.
3. Add the site in Bing Webmaster Tools and submit the same sitemap.
4. Watch indexing afterward. A valid sitemap does not by itself create index entries.
5. On `https://stl.yonsei.ac.kr/`, add a link to `https://yonsei-stl.github.io/publications/`. That website is not in this repository.
6. Confirm these scholarly points before editing them:
   - SpectraDiff PDF title page: `Yagiz Nalcakan` versus Crossref’s `Nalcakan Yagiz`.
   - RM-MLLM PDF: December 2026 issue date versus August 2026 online date.
   - Pix2Next PDF: whether “34.81%” is in the published paper.
   - RM-MLLM code and dataset URLs, if they exist.
   - Whether to host the CC BY Pix2Next PDF, and separately whether CC BY-NC-ND allows hosting the RM-MLLM PDF.
7. Decide whether to delete `IVIFormer_draft/` and `MWSC_draft/` from the publishing branch.
8. Decide whether training crawlers should stay allowed.

## G. Remaining risks

- The root URL is an HTTP 200 stub. Crawlers that do not treat an instant meta refresh as a redirect may index “Redirecting to STL Lab Website” instead of following it. The publication index is a separate, crawlable URL.
- `robots.txt` cannot force a crawler to index a page, and it cannot reliably stop user-triggered fetchers.
- Draft `index_old.html` files remain public even though they are disallowed and marked `noindex`.
- Publisher HTML returned 403 to automated requests. The DOI resolver worked for the Elsevier papers. A 403 here is not evidence that the link was removed.
- The Hugging Face detection-v2 zip is gated. Visitors must accept the dataset conditions.
- Important numeric comparisons for SpectraDiff and RM-MLLM are in figures. Their captions say which metrics or tasks are shown and that the numbers are in the figure. No HTML table was added, because transcribing those numbers from an image would risk inventing or misreading results.
- Before/after sliders are pointer-driven. Both images remain in the HTML, with alt text, so the comparison is still readable without the script.
- Color is used to mark best and second-best SpectraDiff cells inside an image. The caption states the green and yellow meanings, but the values themselves are not text.
- `ScholarlyArticle` JSON-LD is valid structured data. It is not a promise of a Google rich result.
- `llms.txt` is an optional map. It does not control ChatGPT, Gemini, Claude, or Perplexity indexing.
- Local `python scripts/build_discovery.py --check` does not prove the live site. This audit proved the live site by comparing response bytes. After the superscript edit, SpectraDiff and RM-MLLM in the working tree no longer match production.

## H. Final acceptance checklist

| Requirement | Result |
| --- | --- |
| Existing public research URLs remain operational and unchanged | PASS |
| `robots.txt` is valid and matches the intended allow policy | PASS |
| Sitemap is valid and lists every published project plus the index | PASS |
| Published pages use the correct canonical URLs | PASS |
| Academic metadata matches the authoritative records used here | PASS, except the three manual items in section F |
| JSON-LD parses and matches those records and the visible pages | PASS |
| Publication index lists the four published projects and no drafts | PASS |
| Research text, headings, and image alt text are in the initial HTML | PASS |
| Figures that hold the main numeric tables also have an HTML transcription | FAIL. Left as images on purpose. |
| No confirmed critical internal link error remains | PASS |
| Future papers can be checked with the existing GitHub Action and local command | PASS |
| Search Console, Bing, and lab-site link | NOT VERIFIED / not done |
| Mobile visual layout | NOT VERIFIED |
