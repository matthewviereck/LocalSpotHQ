"""
Geographic routing for LocalSpot areas.

Every event source (scrapers, recurring, discovery) writes lat/lng under
venue_info.location, so an event's town is decided by coordinates rather than
by parsing the venue string. That matters: discovery labels venues things like
"Eagleview Town Center, Exton (near Phoenixville)", and substring matching on
that lands an Exton event in the Phoenixville feed.

Each area config carries a `towns` roster. An event belongs to the area whose
roster contains its nearest town; events with no town inside `radius_miles`
are dropped as out-of-region.
"""

import math

# Rough conversion at SE Pennsylvania's latitude. Equirectangular is plenty
# accurate over the ~30 miles that separate these towns.
_MILES_PER_DEG_LAT = 69.0


def distance_miles(lat1, lng1, lat2, lng2):
    """Approximate great-circle distance in miles."""
    mid_lat = math.radians((lat1 + lat2) / 2)
    dx = (lng2 - lng1) * math.cos(mid_lat) * _MILES_PER_DEG_LAT
    dy = (lat2 - lat1) * _MILES_PER_DEG_LAT
    return math.hypot(dx, dy)


def event_coords(event):
    """Pull (lat, lng) off an event, or None when the source omitted them."""
    location = (event.get('venue_info') or {}).get('location') or {}
    lat, lng = location.get('lat'), location.get('lng')
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
        return float(lat), float(lng)
    return None


def geo_config(area_config):
    """Return (towns, radius_miles, tagline_count) for an area."""
    towns = area_config.get('towns') or []
    settings = area_config.get('geo') or {}
    return (
        towns,
        float(settings.get('radius_miles', 6)),
        int(settings.get('tagline_towns', 5)),
    )


def nearest_town(lat, lng, towns, radius_miles):
    """Closest town within radius_miles, or None."""
    best_name, best_dist = None, None
    for town in towns:
        dist = distance_miles(lat, lng, town['lat'], town['lng'])
        if best_dist is None or dist < best_dist:
            best_name, best_dist = town['name'], dist
    if best_dist is not None and best_dist <= radius_miles:
        return best_name
    return None


def route_events(events, area_config):
    """
    Tag each event with its town and drop those outside the area's roster.

    Returns (kept, dropped). Events without coordinates are kept and left
    untagged rather than silently discarded — a source that stops emitting
    lat/lng should degrade to the old behavior, not empty the feed.
    """
    towns, radius, _ = geo_config(area_config)
    if not towns:
        return list(events), []

    kept, dropped = [], []
    for event in events:
        coords = event_coords(event)
        if coords is None:
            kept.append(event)
            continue
        town = nearest_town(coords[0], coords[1], towns, radius)
        if town is None:
            dropped.append((event, None))
            continue
        event['town'] = town
        kept.append(event)
    return kept, dropped


def route_area_events(events, area_config, verbose=True):
    """route_events plus a build-log summary of what was dropped and why."""
    kept, dropped = route_events(events, area_config)
    if verbose and dropped:
        print(f"   Dropped {len(dropped)} events outside the "
              f"{area_config.get('name', 'area')} roster:")
        for event, _ in dropped[:8]:
            venue = (event.get('venue_info') or {}).get('name', '?')
            print(f"     - {str(event.get('title', '?'))[:48]:48} @ {venue[:36]}")
        if len(dropped) > 8:
            print(f"     ... and {len(dropped) - 8} more")
    return kept


def town_counts(events):
    """Event count per town, most events first."""
    counts = {}
    for event in events:
        town = event.get('town')
        if town:
            counts[town] = counts.get(town, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def derive_tagline(events, area_config):
    """
    Build the header tagline from the towns that actually have events.

    Falls back to the config's static `tagline` when routing produced nothing,
    so a bad build never renders an empty header.
    """
    towns, _, tagline_count = geo_config(area_config)
    if not towns:
        return area_config.get('tagline', '')

    # The area's own town leads regardless of count; the rest follow by volume.
    anchor = area_config.get('name', '')
    ranked = [name for name, _ in town_counts(events)]
    ordered = ([anchor] if anchor in ranked else []) + [t for t in ranked if t != anchor]

    if not ordered:
        return area_config.get('tagline', '')
    return ' • '.join(ordered[:tagline_count])
