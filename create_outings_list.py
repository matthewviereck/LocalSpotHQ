import json

def create_outings_list(output_file='outings_curated.json'):
    """
    Create a curated list of real Phoenixville-area activities and attractions
    """
    
    print(">> Creating curated outings list...")
    
    outings = [
        # === OUTDOOR & NATURE ===
        {
            "title": "Schuylkill River Trail",
            "type": "Outdoor",
            "loc": "Phoenixville to Philadelphia",
            "desc": "75-mile paved trail perfect for biking, running, and walking along the scenic Schuylkill River",
            "vibes": ["Biking", "Running", "Scenic", "Family Friendly"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1541625602330-2277a4c46182?auto=format&fit=crop&w=600&q=80",
            "link": "https://schuylkillriver.org/schuylkill-river-trail/",
            "tags": ["outdoor", "biking", "running", "free"]
        },
        {
            "title": "French Creek State Park",
            "type": "Outdoor",
            "loc": "Near Phoenixville",
            "desc": "8,000+ acres of forests, lakes, wetlands with hiking, biking, fishing, and camping",
            "vibes": ["Hiking", "Camping", "Fishing", "Nature"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1511497584788-876760111969?auto=format&fit=crop&w=600&q=80",
            "link": "https://www.dcnr.pa.gov/StateParks/FindAPark/FrenchCreekStatePark/",
            "tags": ["outdoor", "hiking", "camping", "free"]
        },
        {
            "title": "Valley Forge National Historical Park",
            "type": "Outdoor",
            "loc": "10 minutes from Phoenixville",
            "desc": "Revolutionary War historic site with trails, bike paths, and educational programming",
            "vibes": ["History", "Hiking", "Biking", "Educational"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1464207687429-7505649dae38?auto=format&fit=crop&w=600&q=80",
            "link": "https://www.nps.gov/vafo/",
            "tags": ["outdoor", "history", "hiking", "free"]
        },
        {
            "title": "French Creek Heritage Trail",
            "type": "Outdoor",
            "loc": "Phoenixville",
            "desc": "4.2-mile wooded trail along French Creek with bridges, waterfalls, and bird watching",
            "vibes": ["Hiking", "Nature", "Scenic", "Bird Watching"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["outdoor", "hiking", "nature", "free"]
        },
        {
            "title": "Black Rock Sanctuary",
            "type": "Outdoor",
            "loc": "Near Phoenixville",
            "desc": "119 acres of wetlands, woodlands, and meadows - perfect for bird watching",
            "vibes": ["Bird Watching", "Nature", "Peaceful", "Wildlife"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1444464666168-49d633b86797?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["outdoor", "nature", "bird watching", "free"]
        },
        {
            "title": "Phoenixville SUP Paddle Board Rental",
            "type": "Water Sports",
            "loc": "Phoenixville",
            "desc": "Kayak and paddleboard rentals to explore the Schuylkill River",
            "vibes": ["Water Sports", "Kayaking", "Summer", "Adventure"],
            "price": "$$",
            "img": "https://images.unsplash.com/photo-1473496169904-658ba7c44d8a?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["outdoor", "water", "kayaking", "summer"]
        },
        
        # === ENTERTAINMENT & ACTIVITIES ===
        {
            "title": "FUN Dungeon - Brewcade & Billiards",
            "type": "Entertainment",
            "loc": "Phoenixville",
            "desc": "Medieval-themed arcade bar with 30+ classic games, pinball, pool table, and craft beer",
            "vibes": ["Arcade", "Bar", "Games", "Unique"],
            "price": "$",
            "img": "https://images.unsplash.com/photo-1511882150382-421056c89033?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["indoor", "games", "bar", "arcade"]
        },
        {
            "title": "Markie's Mini Golf",
            "type": "Entertainment",
            "loc": "Phoenixville",
            "desc": "26,000 sq ft mini golf course with 18 holes - all-you-can-play!",
            "vibes": ["Family Friendly", "Mini Golf", "Fun", "Outdoor"],
            "price": "$",
            "img": "https://images.unsplash.com/photo-1593346003146-5cc2e6e286ec?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["outdoor", "mini golf", "family", "fun"]
        },
        {
            "title": "SAGE! Escape Room",
            "type": "Entertainment",
            "loc": "Phoenixville",
            "desc": "Immersive escape room experiences with multiple themed rooms",
            "vibes": ["Escape Room", "Puzzles", "Team Building", "Indoor"],
            "price": "$$",
            "img": "https://images.unsplash.com/photo-1522069169874-c58ec4b76be5?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["indoor", "escape room", "puzzles", "groups"]
        },
        
        # === ARTS & CULTURE ===
        {
            "title": "The Spirited Artist",
            "type": "Arts",
            "loc": "Phoenixville",
            "desc": "Paint and sip studio - create art while enjoying wine or beer",
            "vibes": ["Art", "Wine", "Date Night", "Creative"],
            "price": "$$",
            "img": "https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["indoor", "art", "wine", "date night"]
        },
        {
            "title": "Diving Cat Studio Gallery",
            "type": "Arts",
            "loc": "Phoenixville",
            "desc": "Local art gallery featuring works from Chester County artists",
            "vibes": ["Art", "Gallery", "Local Artists", "Cultural"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1451847251646-8a6c0dd1510c?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["indoor", "art", "gallery", "free"]
        },
        {
            "title": "Franklin Commons Art Gallery",
            "type": "Arts",
            "loc": "Phoenixville",
            "desc": "Multi-use educational and events space featuring local and international artists",
            "vibes": ["Art", "Gallery", "Events", "Cultural"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1536924940846-227afb31e2a5?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["indoor", "art", "gallery", "free"]
        },
        {
            "title": "Phoenixville Public Library",
            "type": "Cultural",
            "loc": "Phoenixville",
            "desc": "Historic library with 65,000+ items, programs, and community events",
            "vibes": ["Books", "Educational", "Community", "Family Friendly"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["indoor", "library", "educational", "free"]
        },
        
        # === UNIQUE EXPERIENCES ===
        {
            "title": "Schuylkill River Greenways Visitor Center",
            "type": "Cultural",
            "loc": "Phoenixville",
            "desc": "Exhibits, maps, and videos about the National Heritage Area",
            "vibes": ["Educational", "History", "Nature", "Local"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1566127992631-137a642a90f4?auto=format&fit=crop&w=600&q=80",
            "link": "https://schuylkillriver.org",
            "tags": ["indoor", "educational", "history", "free"]
        },
        {
            "title": "Bridge Street Chocolates",
            "type": "Shopping",
            "loc": "Phoenixville",
            "desc": "Artisan candy & chocolate shop with handmade treats, truffles, and unique gifts. Closes at 7pm.",
            "vibes": ["Candy Shop", "Shopping", "Local", "Treats"],
            "price": "$",
            "img": "https://images.unsplash.com/photo-1511381939415-e44015466834?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["indoor", "shopping", "chocolate", "candy", "treats"]
        },
        {
            "title": "Downtown Phoenixville Shopping",
            "type": "Shopping",
            "loc": "Phoenixville",
            "desc": "Boutique shops, galleries, and locally-owned stores along Bridge & Main Streets",
            "vibes": ["Shopping", "Local", "Boutique", "Window Shopping"],
            "price": "Varies",
            "img": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["indoor", "shopping", "boutique", "local"]
        },
        
        # === NEARBY ATTRACTIONS ===
        {
            "title": "Arnold's Family Fun Center",
            "type": "Entertainment",
            "loc": "Oaks",
            "desc": "Go-karts, mini golf, arcade, batting cages, and more family fun",
            "vibes": ["Family Friendly", "Arcade", "Go-Karts", "Fun"],
            "price": "$$",
            "img": "https://images.unsplash.com/photo-1519961398423-48ebeffb3c3b?auto=format&fit=crop&w=600&q=80",
            "link": "https://arnoldsffc.com",
            "tags": ["outdoor", "family", "arcade", "go-karts"]
        },
        {
            "title": "Pickering Valley Golf Club",
            "type": "Recreation",
            "loc": "Near Phoenixville",
            "desc": "Beautiful 18-hole golf course with challenging holes and scenic views",
            "vibes": ["Golf", "Outdoor", "Scenic", "Sports"],
            "price": "$$$",
            "img": "https://images.unsplash.com/photo-1535131749006-b7f58c99034b?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["outdoor", "golf", "sports"]
        },
        {
            "title": "Bike Schuylkill - Free Bike Rentals",
            "type": "Recreation",
            "loc": "Along Schuylkill River Trail",
            "desc": "Free bike rentals to explore the Schuylkill River Trail",
            "vibes": ["Biking", "Free", "Outdoor", "Active"],
            "price": "Free",
            "img": "https://images.unsplash.com/photo-1571068316344-75bc76f77890?auto=format&fit=crop&w=600&q=80",
            "link": "",
            "tags": ["outdoor", "biking", "free", "trail"]
        }
    ]
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(outings, f, indent=2, ensure_ascii=False)
    
    print(f">> SUCCESS! Created {len(outings)} curated outings")
    print(f">> Saved to: {output_file}")
    
    # Summary by type
    types = {}
    for outing in outings:
        t = outing['type']
        types[t] = types.get(t, 0) + 1
    
    print(f"\n>> Summary by type:")
    for t, count in sorted(types.items()):
        print(f"   {t}: {count} activities")
    
    # Summary by price
    prices = {}
    for outing in outings:
        p = outing['price']
        prices[p] = prices.get(p, 0) + 1
    
    print(f"\n>> Summary by price:")
    for p, count in sorted(prices.items()):
        print(f"   {p}: {count} activities")
    
    return outings

if __name__ == "__main__":
    create_outings_list()
