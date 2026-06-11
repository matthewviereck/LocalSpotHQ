<?php
/**
 * LOCALSPOT AUTO-UPDATE SCRIPT (PHP Server Version)
 * ==================================================
 * Runs automatically via Hostinger Cron Job.
 * Pulls latest code from GitHub, scrapes venues, and rebuilds the site.
 *
 * What it does:
 *   0. Git pull latest repo (data files, template, config)
 *   1. Generates recurring events (Farmers Market, First Friday, Blobfest)
 *   2. Scrapes Colonial Theatre for new shows
 *   3. Scrapes Expo Center for new events
 *   4. Scrapes Steel City Coffeehouse for live music
 *   5. Scrapes Molly Maguire's for pub events
 *   6. Merges all events
 *   7. Formats dates and filters past events
 *   8. Loads dining, outings, curated plans from repo JSON files
 *   9. Injects all data into HTML template
 *  10. Removes landing page, substitutes area placeholders
 *  11. Deploys to public_html/phoenixville/index.html
 *  12. Logs everything
 *
 * Setup:
 *   1. Clone repo:  cd ~ && git clone https://github.com/matthewviereck/LocalSpotHQ.git localspot
 *   2. Place this:   ~/localspot/deploy/auto_update.php (already in repo)
 *   3. Cron:         0 5 * * * /usr/bin/php /home/u277879645/localspot/deploy/auto_update.php >> /home/u277879645/localspot/logs/update.log 2>&1
 */

// ============================================================
// CONFIGURATION
// ============================================================

$HOME_DIR = '/home/u277879645';
$REPO_DIR = $HOME_DIR . '/localspot';
$PUBLIC_HTML = $HOME_DIR . '/domains/localspothq.com/public_html';
// Alternative path - uncomment if yours is different:
// $PUBLIC_HTML = $HOME_DIR . '/public_html';
$LOG_DIR = $REPO_DIR . '/logs';
$BACKUP_DIR = $REPO_DIR . '/backups';
$CACHE_DIR = $REPO_DIR . '/cache';

// Repo data paths
$DATA_DIR = $REPO_DIR . '/data/phoenixville';
$TEMPLATE_FILE = $REPO_DIR . '/templates/app_template.html';

// Area config
$AREA_NAME = 'Phoenixville';
$AREA_TAGLINE = 'Phoenixville • Oaks • Collegeville';
$META_TITLE = 'LocalSpot - Phoenixville Events, Dining & Activities';
$META_DESCRIPTION = 'Your guide to events, restaurants, and things to do in Phoenixville, Oaks, and Collegeville PA.';
$META_KEYWORDS = 'Phoenixville events, Phoenixville restaurants, things to do Phoenixville PA, Oaks events, Collegeville dining';
$OG_IMAGE = 'https://www.localspothq.com/images/og-image.png';
$CANONICAL_URL = 'https://www.localspothq.com/phoenixville/';

// ============================================================
// LOGGING
// ============================================================

function logMsg($message) {
    $timestamp = date('Y-m-d H:i:s');
    echo "[{$timestamp}] {$message}\n";
}

// ============================================================
// SHARED HELPERS: BANDSINTOWN & SQUARESPACE APIS
// ============================================================

function scrapeBandsintownVenue($venueId, $venueInfo, $fallbackUrl, $idPrefix, $defaultVibes) {
    // The authenticated v4 API now returns 403 for unregistered app_ids, so
    // scrape the public venue page's JSON-LD (schema.org MusicEvent) instead.
    $url = "https://www.bandsintown.com/v/{$venueId}";

    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\nAccept: text/html,application/xhtml+xml\r\n",
            'timeout' => 20
        ]
    ]);

    $html = @file_get_contents($url, false, $context);
    if ($html === false) {
        logMsg("  Bandsintown venue page unavailable for venue {$venueId}");
        return false;
    }

    if (!preg_match_all('#<script type="application/ld\+json">(.*?)</script>#s', $html, $matches)) {
        logMsg("  No JSON-LD found on Bandsintown page for venue {$venueId}");
        return [];
    }

    $events = [];
    $seen = [];
    foreach ($matches[1] as $block) {
        $data = json_decode($block, true);
        if (!$data) continue;
        $items = isset($data[0]) ? $data : [$data];
        foreach ($items as $item) {
            $types = (array)($item['@type'] ?? []);
            if (!in_array('MusicEvent', $types) && !in_array('Event', $types)) continue;

            $title = trim($item['name'] ?? '');
            if ($title === '') continue;
            // Bandsintown names events "Artist @ Venue" - keep just the artist
            $atPos = strrpos($title, ' @ ');
            if ($atPos !== false && $atPos > 0) {
                $title = trim(substr($title, 0, $atPos));
            }

            $startDate = $item['startDate'] ?? '';
            $dateText = $startDate ? date('F j, Y g:i A', strtotime($startDate)) : 'Check website';

            $key = $title . '|' . $dateText;
            if (isset($seen[$key])) continue;
            $seen[$key] = true;

            $img = $item['image'] ?? '';
            if (is_array($img)) {
                $img = $img[0] ?? '';
            }

            $events[] = [
                'id' => $idPrefix . abs(crc32($title . $dateText)),
                'type' => 'event',
                'title' => $title,
                'venue_info' => $venueInfo,
                'raw_date_string' => $dateText,
                'attributes' => [
                    'category' => 'Live Music',
                    'vibes' => $defaultVibes,
                    'price' => 'Check Link'
                ],
                'media' => ['image' => $img],
                'action_link' => $item['url'] ?? $fallbackUrl
            ];
            logMsg("  + {$title} ({$dateText})");
        }
    }

    return $events;
}

function scrapeSquarespaceJson($baseUrl, $venueInfo, $idPrefix, $defaultVibes) {
    $jsonUrl = $baseUrl . '?format=json';

    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\nAccept: application/json\r\n",
            'timeout' => 15
        ]
    ]);

    $json = @file_get_contents($jsonUrl, false, $context);
    if ($json === false) return false;

    $data = json_decode($json, true);
    if (!$data) return false;

    $items = $data['items'] ?? $data['upcoming'] ?? [];
    if (empty($items)) return false;

    $events = [];
    foreach ($items as $item) {
        $title = trim($item['title'] ?? '');
        if (!$title) continue;

        $startDate = $item['startDate'] ?? $item['publishOn'] ?? '';
        $dateText = $startDate ? date('F j, Y g:i A', strtotime($startDate / 1000)) : 'Check website';

        $fullUrl = $item['fullUrl'] ?? $item['urlId'] ?? '';
        if ($fullUrl && strpos($fullUrl, 'http') !== 0) {
            $fullUrl = 'https://www.steelcityphx.com' . $fullUrl;
        }

        $imgSrc = $item['assetUrl'] ?? '';

        $events[] = [
            'id' => $idPrefix . abs(crc32($title)),
            'type' => 'event',
            'title' => $title,
            'venue_info' => $venueInfo,
            'raw_date_string' => $dateText,
            'attributes' => [
                'category' => 'Live Music',
                'vibes' => $defaultVibes,
                'price' => 'Check Link'
            ],
            'media' => ['image' => $imgSrc],
            'action_link' => $fullUrl ?: $baseUrl
        ];
    }

    return $events;
}

// ============================================================
// STEP 0: GIT PULL LATEST CODE
// ============================================================

