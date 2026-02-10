#!/usr/bin/env python3
"""
Email Alias Generator

Generates unique email aliases that all route to a single Gmail inbox.
Uses two Gmail tricks:
  1. Dot trick: Gmail ignores dots in the local part, so
     j.asonleejfl and jason.le.ejfl both deliver to jasonleejfl@gmail.com
  2. Plus trick: anything after '+' is ignored, so
     jasonleejfl+xyz@gmail.com delivers to jasonleejfl@gmail.com

All generated emails deliver to: jason.lee.jfl@gmail.com
"""

import random
import json
import csv
import sys
from itertools import combinations
from datetime import datetime

BASE_EMAIL = "jason.lee.jfl@gmail.com"
# Gmail strips dots, so the canonical form is without dots
LOCAL_PART = BASE_EMAIL.split("@")[0].replace(".", "")  # "jasonleejfl"
DOMAIN = "gmail.com"


def get_all_dot_variants(local: str) -> list[str]:
    """
    Generate all possible dot placements for a Gmail local part.
    Dots can go between any two characters. For a string of length N,
    there are N-1 possible dot positions, giving 2^(N-1) variants.
    """
    if len(local) < 2:
        return [local]

    # Positions where dots can be inserted (between each pair of chars)
    positions = list(range(1, len(local)))
    variants = []

    # Every subset of positions gives a unique variant
    for r in range(len(positions) + 1):
        for combo in combinations(positions, r):
            parts = []
            prev = 0
            for pos in combo:
                parts.append(local[prev:pos])
                prev = pos
            parts.append(local[prev:])
            variants.append(".".join(parts))

    return variants


def generate_emails(count: int = 50) -> list[dict]:
    """Generate a list of unique email aliases using dot variants."""
    all_variants = get_all_dot_variants(LOCAL_PART)
    random.shuffle(all_variants)

    # If they need more than dot variants alone, add +tag combos
    if count > len(all_variants):
        print(f"Note: {len(all_variants)} dot variants available. "
              f"Using +suffix for the remaining {count - len(all_variants)}.")

    emails = []
    used = set()

    # Phase 1: pure dot variants (look most natural — no '+' visible)
    for v in all_variants:
        if len(emails) >= count:
            break
        addr = f"{v}@{DOMAIN}"
        if addr not in used:
            used.add(addr)
            emails.append({
                "alias": addr,
                "routes_to": BASE_EMAIL,
                "style": "dot",
                "created": datetime.now().isoformat(),
            })

    # Phase 2: if we still need more, add +suffix variants on top of dot variants
    suffixes = list(range(1, 10000))
    random.shuffle(suffixes)
    si = 0
    while len(emails) < count:
        base_variant = random.choice(all_variants)
        addr = f"{base_variant}+{suffixes[si]}@{DOMAIN}"
        si += 1
        if addr not in used:
            used.add(addr)
            emails.append({
                "alias": addr,
                "routes_to": BASE_EMAIL,
                "style": "dot+suffix",
                "created": datetime.now().isoformat(),
            })

    return emails


def save_emails(emails: list[dict], fmt: str = "all"):
    """Save generated emails to files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt in ("all", "json"):
        path = f"emails_{timestamp}.json"
        with open(path, "w") as f:
            json.dump(emails, f, indent=2)
        print(f"Saved JSON  -> {path}")

    if fmt in ("all", "csv"):
        path = f"emails_{timestamp}.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["alias", "routes_to", "style", "created"])
            writer.writeheader()
            writer.writerows(emails)
        print(f"Saved CSV   -> {path}")

    if fmt in ("all", "txt"):
        path = f"emails_{timestamp}.txt"
        with open(path, "w") as f:
            for e in emails:
                f.write(e["alias"] + "\n")
        print(f"Saved TXT   -> {path}")


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    fmt = sys.argv[2] if len(sys.argv) > 2 else "all"

    total_dot_variants = 2 ** (len(LOCAL_PART) - 1)
    print(f"Base: {BASE_EMAIL}  (canonical: {LOCAL_PART}@{DOMAIN})")
    print(f"Total possible dot variants: {total_dot_variants:,}")
    print(f"Generating {count} aliases...\n")

    emails = generate_emails(count)

    print(f"{'#':<4} {'Alias':<45} {'Style'}")
    print("-" * 65)
    for i, e in enumerate(emails, 1):
        print(f"{i:<4} {e['alias']:<45} {e['style']}")

    print()
    save_emails(emails, fmt)
    print(f"\nAll {count} aliases route to: {BASE_EMAIL}")


if __name__ == "__main__":
    main()
