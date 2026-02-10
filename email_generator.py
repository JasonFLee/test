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

# Common email providers to mix in for realism
DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com",
    "icloud.com", "aol.com", "mail.com", "zoho.com", "yandex.com",
    "fastmail.com", "tutanota.com", "gmx.com", "inbox.com", "live.com",
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


def generate_email() -> str:
    """Generate a single realistic-looking email address."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    # ~40% chance of no number, otherwise 1-2 digit suffix
    if random.random() < 0.4:
        num = ""
    else:
        num = str(random.randint(1, 99))
    domain = random.choice(DOMAINS)
    pattern = random.choice(PATTERNS)
    local = pattern(first, last, num)
    return f"{local}@{domain}"


def generate_emails(count: int = 50, custom_domain: str = None) -> list[dict]:
    """Generate a list of unique realistic email addresses."""
    emails = []
    seen = set()

    while len(emails) < count:
        addr = generate_email()
        # If using a custom catch-all domain, swap the domain
        if custom_domain:
            local = addr.split("@")[0]
            addr = f"{local}@{custom_domain}"
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
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    fmt = sys.argv[2] if len(sys.argv) > 2 else "all"
    # Optional: pass your catch-all domain as 3rd arg
    custom_domain = sys.argv[3] if len(sys.argv) > 3 else None

    if custom_domain:
        print(f"Using catch-all domain: {custom_domain}")
    print(f"All emails route to: {ROUTE_TO}")
    print(f"Generating {count} unique addresses...\n")

    emails = generate_emails(count, custom_domain)

    print(f"{'#':<5} {'Email'}")
    print("-" * 50)
    for i, e in enumerate(emails, 1):
        print(f"{i:<5} {e['email']}")

    print()
    save_emails(emails, fmt)
    print(f"\nDone. {count} addresses generated.")
    if not custom_domain:
        print("\nIMPORTANT: These are real-looking addresses on public domains.")
        print("To actually receive mail, you need one of:")
        print("  1. A catch-all domain: python3 email_generator.py 50 all yourdomain.com")
        print("  2. A forwarding service (SimpleLogin, addy.io, Firefox Relay)")
        print("     to create aliases that forward to your inbox.")


if __name__ == "__main__":
    main()