function syncFromGitHubRaw($repoDir) {
    // exec() is disabled on Hostinger shared hosting, so instead of git pull we
    // download the files this script depends on straight from GitHub raw.
    $rawBase = 'https://raw.githubusercontent.com/matthewviereck/LocalSpotHQ/master/';

    // path => minimum sane byte size (guards against deploying error pages)
    $files = [
        'templates/app_template.html'                   => 10000,
        'data/phoenixville/dining.json'                 => 100,
        'data/phoenixville/outings.json'                => 100,
        'data/phoenixville/plans.json'                  => 100,
        'data/phoenixville/scraped/discovered_events.json' => 2,
        'data/phoenixville/scraped/steel_city_events.json'  => 2,
        'data/phoenixville/scraped/molly_maguires_events.json' => 2,
        'deploy/auto_update.php'                        => 20000, // self-update, takes effect next run
    ];

    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: LocalSpotHQ/1.0\r\n",
            'timeout' => 20
        ]
    ]);

    $updated = 0;
    foreach ($files as $path => $minSize) {
        $content = @file_get_contents($rawBase . $path, false, $context);

        if ($content === false || strlen($content) < $minSize) {
            // 404s are expected for optional files (e.g. discovered_events.json)
            logMsg("  Skipped {$path} (unavailable or too small)");
            continue;
        }
        if (substr($path, -5) === '.json' && json_decode($content) === null) {
            logMsg("  Skipped {$path} (not valid JSON)");
            continue;
        }
        if (substr($path, -4) === '.php' && strpos($content, '<?php') !== 0) {
            logMsg("  Skipped {$path} (does not look like PHP)");
            continue;
        }

        $localPath = $repoDir . '/' . $path;
        if (file_exists($localPath) && md5_file($localPath) === md5($content)) {
            continue; // unchanged
        }

        $dir = dirname($localPath);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        if (@file_put_contents($localPath, $content) !== false) {
            logMsg("  Updated {$path} (" . strlen($content) . " bytes)");
            $updated++;
        } else {
            logMsg("  WARNING: could not write {$localPath}");
        }
    }

    logMsg($updated > 0 ? "  Synced {$updated} file(s) from GitHub" : "  All files already up to date");
    return true;
}

function dedupeEvents($events) {
    // Same event from two sources: match on normalized title + raw date.
    // Keep the richer copy (real image beats none, then a link beats none).
    $best = [];
    $order = [];
    foreach ($events as $event) {
        $title = preg_replace('/[^a-z0-9]/', '', strtolower($event['title'] ?? ''));
        $date = preg_replace('/[^a-z0-9]/', '', strtolower($event['raw_date_string'] ?? ''));
        $key = $title . '|' . $date;

        $img = $event['media']['image'] ?? '';
        $richness = [($img !== '' && strpos($img, 'placehold.co') === false), !empty($event['action_link'])];

        if (!isset($best[$key])) {
            $best[$key] = ['event' => $event, 'richness' => $richness];
            $order[] = $key;
        } elseif ($richness > $best[$key]['richness']) {
            $best[$key]['event'] = $event;
            $best[$key]['richness'] = $richness;
        }
    }
    $result = [];
    foreach ($order as $key) {
        $result[] = $best[$key]['event'];
    }
    return $result;
}

function gitPullLatest($repoDir) {
    logMsg("STEP 0: Pulling latest code from GitHub...");

    if (!is_dir($repoDir . '/.git')) {
        logMsg("  ERROR: Not a git repo at {$repoDir}");
        logMsg("  Run: cd ~ && git clone https://github.com/matthewviereck/LocalSpotHQ.git localspot");
        return false;
    }

    if (!function_exists('exec') || !is_callable('exec')) {
        logMsg("  NOTICE: exec() not available (shared hosting). Syncing from GitHub raw instead...");
        return syncFromGitHubRaw($repoDir);
    }

    $output = [];
    $returnCode = 0;
    exec("cd " . escapeshellarg($repoDir) . " && git pull origin master 2>&1", $output, $returnCode);

    $outputStr = implode("\n", $output);
    if ($returnCode !== 0) {
        logMsg("  WARNING: git pull failed (code {$returnCode}): {$outputStr}");
        logMsg("  Continuing with existing files...");
        return false;
    }

    logMsg("  {$outputStr}");
    return true;
}

// ============================================================
// STEP 1: GENERATE RECURRING EVENTS
// ============================================================

function generateRecurringEvents() {
    logMsg("STEP 1: Generating recurring events...");

    $events = [];

    // --- FARMERS MARKET (Every Saturday) ---
    $start = new DateTime('next Saturday');
    $end = new DateTime('+1 year');
    $saturdayCount = 0;

    $current = clone $start;
    while ($current <= $end) {
        $month = (int)$current->format('n');
        if ($month >= 5 && $month <= 11) {
            $timeInfo = '9am-12pm';
            $season = 'Main Season';
        } else {
            $timeInfo = '10am-12pm';
            $season = 'Winter Hours';
        }

        $events[] = [
            'id' => 'farmers_market_' . $current->format('Ymd'),
            'type' => 'event',
            'title' => 'Phoenixville Farmers Market',
            'venue_info' => [
                'name' => 'Under Gay Street Bridge',
                'location' => ['lat' => 40.1304, 'lng' => -75.5155]
            ],
            'raw_date_string' => $current->format('M d, Y'),
            'attributes' => [
                'category' => 'Farmers Market',
                'vibes' => ['Family Friendly', 'Outdoor', 'Local', $season],
                'price' => 'Free Entry',
                'time' => $timeInfo
            ],
            'media' => [
                'image' => 'https://images.unsplash.com/photo-1488459716781-31db52582fe9?auto=format&fit=crop&w=600&q=80'
            ],
            'action_link' => 'https://www.phoenixvillefarmersmarket.org'
        ];

        $saturdayCount++;
        $current->modify('+7 days');
    }
    logMsg("  Added {$saturdayCount} Farmers Market events");

    // --- FIRST FRIDAYS ---
    // Dynamically compute first Fridays for the next 12 months
    $ffCount = 0;
    $today = new DateTime('today');
    $ffEnd = (clone $today)->modify('+12 months');
    $ffCurrent = new DateTime('first Friday of this month');
    if ($ffCurrent < $today) {
        $ffCurrent = new DateTime('first Friday of next month');
    }

    while ($ffCurrent <= $ffEnd) {
        $month = (int)$ffCurrent->format('n');
        $monthName = $ffCurrent->format('F');
        $special = ($month == 12) ? 'Tree Lighting' : 'Street Festival';

        $events[] = [
            'id' => 'first_friday_' . $ffCurrent->format('Ymd'),
            'type' => 'event',
            'title' => "First Friday - {$monthName}",
            'venue_info' => [
                'name' => 'Downtown Phoenixville',
                'location' => ['lat' => 40.1304, 'lng' => -75.5155]
            ],
            'raw_date_string' => $ffCurrent->format('M d, Y'),
            'attributes' => [
                'category' => 'Community Event',
                'vibes' => ['Family Friendly', 'Live Music', 'Food & Drink', $special],
                'price' => 'Free',
                'time' => '5:30pm-8:30pm'
            ],
            'media' => [
                'image' => 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&w=600&q=80'
            ],
            'action_link' => 'http://www.phoenixvillefirst.org/first-fridays'
        ];
        $ffCount++;
        $ffCurrent->modify('first Friday of next month');
    }
    logMsg("  Added {$ffCount} First Friday events");

    // --- BLOBFEST (dynamically: 2nd Friday of July + Saturday + Sunday) ---
    $currentYear = (int)date('Y');
    for ($year = $currentYear; $year <= $currentYear + 1; $year++) {
        $julyFirst = new DateTime("{$year}-07-01");
        $blobFriday = new DateTime("second Friday of July {$year}");
        $blobSaturday = (clone $blobFriday)->modify('+1 day');
        $blobSunday = (clone $blobFriday)->modify('+2 days');

        $blobfestDays = [
            ['date' => $blobFriday, 'title' => 'Blobfest - Opening Night', 'time' => 'Evening'],
            ['date' => $blobSaturday, 'title' => 'Blobfest - Street Fair', 'time' => 'All Day'],
            ['date' => $blobSunday, 'title' => 'Blobfest - 5K/10K/Half Marathon', 'time' => '7am Start']
        ];

        foreach ($blobfestDays as $blob) {
            if ($blob['date'] < $today) continue;

            $events[] = [
                'id' => 'blobfest_' . $blob['date']->format('Ymd'),
                'type' => 'event',
                'title' => $blob['title'],
                'venue_info' => [
                    'name' => 'The Colonial Theatre & Downtown',
                    'location' => ['lat' => 40.1304, 'lng' => -75.5155]
                ],
                'raw_date_string' => $blob['date']->format('M d, Y'),
                'attributes' => [
                    'category' => 'Festival',
                    'vibes' => ['Family Friendly', 'Cult Classic', 'Horror', 'Community'],
                    'price' => 'Varies',
                    'time' => $blob['time']
                ],
                'media' => [
                    'image' => 'https://images.unsplash.com/photo-1574267432644-f610246f25be?auto=format&fit=crop&w=600&q=80'
                ],
                'action_link' => 'https://thecolonialtheatre.com/blobfest/'
            ];
        }
    }
    logMsg("  Added Blobfest events");

    logMsg("  TOTAL: " . count($events) . " recurring events generated");
    return $events;
}

