#!/usr/bin/env python3
"""
Email Alias Generator

Generates realistic, unique email addresses that all look like different
people. Each address is completely untraceable to the real recipient.

Routing options (pick one when you set up):
  1. Custom domain with catch-all: all emails to *@yourdomain.com forward
     to your real inbox. This is the best option.
  2. Email forwarding service (SimpleLogin, addy.io, Firefox Relay, etc.):
     create aliases that forward to your real address.

All generated emails deliver to: jason.lee.jfl@gmail.com
"""

import random
import json
import csv
import sys
from datetime import datetime

ROUTE_TO = "jason.lee.jfl@gmail.com"

# --- Name pools for generating realistic-looking emails ---

FIRST_NAMES = [
    "emma", "liam", "olivia", "noah", "ava", "ethan", "sophia", "mason",
    "mia", "logan", "isabella", "lucas", "charlotte", "aiden", "amelia",
    "james", "harper", "benjamin", "evelyn", "elijah", "abigail", "alex",
    "daniel", "emily", "michael", "ella", "henry", "scarlett", "sebastian",
    "grace", "jack", "lily", "owen", "chloe", "sam", "zoey", "wyatt",
    "riley", "julian", "nora", "leo", "hannah", "caleb", "addison", "ryan",
    "aubrey", "nathan", "stella", "adrian", "maya", "thomas", "claire",
    "miles", "violet", "david", "hazel", "connor", "aurora", "cole", "luna",
    "max", "penny", "kai", "ivy", "hunter", "willow", "eli", "brooke",
    "tyler", "piper", "grant", "sienna", "derek", "taylor", "marcus",
    "paige", "carlos", "jenna", "trevor", "kira", "blake", "megan",
    "drew", "tessa", "reid", "brynn", "shane", "kylie", "brock", "dana",
    "craig", "nina", "ross", "vera", "kent", "fiona", "dale", "iris",
]

LAST_NAMES = [
    "smith", "johnson", "brown", "williams", "jones", "garcia", "miller",
    "davis", "rodriguez", "martinez", "anderson", "taylor", "thomas",
    "jackson", "white", "harris", "clark", "lewis", "robinson", "walker",
    "hall", "allen", "young", "king", "wright", "scott", "green", "baker",
    "adams", "nelson", "carter", "mitchell", "perez", "roberts", "turner",
    "phillips", "campbell", "parker", "evans", "edwards", "collins",
    "stewart", "morris", "murphy", "cook", "rogers", "morgan", "peterson",
    "cooper", "reed", "bailey", "bell", "howard", "ward", "torres", "gray",
    "watson", "brooks", "price", "bennett", "wood", "barnes", "ross",
    "henderson", "coleman", "jenkins", "perry", "powell", "long", "rivera",
    "ford", "bishop", "grant", "dunn", "meyer", "holt", "marsh", "webb",
    "cole", "hunt", "stone", "beck", "sharp", "wade", "lane", "cross",
    "quinn", "bloom", "norton", "chang", "silva", "pham", "chen", "ngo",
]



def _pattern_firstlast(first: str, last: str, num: str) -> str:
    """emma.johnson42"""
    return f"{first}.{last}{num}"

def _pattern_firstinitiallast(first: str, last: str, num: str) -> str:
    """ejohnson42"""
    return f"{first[0]}{last}{num}"

def _pattern_firstlastinitial(first: str, last: str, num: str) -> str:
    """emmaj42"""
    return f"{first}{last[0]}{num}"

def _pattern_lastfirst(first: str, last: str, num: str) -> str:
    """johnson.emma42"""
    return f"{last}.{first}{num}"

def _pattern_firstunderscorelast(first: str, last: str, num: str) -> str:
    """emma_johnson42"""
    return f"{first}_{last}{num}"

def _pattern_first_num(first: str, last: str, num: str) -> str:
    """emma4287"""
    big_num = str(random.randint(100, 9999))
    return f"{first}{big_num}"

def _pattern_lastinitialfirst(first: str, last: str, num: str) -> str:
    """jemma42"""
    return f"{last[0]}{first}{num}"

def _pattern_initialdotlast(first: str, last: str, num: str) -> str:
    """e.johnson42"""
    return f"{first[0]}.{last}{num}"

def _pattern_firstdashlast(first: str, last: str, num: str) -> str:
    """emma-johnson42"""
    return f"{first}-{last}{num}"

def _pattern_twoinitiallast(first: str, last: str, num: str) -> str:
    """eajohnson42  (uses random middle initial)"""
    mid = random.choice("abcdefghijklmnopqrstuvwxyz")
    return f"{first[0]}{mid}{last}{num}"


PATTERNS = [
    _pattern_firstlast,
    _pattern_firstinitiallast,
    _pattern_firstlastinitial,
    _pattern_lastfirst,
    _pattern_firstunderscorelast,
    _pattern_first_num,
    _pattern_lastinitialfirst,
    _pattern_initialdotlast,
    _pattern_firstdashlast,
    _pattern_twoinitiallast,
]


def generate_local_part() -> str:
    """Generate a single realistic-looking email local part."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    # ~40% chance of no number, otherwise 1-2 digit suffix
    num = "" if random.random() < 0.4 else str(random.randint(1, 99))
    pattern = random.choice(PATTERNS)
    return pattern(first, last, num)


def generate_emails(count: int = 50, domain: str = "example.com") -> list[dict]:
    """Generate a list of unique realistic email addresses on your domain."""
    emails = []
    seen = set()

    while len(emails) < count:
        local = generate_local_part()
        addr = f"{local}@{domain}"
        if addr in seen:
            continue
        seen.add(addr)
        emails.append({
            "email": addr,
            "routes_to": ROUTE_TO,
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
            writer = csv.DictWriter(f, fieldnames=["email", "routes_to", "created"])
            writer.writeheader()
            writer.writerows(emails)
        print(f"Saved CSV   -> {path}")

    if fmt in ("all", "txt"):
        path = f"emails_{timestamp}.txt"
        with open(path, "w") as f:
            for e in emails:
                f.write(e["email"] + "\n")
        print(f"Saved TXT   -> {path}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 email_generator.py <your-domain.com> [count] [format]")
        print()
        print("  your-domain.com  Your catch-all domain (REQUIRED)")
        print("  count            Number of emails to generate (default: 50)")
        print("  format           Output format: all, json, csv, txt (default: all)")
        print()
        print("Example: python3 email_generator.py mydomain.com 100 txt")
        print()
        print("Setup: Configure catch-all forwarding on your domain so that")
        print("       *@your-domain.com forwards to your real inbox.")
        print("       Cloudflare Email Routing does this for free.")
        sys.exit(1)

    domain = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    fmt = sys.argv[3] if len(sys.argv) > 3 else "all"

    print(f"Domain: {domain}  (catch-all -> {ROUTE_TO})")
    print(f"Generating {count} unique addresses...\n")

    emails = generate_emails(count, domain)

    print(f"{'#':<5} {'Email'}")
    print("-" * 50)
    for i, e in enumerate(emails, 1):
        print(f"{i:<5} {e['email']}")

    print()
    save_emails(emails, fmt)
    print(f"\nDone. {count} addresses generated, all routing to {ROUTE_TO}.")


if __name__ == "__main__":
    main()
