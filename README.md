# poly_sniff

> Hard fork of [agile-enigma/poly_sniff](https://github.com/agile-enigma/poly-sniff) — extended with claim-to-market search, AI-powered article analysis, and multi-source market discovery.

A CLI tool for [Polymarket](https://polymarket.com) prediction market intelligence. It does three things:

1. **Search** — Find relevant Polymarket markets from news articles or claim text, using AI claim extraction, entity-based tag search, and LLM relevance ranking. Optionally show confidence ratings and batch-sniff for insider patterns.
2. **Scan** — Survey topic areas for behavioral anomalies across multiple markets. On-demand early warning detection.
3. **Analyze** — Detect suspicious betting behavior by scraping transaction data, computing behavioral metrics, and flagging users whose trading patterns suggest insider knowledge.

## What's new in this fork

This fork extends the original insider detection tool into a broader Polymarket research toolkit:

- **`search` subcommand** — Given a URL or claim text, extracts verifiable claims via GPT, discovers matching Polymarket markets, and ranks them by relevance using LLM re-ranking.
- **AI-powered market discovery** — GPT generates bettor-oriented tag slugs and search phrases (e.g., "iran retaliation", "trade war escalation") for precise market matching. Falls back to entity extraction when no API key is set.
- **Paywall bypass** — Scrapes paywalled articles via archive.ph, Wayback Machine, Google AMP/webcache fallbacks with browser profile rotation.
- **Multi-source search** — AI tags → Gamma API, AI phrases → SearXNG, entity extraction → Gamma, keyword search → SearXNG. Each layer catches what the previous misses.
- **Three-tier ranking** — LLM re-ranking via researchtoolspy → AI semantic scoring via GPT → keyword matching fallback.
- **`scan` subcommand** — Discover markets by topic tag and batch-analyze for insider patterns. Surfaces anomalies across an entire topic area.
- **`--sniff` batch analysis** — Run insider detection across all matched active markets, not just the top one. Replaces the old `--analyze` flag.
- **`--confidence` ratings** — Show market prices as implied probabilities with behavioral signal strength (STRONG/MODERATE/QUIET).
- **Signal strength** — Per-market anomaly scoring based on flagged user counts, directional consistency, and late volume patterns.

## Installation

```bash
git clone https://github.com/irregularchat/poly-sniff.git
cd poly-sniff

python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
pip install -e .
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env:
#   RESEARCHTOOLS_URL=https://researchtools.net   (claim extraction + LLM ranking)
#   OPENAI_API_KEY=sk-...                         (optional: AI market discovery)
```

- **Required:** A [researchtoolspy](https://github.com/gitayam/researchtoolspy) instance for AI claim extraction and LLM ranking.
- **Optional:** An OpenAI API key enables AI-powered market discovery (GPT-generated tags + bettor-oriented search phrases). Without it, search falls back to entity extraction + keyword matching.

## Usage

### Search for markets

Find Polymarket markets related to a news article or claim:

```bash
# Search from a news article URL
poly_sniff search --url "https://www.reuters.com/world/israel-strikes-iran-oil"

# Search from a direct claim
poly_sniff search --claim "Will Iran retaliate against Israel?"

# Combine both — URL claims + explicit claim
poly_sniff search --url "https://example.com/article" --claim "tariffs on China"

# Sniff all matched active markets for insider patterns
poly_sniff search --url "https://example.com/article" --sniff

# Show confidence ratings (price + behavioral signal)
poly_sniff search --claim "Iran retaliates" --confidence

# Both: confidence + sniff all matches
poly_sniff search --url "https://example.com/article" --sniff --confidence
```

#### Search options

| Flag | Default | Description |
|------|---------|-------------|
| `--url`, `-u` | — | URL to extract claims from via AI |
| `--claim`, `-c` | — | Direct claim text to search for |
| `--sniff`, `-s` | — | Run insider analysis across all matched active markets |
| `--confidence` | — | Show price and behavioral signal columns |
| `--analyze`, `-a` | — | *(Deprecated)* Analyze top match only. Use `--sniff`. |
| `--top-n`, `-n` | `5` | Number of results to display |
| `--min-relevance` | `25` | Minimum relevance score (0-100) |

#### Example output

```
Extracting claims from URL: https://www.rt.com/news/...
  ai claims    : 10 (original, 1125 words)
  summary      : Iran has released a Lego-style video depicting retaliation...
  title  : Iran deploys Lego VIDEO in PR war against US
  claims : 15

Searching Polymarket for matching markets...
  ai tags      : 60 events from iran, israel, military, war, middle-east, us-military, sanctions, oil
  ai phrases   : +1 via search (iran retaliation, us strikes iran, israel iran conflict, middle east escalation)
  entity tags  : +1 from lego, iranian, minab, trump
  candidates   : 63

Ranking 25 candidates by relevance...

  #  Rel  Status    Market                                         Slug                                  Reasoning
  1   70  Resolved  Iran response to Israel by Friday?              iran-response-to-israel-by-wednesda   This market is related...
  2   70  Resolved  Iran response to Israel by April 19?            iran-response-to-israel-by-april-19   Similar to the previous...
  3   40  Resolved  U.S. military action against Iran by April 15   us-military-action-against-iran-by-   This market is related...
```

### Scan for anomalies

Survey a topic area for unusual betting patterns:

```bash
# Scan all active Iran-related markets
poly_sniff scan --tags iran

# Scan multiple topics
poly_sniff scan --tags iran,tariffs,china

# Scan specific markets by slug
poly_sniff scan --markets "iran-response-by-apr-15,china-tariffs-2025"

# Widen the net — more markets, looser thresholds
poly_sniff scan --tags iran --max-markets 20 --min-directional 0.75
```

#### Scan options

| Flag | Default | Description |
|------|---------|-------------|
| `--tags`, `-t` | — | Comma-separated Polymarket tag slugs |
| `--markets`, `-m` | — | Comma-separated market slugs (skip discovery) |
| `--min-volume` | `10000` | Skip markets below this USDC volume |
| `--max-markets` | `10` | Maximum markets to analyze |
| `--limit` | `20` | Top position holders to scrape per market |
| Threshold flags | Same as analyze | `--min-directional`, `--min-dominant`, etc. |

#### Signal strength levels

| Level | Meaning |
|-------|---------|
| **STRONG** | 2+ flagged users, or 1 flagged with very high late volume (>=70%) |
| **MODERATE** | 1 flagged user, or elevated aggregate directional consistency + late volume |
| **QUIET** | No anomalies detected |

### Analyze a market

Detect suspicious insider trading patterns on a specific market:

```bash
# Basic analysis — prints flagged users to terminal
poly_sniff analyze will-x-happen-by-date

# Legacy syntax also works (slug found after /event/ in market URL)
poly_sniff will-x-happen-by-date

# Scrape top 50 No-side holders, flag only those who bet on the winning side
poly_sniff analyze will-x-happen-by-date --position-side No --limit 50 --resolved-outcome No

# Loosen thresholds for a wider net
poly_sniff analyze will-x-happen-by-date --min-directional 0.75 --min-dominant 0.80

# Export everything for further analysis
poly_sniff analyze will-x-happen-by-date --export-all
```

The market slug is found after `/event/` in the Polymarket URL, e.g. `polymarket.com/event/will-x-happen-by-date`.

#### Analyze options

| Flag | Default | Description |
|------|---------|-------------|
| `--resolved-outcome` | — | `Yes` or `No`. Only flag users whose dominant side matches the winning outcome. |
| `--position-side` | `Yes` | Which side's top position holders to scrape. |
| `--limit` | `20` | Number of top position holders to scrape. |
| `--late-window` | `24` | Hours before resolution that count as "late" trading. |
| `--min-directional` | `0.85` | Minimum Directional Consistency to flag. |
| `--min-dominant` | `0.90` | Minimum Dominant Side Ratio to flag. |
| `--max-conviction` | `0` | Maximum Price Conviction Score to flag. |
| `--min-late-volume` | `0.50` | Minimum Late Volume Ratio to flag. |
| `--export-profiles` | — | Export user profiles to `profiles.xlsx`. |
| `--export-transactions` | — | Export transaction data to `transactions.xlsx`. |
| `--export-scaffold` | — | Export hourly scaffold to `scaffold.xlsx`. |
| `--export-flagged` | — | Export flagged users with all metrics to `flagged_users.xlsx`. |
| `--export-all` | — | Export all four xlsx files. |

## How search works

The search pipeline has five stages:

1. **Claim extraction** — The article URL is sent to the researchtoolspy `/api/tools/extract-claims` endpoint, which scrapes the content (with paywall bypass via archive.ph/Wayback/AMP), then uses GPT to extract 5-15 verifiable claims with categories, confidence scores, and suggested prediction market questions.

2. **AI market discovery** *(primary, requires OPENAI_API_KEY)* — GPT analyzes the claims and generates two things: (a) 5-8 Polymarket tag slugs including tangential topics (e.g., `oil`, `sanctions` for an Iran article), and (b) 5-8 bettor-oriented search phrases that capture the specific nuance of the article (e.g., "iran retaliation", "us casualties iran" instead of just "iran"). Tags are searched via the Gamma API; phrases are searched via SearXNG.

3. **Entity extraction** *(fallback/supplement)* — Key entities (countries, people, organizations) are extracted from claims via regex and mapped to Polymarket tag slugs. Searches any tags not already covered by AI discovery.

4. **Ranking** — Three-tier fallback: (a) LLM re-ranking via researchtoolspy `/api/tools/claim-match` with full claim context, (b) AI semantic scoring via GPT if the LLM ranker is unavailable, (c) keyword matching as final fallback. Each scores relevance 0-100.

5. **Display** — Results filtered by relevance threshold, displayed with market status (Active/Resolved), optional price confidence, and optional insider signal strength.

## How insider detection works

poly_sniff pulls the top position holders for a market, retrieves their full transaction histories within that market, and runs four behavioral metrics against each user.

Users are flagged through a conjunctive filter — all four conditions must be satisfied simultaneously. A user who passes only two or three criteria is not flagged. The core idea: an insider doesn't hedge, doesn't follow the crowd, and tends to act late.

### Detection metrics

| Metric | Formula | What it measures |
|--------|---------|-----------------|
| **Directional consistency** | `abs(sum(netPosition)) / sum(abs(netPosition))` | Whether all trades point the same direction. Score of 1.0 = purely unidirectional. |
| **Dominant side ratio** | Fraction of USDC on dominant side | Capital concentration. >0.90 means nearly all capital committed one way. |
| **Price conviction score** | USDC-weighted avg of `(price - 0.50)` | Contrarian pricing. Negative = buying before market moves their way. |
| **Late volume ratio** | Fraction of USDC in final hours | Timing. Insiders often act close to resolution when they confirm info. |

All thresholds are configurable via CLI flags. Defaults live in `config.py`.

When `--resolved-outcome` is provided, an additional filter is applied: only users whose dominant side matches the winning outcome are flagged (bullish for Yes, bearish for No). When omitted, users are flagged in both directions, which is useful for pre-resolution analysis.

## Architecture

```
poly_sniff/
├── __main__.py          # CLI entry point (analyze + search + scan subcommands)
├── config.py            # Thresholds and defaults
├── sniff.py             # Shared sniff pipeline (single-market insider analysis)
├── scan.py              # Scan subcommand (tag-based anomaly detection)
├── output.py            # Flagging logic and table/xlsx output
├── scaffold.py          # Hourly time-series grid builder
├── data/
│   ├── loader.py        # Parse API responses into DataFrames
│   ├── preprocessing.py # Merge profiles, compute base columns
│   └── scraper.py       # Polymarket API scraping
├── metrics/
│   ├── activity.py      # Trade count and volume metrics
│   ├── conviction.py    # Price conviction scoring
│   ├── directional.py   # Directional consistency
│   ├── dominance.py     # Dominant side ratio
│   ├── signal.py        # Per-market signal strength (STRONG/MODERATE/QUIET)
│   └── timing.py        # Late volume ratio
└── search/
    ├── config.py         # Search-specific config (API URLs, limits)
    ├── ai_discovery.py   # GPT-powered tag + phrase generation, semantic scoring
    ├── claims.py         # Claim extraction (AI + metadata + URL fallbacks)
    ├── polymarket.py     # Market search (AI tags + Gamma + SearXNG + prices)
    └── ranker.py         # Three-tier relevance ranking (LLM → AI → keyword)
```

## Requirements

- Python 3.10+
- pandas, openpyxl, requests, tabulate, python-dotenv
- For search features: a [researchtoolspy](https://github.com/gitayam/researchtoolspy) instance
- Optional: `openai` package + `OPENAI_API_KEY` for AI-powered market discovery

## Mirrors

- GitHub: [irregularchat/poly-sniff](https://github.com/irregularchat/poly-sniff)
- GitLab: [irregulars/poly-sniff](https://git.irregularchat.com/irregulars/poly-sniff)
- Original: [agile-enigma/poly-sniff](https://github.com/agile-enigma/poly-sniff)

## Disclaimer

This tool is for research and analysis purposes. Flagged users are not necessarily engaged in insider trading — the metrics identify behavioral patterns that *warrant further investigation*, not proof of wrongdoing.

## License

MIT