// ============================================================
// STEP 2: SCRAPE COLONIAL THEATRE
// ============================================================

function scrapeColonial() {
    logMsg("STEP 2: Scraping Colonial Theatre...");

    $url = 'https://thecolonialtheatre.com/events/';
    $events = [];

    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: Mozilla/5.0\r\n",
            'timeout' => 30
        ]
    ]);

    $html = @file_get_contents($url, false, $context);

    if ($html === false) {
        logMsg("  WARNING: Could not connect to Colonial Theatre website");
        return false;
    }

    $doc = new DOMDocument();
    @$doc->loadHTML($html);
    $xpath = new DOMXPath($doc);

    $eventCards = $xpath->query("//div[contains(@class, 'eventrow')]");
    logMsg("  Found {$eventCards->length} events");

    foreach ($eventCards as $card) {
        try {
            $titleNodes = $xpath->query(".//h3[contains(@class, 'eventrow-title')]", $card);
            $title = $titleNodes->length > 0 ? trim($titleNodes->item(0)->textContent) : 'Unknown Event';
            $title = str_replace(['Rising Sun Presents ', 'The Colonial Presents '], '', $title);

            $btnNodes = $xpath->query(".//a[contains(@class, 'btn')]", $card);
            $link = $btnNodes->length > 0 ? $btnNodes->item(0)->getAttribute('href') : '#';

            $dateNodes = $xpath->query(".//time[contains(@class, 'eventrow-date')]", $card);
            $dateText = $dateNodes->length > 0 ? trim($dateNodes->item(0)->textContent) : 'Check website';

            $imgNodes = $xpath->query(".//div[contains(@class, 'eventrow-img')]//img", $card);
            $imgSrc = '';
            if ($imgNodes->length > 0) {
                $img = $imgNodes->item(0);
                $imgSrc = $img->getAttribute('data-src') ?: $img->getAttribute('src');
            }

            $tagNodes = $xpath->query(".//a[contains(@class, 'eventrow-tag')]", $card);
            $category = $tagNodes->length > 0 ? trim($tagNodes->item(0)->textContent) : 'General';

            $events[] = [
                'id' => 'col_' . abs(crc32($title)),
                'type' => 'event',
                'title' => $title,
                'venue_info' => [
                    'name' => 'The Colonial Theatre',
                    'location' => ['lat' => 40.132, 'lng' => -75.513]
                ],
                'raw_date_string' => $dateText,
                'attributes' => [
                    'category' => $category,
                    'vibes' => [$category, 'Historic Venue']
                ],
                'media' => ['image' => $imgSrc],
                'action_link' => $link
            ];

        } catch (Exception $e) {
            logMsg("  WARNING: Error parsing event card: " . $e->getMessage());
        }
    }

    logMsg("  SUCCESS: Scraped " . count($events) . " Colonial Theatre events");
    return $events;
}

// ============================================================
// STEP 3: SCRAPE EXPO CENTER (OAKS)
// ============================================================

function scrapeOaks() {
    logMsg("STEP 3: Scraping Expo Center...");

    $url = 'https://phillyexpocenter.com/events/';
    $events = [];

    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: Mozilla/5.0\r\n",
            'timeout' => 30
        ]
    ]);

    $html = @file_get_contents($url, false, $context);

    if ($html === false) {
        logMsg("  WARNING: Could not connect to Expo Center website");
        return false;
    }

    $doc = new DOMDocument();
    @$doc->loadHTML($html);
    $xpath = new DOMXPath($doc);

    $eventCards = $xpath->query("//article[contains(@class, 'mec-event-article')]");
    logMsg("  Found {$eventCards->length} events");

    foreach ($eventCards as $card) {
        try {
            $titleNodes = $xpath->query(".//h4[contains(@class, 'mec-event-title')]//a", $card);
            $title = $titleNodes->length > 0 ? trim($titleNodes->item(0)->textContent) : 'Unknown Event';
            $link = $titleNodes->length > 0 ? $titleNodes->item(0)->getAttribute('href') : '#';

            $startDateNodes = $xpath->query(".//span[contains(@class, 'mec-start-date-label')]", $card);
            $endDateNodes = $xpath->query(".//span[contains(@class, 'mec-end-date-label')]", $card);
            $dateText = '';
            if ($startDateNodes->length > 0) $dateText .= trim($startDateNodes->item(0)->textContent);
            if ($endDateNodes->length > 0) $dateText .= trim($endDateNodes->item(0)->textContent);

            $imgNodes = $xpath->query(".//div[contains(@class, 'mec-event-image')]//img", $card);
            $imgSrc = $imgNodes->length > 0 ? $imgNodes->item(0)->getAttribute('src') : '';

            $locNodes = $xpath->query(".//div[contains(@class, 'mec-event-loc-place')]", $card);
            $location = $locNodes->length > 0 ? trim($locNodes->item(0)->textContent) : 'Expo Center';

            $events[] = [
                'id' => 'oaks_' . abs(crc32($title)),
                'type' => 'event',
                'title' => $title,
                'venue_info' => [
                    'name' => 'Greater Philadelphia Expo Center',
                    'location' => ['lat' => 40.123, 'lng' => -75.450]
                ],
                'raw_date_string' => $dateText,
                'attributes' => [
                    'category' => 'Expo',
                    'vibes' => ['Family Friendly', 'Large Crowd', $location],
                    'price' => 'Check Link'
                ],
                'media' => ['image' => $imgSrc],
                'action_link' => $link
            ];

        } catch (Exception $e) {
            logMsg("  WARNING: Error parsing expo event: " . $e->getMessage());
        }
    }

    logMsg("  SUCCESS: Scraped " . count($events) . " Expo Center events");
    return $events;
}

// ============================================================
// STEP 4: SCRAPE STEEL CITY COFFEEHOUSE
// ============================================================

function scrapeSteelCity() {
    logMsg("STEP 4: Scraping Steel City Coffeehouse...");

    $venueInfo = [
        'name' => 'Steel City Coffeehouse & Brewery',
        'location' => ['lat' => 40.1305, 'lng' => -75.5148]
    ];
    $venueUrl = 'https://www.steelcityphx.com/concerts-and-events';

    // Try Bandsintown API first (venue ID 10008291)
    $events = scrapeBandsintownVenue('10008291', $venueInfo, $venueUrl, 'sc_', ['Live Music', 'Coffeehouse', 'Brewery']);
    if ($events !== false && count($events) > 0) {
        logMsg("  SUCCESS: Scraped " . count($events) . " Steel City events (via Bandsintown)");
        return $events;
    }

    // Try Squarespace JSON API
    $events = scrapeSquarespaceJson($venueUrl, $venueInfo, 'sc_', ['Live Music', 'Coffeehouse', 'Brewery']);
    if ($events !== false && count($events) > 0) {
        logMsg("  SUCCESS: Scraped " . count($events) . " Steel City events (via Squarespace JSON)");
        return $events;
    }

    // Fallback: direct HTML scrape
    $events = [];
    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\nAccept: text/html,application/xhtml+xml\r\n",
            'timeout' => 30
        ]
    ]);

    $html = @file_get_contents($venueUrl, false, $context);

    if ($html === false) {
        logMsg("  WARNING: Could not connect to Steel City website");
        return false;
    }

    $doc = new DOMDocument();
    @$doc->loadHTML($html);
    $xpath = new DOMXPath($doc);

    $eventCards = $xpath->query("//article[contains(@class, 'eventlist-event')]");
    if ($eventCards->length === 0) {
        $eventCards = $xpath->query("//div[contains(@class, 'summary-item')]");
    }
    if ($eventCards->length === 0) {
        $eventCards = $xpath->query("//main//article");
    }
    logMsg("  Found {$eventCards->length} events (HTML fallback)");

    foreach ($eventCards as $card) {
        try {
            $titleNodes = $xpath->query(".//h1 | .//h2 | .//h3 | .//a[contains(@class, 'eventlist-title-link')]", $card);
            $title = $titleNodes->length > 0 ? trim($titleNodes->item(0)->textContent) : null;
            if (!$title) continue;

            $linkNodes = $xpath->query(".//a[@href]", $card);
            $link = $venueUrl;
            if ($linkNodes->length > 0) {
                $link = $linkNodes->item(0)->getAttribute('href');
                if (strpos($link, '/') === 0) {
                    $link = 'https://www.steelcityphx.com' . $link;
                }
            }

            $dateNodes = $xpath->query(".//time | .//span[contains(@class, 'date')]", $card);
            $dateText = 'Check website';
            if ($dateNodes->length > 0) {
                $dateEl = $dateNodes->item(0);
                $dateText = $dateEl->getAttribute('datetime') ?: trim($dateEl->textContent);
            }

            $events[] = [
                'id' => 'sc_' . abs(crc32($title)),
                'type' => 'event',
                'title' => $title,
                'venue_info' => $venueInfo,
                'raw_date_string' => $dateText,
                'attributes' => [
                    'category' => 'Live Music',
                    'vibes' => ['Live Music', 'Coffeehouse', 'Brewery'],
                    'price' => 'Check Link'
                ],
                'media' => ['image' => ''],
                'action_link' => $link
            ];

        } catch (Exception $e) {
            logMsg("  WARNING: Error parsing Steel City event: " . $e->getMessage());
        }
    }

    logMsg("  SUCCESS: Scraped " . count($events) . " Steel City events");
    return $events;
}

