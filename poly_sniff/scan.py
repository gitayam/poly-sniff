"""Scan subcommand — discover and analyze markets by topic tag."""

import argparse
from tabulate import tabulate

from . import config, output
from .search.polymarket import _search_via_gamma_tags
from .sniff import sniff_market


def run_scan(args: argparse.Namespace) -> None:
    """Scan topic tags or specific markets for behavioral anomalies."""
    markets_to_scan = []

    if args.tags:
        tag_list = [t.strip() for t in args.tags.split(',') if t.strip()]
        print(f"\nDiscovering active markets for tags: {', '.join(tag_list)}")

        candidates = _search_via_gamma_tags(tag_list, limit=30)

        # Filter: active only, above min volume
        for c in candidates:
            if c.get('closed') is True or c.get('active') is not True:
                continue
            vol = c.get('volume')
            if vol is not None:
                try:
                    if float(vol) < args.min_volume:
                        continue
                except (ValueError, TypeError):
                    pass
            markets_to_scan.append({
                'slug': c['slug'],
                'title': c.get('title', ''),
            })

        print(f"  found        : {len(candidates)} events")
        print(f"  active       : {len(markets_to_scan)} (above ${args.min_volume:,.0f} volume)")

    elif args.markets:
        slug_list = [s.strip() for s in args.markets.split(',') if s.strip()]
        markets_to_scan = [{'slug': s, 'title': ''} for s in slug_list]
        print(f"\nScanning {len(markets_to_scan)} specified market(s)")

    else:
        print("Error: Provide --tags or --markets to scan.")
        return

    if not markets_to_scan:
        print("\n  No active markets found matching criteria.")
        return

    # Cap at max_markets
    if len(markets_to_scan) > args.max_markets:
        print(f"  capping at   : {args.max_markets} markets (use --max-markets to change)")
        markets_to_scan = markets_to_scan[:args.max_markets]

    # Batch sniff
    print(f"\nAnalyzing {len(markets_to_scan)} market(s) for insider patterns...\n")
    results = []

    for i, m in enumerate(markets_to_scan, 1):
        slug = m['slug']
        print(f"  [{i}/{len(markets_to_scan)}] {slug}...")
        sr = sniff_market(
            slug,
            limit=args.limit,
            min_directional=args.min_directional,
            min_dominant=args.min_dominant,
            max_conviction=args.max_conviction,
            min_late_volume=args.min_late_volume,
            verbose=True,
        )
        if sr:
            sr['title'] = m.get('title', '') or sr.get('slug', '')
            results.append(sr)

    if not results:
        print("\n  No market data could be retrieved.")
        return

    # Sort by anomaly score descending
    results.sort(key=lambda r: r['signal']['anomaly_score'], reverse=True)

    # Summary table
    anomaly_count = sum(1 for r in results if r['signal']['signal_level'] != 'QUIET')

    print(f"\n{'='*80}")
    print(f"  Scan complete: {anomaly_count} of {len(results)} markets with anomalies")
    print(f"{'='*80}\n")

    table_data = []
    for i, r in enumerate(results, 1):
        table_data.append([
            i,
            f"{r['flagged_count']}/{r['holder_count']}",
            r['signal']['signal_level'],
            r['title'][:50],
            r['slug'][:35],
        ])

    print(tabulate(
        table_data,
        headers=['#', 'Flagged', 'Signal', 'Market', 'Slug'],
        tablefmt='simple',
    ))

    # Detail sections for markets with anomalies
    for r in results:
        if r['flagged_count'] > 0:
            print(f"\n{'─'*80}")
            print(f"  {r['slug']} — {r['flagged_count']} flagged user(s)  "
                  f"[Signal: {r['signal']['signal_level']}]")
            print(f"{'─'*80}")
            output.print_table(r['flagged_df'])
