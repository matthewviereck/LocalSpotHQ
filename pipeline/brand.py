"""
The site's name, in one place.

Until 2026-11-19 the name was written three ways: "LocalSpot" (the root's
WebSite data, every visible header), "LocalSpot HQ" (the town pages' WebSite
data, og:site_name on the town apps, guide and plan publisher) and "LocalSpot
<Town>" (og:site_name on guides, plans, cases and camps). Google picks a
site's display name from exactly these tags and wants them to agree, and it
had not learned the name at all: a search for "localspothq" was rewritten to
"local spot" and answered with restaurants. One name everywhere, the
variants as alternateName, and the Facebook Page as sameAs, so Google can
tie the site to the name people see on Facebook.
"""

SITE_NAME = 'LocalSpot'
SITE_URL = 'https://www.localspothq.com/'
ALTERNATE_NAMES = ['LocalSpot HQ', 'LocalSpot Phoenixville', 'LocalSpot West Chester', 'localspothq.com']
SAME_AS = ['https://www.facebook.com/LocalSpotPhoenixville']


def organization():
    """schema.org Organization for author/publisher fields."""
    return {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL}


def website():
    """schema.org WebSite for the root page (the one Google reads the site name from)."""
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "alternateName": ALTERNATE_NAMES,
        "url": SITE_URL,
        "publisher": {**organization(), "sameAs": SAME_AS},
    }