// ============================================================
// STEP 5: SCRAPE MOLLY MAGUIRE'S
// ============================================================

function scrapeMollyMaguires() {
    logMsg("STEP 5: Scraping Molly Maguire's...");

    $venueInfo = [
        'name' => "Molly Maguire's Irish Pub",
        'location' => ['lat' => 40.1317, 'lng' => -75.5149]
    ];
    $venueUrl = 'https://www.mollymaguiresphoenixville.com/events/';

    // Try Bandsintown API first (venue ID 10131755)
    $events = scrapeBandsintownVenue('10131755', $venueInfo, $venueUrl, 'mm_', ['Live Music', 'Irish Pub']);
    if ($events !== false && count($events) > 0) {
        // Categorize Molly's events by title keywords
        foreach ($events as &$event) {
            $titleLower = strtolower($event['title']);
            if (preg_match('/karaoke|dj|dance/', $titleLower)) {
                $event['attributes']['category'] = 'Nightlife';
                $event['attributes']['vibes'] = ['Nightlife', 'Irish Pub'];
            } elseif (preg_match('/trivia|quiz/', $titleLower)) {
                $event['attributes']['category'] = 'Trivia';
                $event['attributes']['vibes'] = ['Trivia', 'Irish Pub'];
            } elseif (preg_match('/irish session|trad/', $titleLower)) {
                $event['attributes']['category'] = 'Irish Music';
                $event['attributes']['vibes'] = ['Irish Music', 'Traditional', 'Irish Pub'];
            }
        }
        unset($event);
        logMsg("  SUCCESS: Scraped " . count($events) . " Molly Maguire's events (via Bandsintown)");
        return $events;
    }

    // Fallback: direct HTML scrape
    $events = [];
    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\nAccept: text/html,application/xhtml+xml\r\n",
            'timeout' => 30
        ]
    ]);

    $html = @file_get_contents($venueUrl, false, $context);

    if ($html === false) {
        logMsg("  WARNING: Could not connect to Molly Maguire's website");
        return false;
    }

    $doc = new DOMDocument();
    @$doc->loadHTML($html);
    $xpath = new DOMXPath($doc);

    $selectors = [
        "//div[contains(@class, 'event-item')]",
        "//div[contains(@class, 'event-card')]",
        "//article[contains(@class, 'event')]",
        "//div[contains(@class, 'tribe-events')]",
        "//div[contains(@class, 'summary-item')]",
        "//main//article",
    ];

    $eventCards = null;
    foreach ($selectors as $selector) {
        $result = $xpath->query($selector);
        if ($result->length > 0) {
            $eventCards = $result;
            break;
        }
    }

    $cardCount = $eventCards ? $eventCards->length : 0;
    logMsg("  Found {$cardCount} events (HTML fallback)");

    if ($eventCards) {
        foreach ($eventCards as $card) {
            try {
                $titleNodes = $xpath->query(".//h2 | .//h3 | .//h1", $card);
                $title = $titleNodes->length > 0 ? trim($titleNodes->item(0)->textContent) : null;
                if (!$title) continue;

                $linkNodes = $xpath->query(".//a[@href]", $card);
                $link = $venueUrl;
                if ($linkNodes->length > 0) {
                    $link = $linkNodes->item(0)->getAttribute('href');
                    if (strpos($link, '/') === 0) {
                        $link = 'https://www.mollymaguiresphoenixville.com' . $link;
                    }
                }

                $dateNodes = $xpath->query(".//time | .//span[contains(@class, 'date')]", $card);
                $dateText = 'Check website';
                if ($dateNodes->length > 0) {
                    $dateEl = $dateNodes->item(0);
                    $dateText = $dateEl->getAttribute('datetime') ?: trim($dateEl->textContent);
                }

                $titleLower = strtolower($title);
                if (preg_match('/karaoke|dj|dance/', $titleLower)) {
                    $category = 'Nightlife';
                    $vibes = ['Nightlife', 'Irish Pub'];
                } elseif (preg_match('/trivia|quiz/', $titleLower)) {
                    $category = 'Trivia';
                    $vibes = ['Trivia', 'Irish Pub'];
                } elseif (preg_match('/irish session|trad/', $titleLower)) {
                    $category = 'Irish Music';
                    $vibes = ['Irish Music', 'Traditional', 'Irish Pub'];
                } else {
                    $category = 'Live Music';
                    $vibes = ['Live Music', 'Irish Pub'];
                }

                $events[] = [
                    'id' => 'mm_' . abs(crc32($title . $dateText)),
                    'type' => 'event',
                    'title' => $title,
                    'venue_info' => $venueInfo,
                    'raw_date_string' => $dateText,
                    'attributes' => [
                        'category' => $category,
                        'vibes' => $vibes,
                        'price' => 'Check Link'
                    ],
                    'media' => ['image' => ''],
                    'action_link' => $link
                ];

            } catch (Exception $e) {
                logMsg("  WARNING: Error parsing Molly Maguire's event: " . $e->getMessage());
            }
        }
    }

    logMsg("  SUCCESS: Scraped " . count($events) . " Molly Maguire's events");
    return $events;
}

// ============================================================
// MERGE & TRANSFORM EVENTS
// ============================================================

function parseDateAdvanced($dateString) {
    $dateString = preg_replace('/\s+/', ' ', trim($dateString));

    // Handle range - extract start date
    if (strpos($dateString, ' - ') !== false || strpos($dateString, '- ') !== false) {
        $parts = preg_split('/\s*-\s*/', $dateString);
        $dateString = trim($parts[0]);
    }

    // Match: Month Day, Year OR Month Day Year OR Month Day
    if (preg_match('/([A-Za-z]+)\s+(\d+)(?:,?\s+(\d{4}))?/', $dateString, $matches)) {
        $monthMap = [
            'Jan' => 1, 'January' => 1, 'Feb' => 2, 'February' => 2,
            'Mar' => 3, 'March' => 3, 'Apr' => 4, 'April' => 4,
            'May' => 5, 'Jun' => 6, 'June' => 6, 'Jul' => 7, 'July' => 7,
            'Aug' => 8, 'August' => 8, 'Sep' => 9, 'September' => 9,
            'Oct' => 10, 'October' => 10, 'Nov' => 11, 'November' => 11,
            'Dec' => 12, 'December' => 12
        ];

        $monthName = $matches[1];
        $day = (int)$matches[2];
        $year = isset($matches[3]) && $matches[3] ? (int)$matches[3] : (int)date('Y');
        $month = $monthMap[$monthName] ?? 1;

        try {
            return new DateTime("{$year}-{$month}-{$day}");
        } catch (Exception $e) {
            return null;
        }
    }

    return null;
}

