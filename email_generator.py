#!/usr/bin/env python3
"""
Email Alias Generator

Generates unique email aliases that all route to a single Gmail inbox
using Gmail's '+' aliasing feature.

All generated emails deliver to: jason.lee.jfl@gmail.com
"""

import random
import string
import json
import csv
import sys
from datetime import datetime

BASE_EMAIL = "jason.lee.jfl@gmail.com"
LOCAL_PART, DOMAIN = BASE_EMAIL.split("@")

# Word pools for generating natural-looking aliases
ADJECTIVES = [
    "swift", "bold", "keen", "calm", "warm", "cool", "bright", "sharp",
    "quick", "smart", "fresh", "grand", "prime", "noble", "vivid", "lucid",
    "agile", "witty", "brave", "sleek", "crisp", "neat", "fair", "fine",
    "glad", "wise", "pure", "rare", "free", "true", "dark", "deep",
]

NOUNS = [
    "falcon", "cedar", "river", "atlas", "spark", "flint", "grove", "ridge",
    "arrow", "ember", "crane", "drift", "frost", "blade", "stone", "brook",
    "cliff", "trail", "storm", "coral", "north", "steel", "tiger", "maple",
    "orbit", "quest", "pixel", "nexus", "prism", "pulse", "sigma", "theta",
]

ACTIVITIES = [
    "hiker", "coder", "reader", "runner", "rider", "maker", "writer", "gamer",
    "baker", "diver", "pilot", "scout", "racer", "sailor", "builder", "dreamer",
]


def generate_alias_tag(style: str = "random") -> str:
    """Generate a unique alias tag to insert after the '+' in the email."""
    if style == "word":
        adj = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        num = random.randint(1, 999)
        return f"{adj}.{noun}{num}"

    elif style == "activity":
        activity = random.choice(ACTIVITIES)
        adj = random.choice(ADJECTIVES)
        num = random.randint(10, 99)
        return f"{activity}.{adj}{num}"

    elif style == "alphanumeric":
        letters = "".join(random.choices(string.ascii_lowercase, k=5))
        digits = "".join(random.choices(string.digits, k=3))
        return f"{letters}{digits}"

    elif style == "date":
        now = datetime.now()
        rand = "".join(random.choices(string.ascii_lowercase, k=4))
        return f"{now.strftime('%Y%m%d')}.{rand}"

    else:  # mixed random
        style = random.choice(["word", "activity", "alphanumeric", "date"])
        return generate_alias_tag(style)


def generate_emails(count: int = 50) -> list[dict]:
    """Generate a list of unique email aliases with metadata."""
    emails = []
    seen_tags = set()

    while len(emails) < count:
        tag = generate_alias_tag()
        if tag in seen_tags:
            continue
        seen_tags.add(tag)

        alias = f"{LOCAL_PART}+{tag}@{DOMAIN}"
        emails.append({
            "alias": alias,
            "routes_to": BASE_EMAIL,
            "tag": tag,
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
            writer = csv.DictWriter(f, fieldnames=["alias", "routes_to", "tag", "created"])
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

    print(f"Generating {count} email aliases routing to {BASE_EMAIL}\n")
    emails = generate_emails(count)

    print(f"{'#':<4} {'Alias':<55} {'Tag'}")
    print("-" * 80)
    for i, e in enumerate(emails, 1):
        print(f"{i:<4} {e['alias']:<55} {e['tag']}")

    print()
    save_emails(emails, fmt)
    print(f"\nAll {count} aliases route to: {BASE_EMAIL}")


if __name__ == "__main__":
    main()