function formatDateDisplay($dateString) {
    $dateString = preg_replace('/\s+/', ' ', trim($dateString));

    // Handle range
    if (strpos($dateString, ' - ') !== false || strpos($dateString, '- ') !== false) {
        $dateString = str_replace('- ', ' - ', $dateString);
        $dateString = str_replace(' -', ' - ', $dateString);
        $parts = explode(' - ', $dateString);

        if (count($parts) == 2) {
            $start = trim($parts[0]);
            $end = trim($parts[1]);

            if (preg_match('/([A-Za-z]+)\s+(\d+)/', $start, $startMatch)) {
                $startMonth = $startMatch[1];
                $startDay = (int)$startMatch[2];

                if (preg_match('/^(\d+)/', $end, $endMatch)) {
                    return "{$startMonth} {$startDay}-" . (int)$endMatch[1];
                }

                if (preg_match('/([A-Za-z]+)\s+(\d+)/', $end, $endMatch)) {
                    return "{$startMonth} {$startDay} - {$endMatch[1]} " . (int)$endMatch[2];
                }
            }
        }
    }

    // Single date
    if (preg_match('/([A-Za-z]+)\s+(\d+)/', $dateString, $match)) {
        return $match[1] . ' ' . (int)$match[2];
    }

    // Strip year suffixes
    return preg_replace('/,?\s*\d{4}/', '', $dateString);
}

function getDateCategory($eventDate) {
    if (!$eventDate) return 'later';

    $today = new DateTime('today');
    $tomorrow = (clone $today)->modify('+1 day');
    $weekEnd = (clone $today)->modify('+7 days');
    $nextWeekEnd = (clone $today)->modify('+14 days');
    $monthEnd = new DateTime('last day of this month');

    if ($eventDate->format('Y-m-d') === $today->format('Y-m-d')) return 'today';
    if ($eventDate->format('Y-m-d') === $tomorrow->format('Y-m-d')) return 'tomorrow';
    if ($eventDate < $weekEnd) return 'this_week';
    if ($eventDate < $nextWeekEnd) return 'next_week';
    if ($eventDate <= $monthEnd) return 'this_month';
    return 'later';
}

function getSmartLabel($eventDate) {
    if (!$eventDate) return '';

    $today = new DateTime('today');
    $tomorrow = (clone $today)->modify('+1 day');
    $weekEnd = (clone $today)->modify('+7 days');

    if ($eventDate->format('Y-m-d') === $today->format('Y-m-d')) return 'Today';
    if ($eventDate->format('Y-m-d') === $tomorrow->format('Y-m-d')) return 'Tomorrow';
    if ($eventDate < $weekEnd) return 'This Week';
    return '';
}

function transformEvents($allEvents) {
    logMsg("Transforming and formatting events...");

    $transformed = [];
    $today = new DateTime('today');
    $skipped = 0;

    foreach ($allEvents as $event) {
        $rawDate = $event['raw_date_string'] ?? 'TBA';
        $eventDate = parseDateAdvanced($rawDate);

        // Skip past events
        if ($eventDate && $eventDate < $today) {
            $skipped++;
            continue;
        }

        $transformed[] = [
            'title' => $event['title'] ?? 'Untitled Event',
            'date' => formatDateDisplay($rawDate),
            'date_label' => getSmartLabel($eventDate),
            'date_category' => getDateCategory($eventDate),
            'type' => $event['attributes']['category'] ?? 'Event',
            'loc' => $event['venue_info']['name'] ?? 'Unknown Venue',
            'img' => $event['media']['image'] ?? 'https://placehold.co/400x300?text=No+Image',
            'link' => $event['action_link'] ?? '',
            '_sort_date' => $eventDate ? $eventDate->getTimestamp() : 9999999999
        ];
    }

    // Second dedupe pass: sources may write the same date differently
    // ("June 17 - September 2" vs "Jun 17 - Sep 2"), which slips past the
    // merge-level dedupe. After parsing they share a timestamp, so dedupe on
    // normalized title + parsed date, preferring the copy with a real image.
    $best = [];
    $order = [];
    foreach ($transformed as $ev) {
        $key = preg_replace('/[^a-z0-9]/', '', strtolower($ev['title'])) . '|' . $ev['_sort_date'];
        $richness = [strpos($ev['img'], 'placehold.co') === false, !empty($ev['link'])];
        if (!isset($best[$key])) {
            $best[$key] = ['ev' => $ev, 'richness' => $richness];
            $order[] = $key;
        } elseif ($richness > $best[$key]['richness']) {
            $best[$key] = ['ev' => $ev, 'richness' => $richness];
        }
    }
    if (count($best) < count($transformed)) {
        logMsg("  Removed " . (count($transformed) - count($best)) . " duplicate events (post-parse)");
    }
    $transformed = [];
    foreach ($order as $key) {
        $transformed[] = $best[$key]['ev'];
    }

    $transformed = fuzzyDedupe($transformed);

    // Sort by date. Keep _sort_date in the output so buildStructuredData() can
    // derive an ISO startDate without re-parsing.
    usort($transformed, function($a, $b) {
        return $a['_sort_date'] - $b['_sort_date'];
    });

    logMsg("  Transformed " . count($transformed) . " upcoming events (skipped {$skipped} past)");
    return $transformed;
}

function titleTokens($title) {
    static $stopwords = ['the', 'a', 'an', 'at', 'of', 'in', 'on', 'with', 'and', 'for', 'to'];
    preg_match_all('/[a-z0-9]+/', strtolower($title), $m);
    return array_values(array_diff(array_unique($m[0]), $stopwords));
}

function fuzzyDedupe($events) {
    // Merge near-duplicate events: same parsed date, one title's tokens a
    // subset of the other's ("First Friday - July" vs "First Friday -
    // Downtown Phoenixville (July)"). Keeps the richer copy. Undated events
    // are skipped - they all share a sentinel timestamp and would over-merge.
    $byDate = [];
    foreach ($events as $ev) {
        $byDate[$ev['_sort_date']][] = $ev;
    }

    $removed = 0;
    $result = [];
    foreach ($byDate as $ts => $group) {
        if ($ts == 9999999999 || count($group) === 1) {
            foreach ($group as $ev) { $result[] = $ev; }
            continue;
        }
        $kept = []; // each: ['tokens' =>, 'ev' =>, 'richness' =>]
        foreach ($group as $ev) {
            $tokens = titleTokens($ev['title']);
            $richness = [strpos($ev['img'], 'placehold.co') === false, !empty($ev['link'])];
            $merged = false;
            foreach ($kept as $i => $entry) {
                $small = count($tokens) <= count($entry['tokens']) ? $tokens : $entry['tokens'];
                $large = count($tokens) <= count($entry['tokens']) ? $entry['tokens'] : $tokens;
                if (count($small) >= 2 && count(array_diff($small, $large)) === 0) {
                    $removed++;
                    if ($richness > $entry['richness']) {
                        $kept[$i] = ['tokens' => $tokens, 'ev' => $ev, 'richness' => $richness];
                    }
                    $merged = true;
                    break;
                }
            }
            if (!$merged) {
                $kept[] = ['tokens' => $tokens, 'ev' => $ev, 'richness' => $richness];
            }
        }
        foreach ($kept as $entry) { $result[] = $entry['ev']; }
    }

    if ($removed > 0) {
        logMsg("  Removed {$removed} near-duplicate events (fuzzy title match)");
    }
    return $result;
}

// ============================================================
// THIS WEEKEND PAGE + ICS FEED
// ============================================================

function weekendRange() {
    // Upcoming Fri-Sun, or the current weekend if today is Fri/Sat/Sun
    $today = new DateTime('today');
    $dow = (int)$today->format('N'); // Mon=1 .. Sun=7
    $friday = clone $today;
    if ($dow >= 5) {
        $friday->modify('-' . ($dow - 5) . ' days');
    } else {
        $friday->modify('+' . (5 - $dow) . ' days');
    }
    $sunday = (clone $friday)->modify('+2 days');
    return [$friday, $sunday];
}

function buildThisWeekendPage($events, $deployDir, $areaName, $ogImage, $canonicalBase) {
    list($friday, $sunday) = weekendRange();
    $today = new DateTime('today');
    $start = max($friday, $today);

    $picked = [];
    foreach ($events as $ev) {
        $ts = $ev['_sort_date'] ?? 9999999999;
        if ($ts == 9999999999) continue;
        $d = (new DateTime('@' . $ts))->setTime(0, 0); // server TZ == builder TZ (UTC)
        if ($d >= $start && $d <= $sunday) {
            $picked[] = ['date' => $d, 'ev' => $ev];
        }
    }
    usort($picked, function($a, $b) {
        $c = $a['date'] <=> $b['date'];
        return $c !== 0 ? $c : strcasecmp($a['ev']['title'], $b['ev']['title']);
    });

    $base = rtrim($canonicalBase, '/');
    $canonical = $base . '/this-weekend/';
    $rangeLabel = $friday->format('F j') . '–' .
        ($friday->format('m') === $sunday->format('m') ? $sunday->format('j') : $sunday->format('F j')) .
        ', ' . $sunday->format('Y');
    $title = "Things to Do in {$areaName} This Weekend ({$rangeLabel})";
    $description = count($picked) . " events happening in and around {$areaName} PA this weekend, "
        . "{$rangeLabel}: festivals, live music, markets, family activities. Updated daily.";

    // Day sections
    $byDay = [];
    foreach ($picked as $p) {
        $byDay[$p['date']->format('Y-m-d')][] = $p;
    }
    $sections = '';
    foreach ($byDay as $entries) {
        $sections .= '<h2>' . $entries[0]['date']->format('l, F j') . "</h2>\n<ul>\n";
        foreach ($entries as $p) {
            $ev = $p['ev'];
            $t = htmlspecialchars($ev['title'], ENT_QUOTES);
            $titleHtml = !empty($ev['link'])
                ? '<a href="' . htmlspecialchars($ev['link'], ENT_QUOTES) . '" rel="nofollow">' . $t . '</a>'
                : $t;
            $metaParts = array_filter([
                htmlspecialchars($ev['loc'] ?? '', ENT_QUOTES),
                ($ev['type'] ?? '') !== 'Event' ? htmlspecialchars($ev['type'] ?? '', ENT_QUOTES) : ''
            ]);
            $sections .= '<li><strong>' . $titleHtml . '</strong><br><span class="meta">'
                . implode(' &middot; ', $metaParts) . "</span></li>\n";
        }
        $sections .= "</ul>\n";
    }
    if ($sections === '') {
        $sections = '<p>No events listed for this weekend yet — check the <a href="' . $base
            . '/">full ' . htmlspecialchars($areaName) . ' events calendar</a>.</p>';
    }

    // JSON-LD ItemList
    $items = [];
    foreach ($picked as $i => $p) {
        $item = [
            '@type' => 'ListItem',
            'position' => $i + 1,
            'item' => [
                '@type' => 'Event',
                'name' => $p['ev']['title'],
                'startDate' => $p['date']->format('Y-m-d'),
                'eventAttendanceMode' => 'https://schema.org/OfflineEventAttendanceMode',
                'location' => [
                    '@type' => 'Place',
                    'name' => $p['ev']['loc'] ?? $areaName,
                    'address' => ['@type' => 'PostalAddress', 'addressRegion' => 'PA', 'addressCountry' => 'US']
                ]
            ]
        ];
        if (!empty($p['ev']['link'])) {
            $item['item']['url'] = $p['ev']['link'];
        }
        $items[] = $item;
    }
    $jsonLd = json_encode([
        '@context' => 'https://schema.org',
        '@type' => 'ItemList',
        'name' => $title,
        'numberOfItems' => count($picked),
        'itemListElement' => $items
    ], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

    $titleEsc = htmlspecialchars($title, ENT_QUOTES);
    $descEsc = htmlspecialchars($description, ENT_QUOTES);
    $areaEsc = htmlspecialchars($areaName, ENT_QUOTES);
    $generated = date('Y-m-d');
    $count = count($picked);

    $page = <<<HTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{$titleEsc} | LocalSpot</title>
<meta name="description" content="{$descEsc}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{$canonical}">
<meta property="og:type" content="website">
<meta property="og:url" content="{$canonical}">
<meta property="og:title" content="{$titleEsc}">
<meta property="og:description" content="{$descEsc}">
<meta property="og:image" content="{$ogImage}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{$jsonLd}</script>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:24px 16px;color:#0f172a;line-height:1.5}
h1{font-size:1.6rem;margin-bottom:4px}
.sub{color:#64748b;margin-top:0}
h2{font-size:1.1rem;margin:28px 0 8px;border-bottom:2px solid #e2e8f0;padding-bottom:4px}
ul{list-style:none;padding:0;margin:0}
li{padding:10px 0;border-bottom:1px solid #f1f5f9}
a{color:#2563eb;text-decoration:none}
a:hover{text-decoration:underline}
.meta{color:#64748b;font-size:0.85rem}
.cta{display:inline-block;margin-top:24px;background:#2563eb;color:#fff;padding:10px 18px;border-radius:10px;font-weight:700}
footer{margin-top:32px;color:#94a3b8;font-size:0.8rem}
</style>
</head>
<body>
<h1>Things to Do in {$areaEsc} This Weekend</h1>
<p class="sub">{$rangeLabel} &middot; {$count} events &middot; updated daily</p>
{$sections}
<a class="cta" href="{$base}/">See all {$areaEsc} events &rarr;</a>
<p><a href="{$base}/events.ics">&#128197; Subscribe to the {$areaEsc} events calendar</a></p>
<footer>LocalSpot HQ &middot; generated {$generated}</footer>
</body>
</html>
HTML;

    $dir = $deployDir . '/this-weekend';
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
    }
    if (@file_put_contents($dir . '/index.html', $page) !== false) {
        logMsg("  This Weekend page: {$count} events -> {$dir}/index.html");
    } else {
        logMsg("  WARNING: could not write This Weekend page");
    }
}

function icsEscape($text) {
    return str_replace(["\\", ";", ",", "\n"], ["\\\\", "\\;", "\\,", "\\n"], $text);
}

function icsFold($line) {
    // Fold lines >75 octets per RFC 5545
    $out = [];
    while (strlen($line) > 73) {
        $cut = 73;
        // don't split a UTF-8 sequence
        while ($cut > 0 && (ord($line[$cut]) & 0xC0) === 0x80) {
            $cut--;
        }
        $out[] = substr($line, 0, $cut);
        $line = ' ' . substr($line, $cut);
    }
    $out[] = $line;
    return implode("\r\n", $out);
}

function buildIcsFeed($events, $deployDir, $areaName) {
    $nowUtc = gmdate('Ymd\THis\Z');
    $lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//LocalSpot HQ//' . $areaName . ' Events//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:' . icsEscape($areaName) . ' Events (LocalSpot)',
        'X-WR-TIMEZONE:America/New_York',
    ];

    $count = 0;
    foreach ($events as $ev) {
        $ts = $ev['_sort_date'] ?? 9999999999;
        if ($ts == 9999999999) continue;
        $day = gmdate('Ymd', $ts);
        $nextDay = gmdate('Ymd', $ts + 86400);
        $uid = md5($ev['title'] . gmdate('Y-m-d', $ts));
        $lines[] = 'BEGIN:VEVENT';
        $lines[] = "UID:{$uid}@localspothq.com";
        $lines[] = "DTSTAMP:{$nowUtc}";
        $lines[] = "DTSTART;VALUE=DATE:{$day}";
        $lines[] = "DTEND;VALUE=DATE:{$nextDay}";
        $lines[] = icsFold('SUMMARY:' . icsEscape($ev['title']));
        if (!empty($ev['loc'])) {
            $lines[] = icsFold('LOCATION:' . icsEscape($ev['loc']));
        }
        if (!empty($ev['link'])) {
            $lines[] = icsFold('URL:' . $ev['link']);
        }
        $lines[] = 'END:VEVENT';
        $count++;
    }
    $lines[] = 'END:VCALENDAR';

    if (@file_put_contents($deployDir . '/events.ics', implode("\r\n", $lines) . "\r\n") !== false) {
        logMsg("  ICS feed: {$count} events -> {$deployDir}/events.ics");
    } else {
        logMsg("  WARNING: could not write ICS feed");
    }
}

// ============================================================
// BUILD STRUCTURED DATA (JSON-LD)
// ============================================================

function buildStructuredData($areaName, $metaTitle, $metaDescription, $canonicalUrl, $events) {
    $webPage = [
        '@context' => 'https://schema.org',
        '@type' => 'WebPage',
        'name' => $metaTitle,
        'description' => $metaDescription,
        'url' => $canonicalUrl,
        'isPartOf' => [
            '@type' => 'WebSite',
            'name' => 'LocalSpot HQ',
            'url' => 'https://www.localspothq.com'
        ],
        'about' => [
            '@type' => 'Place',
            'name' => $areaName,
            'address' => [
                '@type' => 'PostalAddress',
                'addressRegion' => 'PA',
                'addressCountry' => 'US'
            ]
        ]
    ];

    $eventItems = [];
    foreach ($events as $ev) {
        if (!is_array($ev)) continue;
        $title = $ev['title'] ?? null;
        $ts = $ev['_sort_date'] ?? null;
        // Skip sentinel "no parseable date" entries
        if (!$title || !$ts || $ts >= 9000000000) continue;
        $startIso = gmdate('Y-m-d', (int)$ts);
        $item = [
            '@context' => 'https://schema.org',
            '@type' => 'Event',
            'name' => $title,
            'startDate' => $startIso,
            'eventStatus' => 'https://schema.org/EventScheduled',
            'eventAttendanceMode' => 'https://schema.org/OfflineEventAttendanceMode'
        ];
        if (!empty($ev['img'])) $item['image'] = $ev['img'];
        if (!empty($ev['link'])) $item['url'] = $ev['link'];
        if (!empty($ev['loc'])) {
            $item['location'] = [
                '@type' => 'Place',
                'name' => $ev['loc'],
                'address' => [
                    '@type' => 'PostalAddress',
                    'addressLocality' => $areaName,
                    'addressRegion' => 'PA',
                    'addressCountry' => 'US'
                ]
            ];
        }
        $eventItems[] = $item;
    }

    $blocks = [];
    $blocks[] = '<script type="application/ld+json">' . "\n"
              . json_encode($webPage, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n"
              . '</script>';
    if (!empty($eventItems)) {
        $blocks[] = '<script type="application/ld+json">' . "\n"
                  . json_encode($eventItems, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n"
                  . '</script>';
    }
    return implode("\n    ", $blocks);
}

// ============================================================
// INJECT DATA INTO HTML
// ============================================================

function injectDataIntoHtml($dataDir, $templateFile, $events, $areaName, $areaTagline, $metaTitle,
                            $metaDescription = '', $metaKeywords = '', $ogImage = '', $canonicalUrl = '') {
    logMsg("Loading static data files from repo...");

    // Load dining data
    $diningFile = $dataDir . '/dining.json';
    $dining = file_exists($diningFile) ? json_decode(file_get_contents($diningFile), true) : [];
    logMsg("  Loaded " . count($dining) . " dining spots from " . basename($diningFile));

    // Load outings data
    $outingsFile = $dataDir . '/outings.json';
    $outings = file_exists($outingsFile) ? json_decode(file_get_contents($outingsFile), true) : [];
    logMsg("  Loaded " . count($outings) . " outings from " . basename($outingsFile));

    // Load curated plans
    $plansFile = $dataDir . '/plans.json';
    $plans = file_exists($plansFile) ? json_decode(file_get_contents($plansFile), true) : [];
    logMsg("  Loaded " . count($plans) . " curated plans from " . basename($plansFile));

    // Load HTML template
    logMsg("Injecting data into HTML template...");
    if (!file_exists($templateFile)) {
        logMsg("  ERROR: Template file not found: {$templateFile}");
        return false;
    }
    $html = file_get_contents($templateFile);
    logMsg("  Loaded template (" . strlen($html) . " characters)");

    // Substitute area + SEO placeholders
    $buildTimestamp = gmdate('Y-m-d\TH:i:s\Z');
    $structuredData = buildStructuredData($areaName, $metaTitle, $metaDescription, $canonicalUrl, $events);
    $replacements = [
        '{{AREA_NAME}}' => $areaName,
        '{{AREA_TAGLINE}}' => $areaTagline,
        '{{META_TITLE}}' => $metaTitle,
        '{{META_DESCRIPTION}}' => $metaDescription,
        '{{META_KEYWORDS}}' => $metaKeywords,
        '{{OG_IMAGE}}' => $ogImage,
        '{{CANONICAL_URL}}' => $canonicalUrl,
        '{{BUILD_TIMESTAMP}}' => $buildTimestamp,
        '{{STRUCTURED_DATA}}' => $structuredData,
    ];
    foreach ($replacements as $placeholder => $value) {
        $html = str_replace($placeholder, $value, $html);
    }
    logMsg("  Replaced " . count($replacements) . " placeholders (build " . $buildTimestamp . ")");

    // Warn on any unsubstituted {{PLACEHOLDER}} so future template additions don't silently leak
    if (preg_match_all('/\{\{[A-Z_]+\}\}/', $html, $leftover)) {
        $unique = array_unique($leftover[0]);
        logMsg("  WARNING: unsubstituted placeholders remain: " . implode(', ', $unique));
    }

    // Convert to JS format
    $eventsJs = json_encode($events, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    $diningJs = json_encode($dining, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    $outingsJs = json_encode($outings, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    $plansJs = json_encode($plans, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

    // Inject events
    $html = preg_replace('/const eventsData = \[[\s\S]*?\];/', 'const eventsData = ' . $eventsJs . ';', $html, 1, $count);
    if ($count > 0) {
        logMsg("  Injected " . count($events) . " events");
    } else {
        logMsg("  ERROR: Could not find eventsData pattern!");
        return false;
    }

    // Inject dining
    $html = preg_replace('/const diningData = \[[\s\S]*?\];/', 'const diningData = ' . $diningJs . ';', $html, 1, $count);
    if ($count > 0) {
        logMsg("  Injected " . count($dining) . " dining spots");
    } else {
        logMsg("  ERROR: Could not find diningData pattern!");
        return false;
    }

    // Inject outings
    $html = preg_replace('/const outingsData = \[[\s\S]*?\];/', 'const outingsData = ' . $outingsJs . ';', $html, 1, $count);
    if ($count > 0) {
        logMsg("  Injected " . count($outings) . " outings");
    } else {
        logMsg("  ERROR: Could not find outingsData pattern!");
        return false;
    }

    // Inject plans
    $html = preg_replace('/const plansData = \[[\s\S]*?\];/', 'const plansData = ' . $plansJs . ';', $html, 1, $count);
    if ($count > 0) {
        logMsg("  Injected " . count($plans) . " curated plans");
    } else {
        logMsg("  WARNING: Could not find plansData pattern");
    }

    // Remove landing page, show main app
    logMsg("Post-processing: removing landing page...");

    $html = str_replace(
        '<div id="landing-page" class="fixed inset-0',
        '<div id="landing-page" class="hidden fixed inset-0',
        $html
    );

    $html = str_replace(
        '<div id="main-app" class="hidden min-h-screen',
        '<div id="main-app" class="min-h-screen',
        $html
    );

    // Add auto-load script as its own <script> immediately before </body>.
    // Using a standalone block (rather than appending to an existing one) is
    // robust against trailing markup such as the build-timestamp footer.
    $autoLoadScript = "\n    <script>\n"
                    . "        // Auto-load content (landing page is skipped on built output)\n"
                    . "        window.addEventListener(\"DOMContentLoaded\", function() {\n"
                    . "            console.log(\"Auto-loading content...\");\n"
                    . "            if (typeof renderContent === \"function\") renderContent();\n"
                    . "        });\n"
                    . "    </script>\n";

    if (strpos($html, '</body>') !== false) {
        $html = preg_replace('/<\/body>/', $autoLoadScript . '</body>', $html, 1);
        logMsg("  Landing page removed, auto-load added before </body>");
    } else {
        logMsg("  WARNING: </body> not found; appending auto-load at end");
        $html .= $autoLoadScript;
    }

    return $html;
}

// ============================================================
// BACKUP & DEPLOY
// ============================================================

function backupCurrentApp($deployPath, $backupDir) {
    if (!is_dir($backupDir)) mkdir($backupDir, 0755, true);

    if (file_exists($deployPath)) {
        $dateStr = date('Ymd_His');
        $backupPath = $backupDir . "/index_{$dateStr}.html";
        copy($deployPath, $backupPath);
        logMsg("  Backed up current site");

        // Keep only last 7 backups
        $backups = glob($backupDir . '/index_*.html');
        sort($backups);
        while (count($backups) > 7) {
            $old = array_shift($backups);
            unlink($old);
            logMsg("  Removed old backup: " . basename($old));
        }
    }
}

function deploy($html, $deployPath) {
    $size = strlen($html);

    if ($size < 50000) {
        logMsg("  WARNING: Generated HTML seems too small ({$size} bytes). Skipping deploy.");
        return false;
    }

    // Ensure deploy directory exists
    $deployDir = dirname($deployPath);
    if (!is_dir($deployDir)) {
        mkdir($deployDir, 0755, true);
        logMsg("  Created directory: {$deployDir}");
    }

    file_put_contents($deployPath, $html);
    logMsg("  Deployed ({$size} bytes) to {$deployPath}");
    return true;
}

// ============================================================
// MAIN: RUN EVERYTHING
// ============================================================

logMsg(str_repeat('=', 60));
logMsg("LOCALSPOT AUTO-UPDATE STARTING");
logMsg(str_repeat('=', 60));

// Ensure directories exist
if (!is_dir($LOG_DIR)) mkdir($LOG_DIR, 0755, true);
if (!is_dir($BACKUP_DIR)) mkdir($BACKUP_DIR, 0755, true);
if (!is_dir($CACHE_DIR)) mkdir($CACHE_DIR, 0755, true);

// Step 0: Git pull latest code
gitPullLatest($REPO_DIR);

// Step 1: Generate recurring events
$recurringEvents = generateRecurringEvents();

// Step 2: Scrape Colonial Theatre
$colonialEvents = scrapeColonial();
if ($colonialEvents === false) {
    logMsg("  Using cached colonial data...");
    $cachedFile = $CACHE_DIR . '/colonial_events.json';
    $colonialEvents = file_exists($cachedFile) ? json_decode(file_get_contents($cachedFile), true) : [];
    logMsg("  Loaded " . count($colonialEvents) . " cached Colonial events");
} else {
    file_put_contents($CACHE_DIR . '/colonial_events.json', json_encode($colonialEvents, JSON_PRETTY_PRINT));
}

// Step 3: Scrape Expo Center
$oaksEvents = scrapeOaks();
if ($oaksEvents === false) {
    logMsg("  Using cached oaks data...");
    $cachedFile = $CACHE_DIR . '/oaks_events.json';
    $oaksEvents = file_exists($cachedFile) ? json_decode(file_get_contents($cachedFile), true) : [];
    logMsg("  Loaded " . count($oaksEvents) . " cached Expo events");
} else {
    file_put_contents($CACHE_DIR . '/oaks_events.json', json_encode($oaksEvents, JSON_PRETTY_PRINT));
}

// Step 4: Scrape Steel City
$steelCityEvents = scrapeSteelCity();
if ($steelCityEvents === false) {
    logMsg("  Using cached Steel City data...");
    $cachedFile = $CACHE_DIR . '/steel_city_events.json';
    $steelCityEvents = file_exists($cachedFile) ? json_decode(file_get_contents($cachedFile), true) : [];
    logMsg("  Loaded " . count($steelCityEvents) . " cached Steel City events");
} else {
    file_put_contents($CACHE_DIR . '/steel_city_events.json', json_encode($steelCityEvents, JSON_PRETTY_PRINT));
}
if (empty($steelCityEvents)) {
    // Bandsintown blocks this host's datacenter IP; the local Python pipeline
    // scrapes it fine and commits the JSON, which STEP 0 syncs from GitHub.
    $repoFile = $DATA_DIR . '/scraped/steel_city_events.json';
    $steelCityEvents = file_exists($repoFile) ? (json_decode(file_get_contents($repoFile), true) ?: []) : [];
    if (!empty($steelCityEvents)) {
        logMsg("  Using " . count($steelCityEvents) . " repo-synced Steel City events");
    }
}

// Step 5: Scrape Molly Maguire's
$mollyEvents = scrapeMollyMaguires();
if ($mollyEvents === false) {
    logMsg("  Using cached Molly Maguire's data...");
    $cachedFile = $CACHE_DIR . '/molly_maguires_events.json';
    $mollyEvents = file_exists($cachedFile) ? json_decode(file_get_contents($cachedFile), true) : [];
    logMsg("  Loaded " . count($mollyEvents) . " cached Molly Maguire's events");
} else {
    file_put_contents($CACHE_DIR . '/molly_maguires_events.json', json_encode($mollyEvents, JSON_PRETTY_PRINT));
}
if (empty($mollyEvents)) {
    // Same Bandsintown IP block as Steel City - use the repo-synced JSON
    $repoFile = $DATA_DIR . '/scraped/molly_maguires_events.json';
    $mollyEvents = file_exists($repoFile) ? (json_decode(file_get_contents($repoFile), true) ?: []) : [];
    if (!empty($mollyEvents)) {
        logMsg("  Using " . count($mollyEvents) . " repo-synced Molly Maguire's events");
    }
}

// Step 6: Load AI-discovered events (written daily by the scheduled Claude routine).
// The file may be missing — treat that as zero events rather than an error.
$discoveredFile = $DATA_DIR . '/scraped/discovered_events.json';
$discoveredEvents = [];
if (file_exists($discoveredFile)) {
    $raw = json_decode(file_get_contents($discoveredFile), true);
    if (is_array($raw)) {
        $discoveredEvents = $raw;
        logMsg("  Loaded " . count($discoveredEvents) . " AI-discovered events from " . basename($discoveredFile));
    } else {
        logMsg("  WARNING: discovered_events.json present but not valid JSON; skipping");
    }
} else {
    logMsg("  No discovered_events.json yet (scheduled routine hasn't run)");
}

// Merge all events
logMsg("Merging all events...");
$allEvents = array_merge($recurringEvents, $colonialEvents, $oaksEvents, $steelCityEvents, $mollyEvents, $discoveredEvents);
$beforeDedupe = count($allEvents);
$allEvents = dedupeEvents($allEvents);
if (count($allEvents) < $beforeDedupe) {
    logMsg("  Removed " . ($beforeDedupe - count($allEvents)) . " duplicate events");
}
logMsg("  Total merged: " . count($allEvents) . " events");

// Transform events
$formattedEvents = transformEvents($allEvents);

// Inject into HTML
$finalHtml = injectDataIntoHtml(
    $DATA_DIR, $TEMPLATE_FILE, $formattedEvents,
    $AREA_NAME, $AREA_TAGLINE, $META_TITLE,
    $META_DESCRIPTION, $META_KEYWORDS, $OG_IMAGE, $CANONICAL_URL
);

if ($finalHtml === false) {
    logMsg(str_repeat('=', 60));
    logMsg("AUTO-UPDATE FAILED - Could not generate HTML");
    logMsg("Site was NOT updated (previous version still live)");
    logMsg(str_repeat('=', 60));
    exit(1);
}

// Backup & Deploy
$deployPath = $PUBLIC_HTML . '/phoenixville/index.html';
logMsg("Backing up and deploying...");
backupCurrentApp($deployPath, $BACKUP_DIR);

if (deploy($finalHtml, $deployPath)) {
    // SEO/subscription artifacts (non-fatal if they fail)
    buildThisWeekendPage($formattedEvents, $PUBLIC_HTML . '/phoenixville', $AREA_NAME, $OG_IMAGE, $CANONICAL_URL);
    buildIcsFeed($formattedEvents, $PUBLIC_HTML . '/phoenixville', $AREA_NAME);

    logMsg(str_repeat('=', 60));
    logMsg("AUTO-UPDATE COMPLETE!");
    logMsg("Events: " . count($formattedEvents));
    logMsg("Deployed to: {$deployPath}");
    logMsg("Site is now live with fresh data.");
    logMsg(str_repeat('=', 60));
} else {
    logMsg(str_repeat('=', 60));
    logMsg("AUTO-UPDATE FAILED - Deploy error");
    logMsg("Site was NOT updated (previous version still live)");
    logMsg(str_repeat('=', 60));
    exit(1);
}
