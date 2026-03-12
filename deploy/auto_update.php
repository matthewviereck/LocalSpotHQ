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

// ============================================================
// LOGGING
// ============================================================

function logMsg($message) {
    $timestamp = date('Y-m-d H:i:s');
    echo "[{$timestamp}] {$message}\n";
}

// ============================================================
// STEP 0: GIT PULL LATEST CODE
// ============================================================

function gitPullLatest($repoDir) {
    logMsg("STEP 0: Pulling latest code from GitHub...");

    if (!is_dir($repoDir . '/.git')) {
        logMsg("  ERROR: Not a git repo at {$repoDir}");
        logMsg("  Run: cd ~ && git clone https://github.com/matthewviereck/LocalSpotHQ.git localspot");
        return false;
    }

    $output = [];
    $returnCode = 0;
    exec("cd " . escapeshellarg($repoDir) . " && git pull origin main 2>&1", $output, $returnCode);

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

    $url = 'https://www.steelcityphx.com/concerts-and-events';
    $events = [];

    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: Mozilla/5.0\r\n",
            'timeout' => 30
        ]
    ]);

    $html = @file_get_contents($url, false, $context);

    if ($html === false) {
        logMsg("  WARNING: Could not connect to Steel City website");
        return false;
    }

    $doc = new DOMDocument();
    @$doc->loadHTML($html);
    $xpath = new DOMXPath($doc);

    // Squarespace eventlist format
    $eventCards = $xpath->query("//article[contains(@class, 'eventlist-event')]");
    if ($eventCards->length === 0) {
        // Fallback: summary block format
        $eventCards = $xpath->query("//div[contains(@class, 'summary-item')]");
    }
    if ($eventCards->length === 0) {
        // Fallback: any article in main
        $eventCards = $xpath->query("//main//article");
    }
    logMsg("  Found {$eventCards->length} events");

    foreach ($eventCards as $card) {
        try {
            // Title
            $titleNodes = $xpath->query(".//h1[contains(@class, 'eventlist-title')] | .//h2[contains(@class, 'eventlist-title')] | .//a[contains(@class, 'eventlist-title-link')] | .//h1 | .//h2 | .//h3", $card);
            $title = $titleNodes->length > 0 ? trim($titleNodes->item(0)->textContent) : null;
            if (!$title) continue;

            // Link
            $linkNodes = $xpath->query(".//a[contains(@class, 'eventlist-title-link')] | .//a[contains(@class, 'eventlist-button')] | .//a[@href]", $card);
            $link = '#';
            if ($linkNodes->length > 0) {
                $link = $linkNodes->item(0)->getAttribute('href');
                if (strpos($link, '/') === 0) {
                    $link = 'https://www.steelcityphx.com' . $link;
                }
            }

            // Date
            $dateNodes = $xpath->query(".//time[contains(@class, 'event-date')] | .//time | .//span[contains(@class, 'eventlist-datetag-startdate')] | .//li[contains(@class, 'eventlist-meta-date')]", $card);
            $dateText = 'Check website';
            if ($dateNodes->length > 0) {
                $dateEl = $dateNodes->item(0);
                $dateText = $dateEl->getAttribute('datetime') ?: trim($dateEl->textContent);
            }

            // Image
            $imgNodes = $xpath->query(".//img", $card);
            $imgSrc = '';
            if ($imgNodes->length > 0) {
                $img = $imgNodes->item(0);
                $imgSrc = $img->getAttribute('data-src') ?: $img->getAttribute('src');
            }

            $events[] = [
                'id' => 'sc_' . abs(crc32($title)),
                'type' => 'event',
                'title' => $title,
                'venue_info' => [
                    'name' => 'Steel City Coffeehouse & Brewery',
                    'location' => ['lat' => 40.1305, 'lng' => -75.5148]
                ],
                'raw_date_string' => $dateText,
                'attributes' => [
                    'category' => 'Live Music',
                    'vibes' => ['Live Music', 'Coffeehouse', 'Brewery'],
                    'price' => 'Check Link'
                ],
                'media' => ['image' => $imgSrc],
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

    $url = 'https://www.mollymaguiresphoenixville.com/events/';
    $events = [];

    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: Mozilla/5.0\r\n",
            'timeout' => 30
        ]
    ]);

    $html = @file_get_contents($url, false, $context);

    if ($html === false) {
        logMsg("  WARNING: Could not connect to Molly Maguire's website");
        return false;
    }

    $doc = new DOMDocument();
    @$doc->loadHTML($html);
    $xpath = new DOMXPath($doc);

    // Try multiple selectors for event containers
    $selectors = [
        "//div[contains(@class, 'event-item')]",
        "//div[contains(@class, 'event-card')]",
        "//article[contains(@class, 'event')]",
        "//div[contains(@class, 'tribe-events-calendar-list__event')]",
        "//article[contains(@class, 'tribe_events')]",
        "//div[contains(@class, 'event')]",
        "//div[contains(@class, 'summary-item')]",
    ];

    $eventCards = null;
    foreach ($selectors as $selector) {
        $result = $xpath->query($selector);
        if ($result->length > 0) {
            $eventCards = $result;
            break;
        }
    }

    if (!$eventCards || $eventCards->length === 0) {
        // Last resort: articles in main
        $eventCards = $xpath->query("//main//article");
    }

    $cardCount = $eventCards ? $eventCards->length : 0;
    logMsg("  Found {$cardCount} events");

    if ($eventCards) {
        foreach ($eventCards as $card) {
            try {
                // Title
                $titleNodes = $xpath->query(".//h2 | .//h3 | .//h1", $card);
                $title = $titleNodes->length > 0 ? trim($titleNodes->item(0)->textContent) : null;
                if (!$title) continue;

                // Link
                $linkNodes = $xpath->query(".//a[@href]", $card);
                $link = $url;
                if ($linkNodes->length > 0) {
                    $link = $linkNodes->item(0)->getAttribute('href');
                    if (strpos($link, '/') === 0) {
                        $link = 'https://www.mollymaguiresphoenixville.com' . $link;
                    }
                }

                // Date
                $dateNodes = $xpath->query(".//time | .//span[contains(@class, 'date')] | .//div[contains(@class, 'date')]", $card);
                $dateText = 'Check website';
                if ($dateNodes->length > 0) {
                    $dateEl = $dateNodes->item(0);
                    $dateText = $dateEl->getAttribute('datetime') ?: trim($dateEl->textContent);
                }

                // Image
                $imgNodes = $xpath->query(".//img", $card);
                $imgSrc = '';
                if ($imgNodes->length > 0) {
                    $img = $imgNodes->item(0);
                    $imgSrc = $img->getAttribute('data-src') ?: $img->getAttribute('src');
                }

                // Categorize by title keywords
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
                    'venue_info' => [
                        'name' => "Molly Maguire's Irish Pub",
                        'location' => ['lat' => 40.1317, 'lng' => -75.5149]
                    ],
                    'raw_date_string' => $dateText,
                    'attributes' => [
                        'category' => $category,
                        'vibes' => $vibes,
                        'price' => 'Check Link'
                    ],
                    'media' => ['image' => $imgSrc],
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

    // Sort by date
    usort($transformed, function($a, $b) {
        return $a['_sort_date'] - $b['_sort_date'];
    });

    // Remove sort field
    foreach ($transformed as &$event) {
        unset($event['_sort_date']);
    }

    logMsg("  Transformed " . count($transformed) . " upcoming events (skipped {$skipped} past)");
    return $transformed;
}

// ============================================================
// INJECT DATA INTO HTML
// ============================================================

function injectDataIntoHtml($dataDir, $templateFile, $events, $areaName, $areaTagline, $metaTitle) {
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

    // Substitute area placeholders
    $html = str_replace('{{AREA_NAME}}', $areaName, $html);
    $html = str_replace('{{AREA_TAGLINE}}', $areaTagline, $html);
    $html = str_replace('{{META_TITLE}}', $metaTitle, $html);
    logMsg("  Replaced area placeholders");

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

    // Add auto-load script
    $autoLoadScript = '
        // Load content when page loads (since we\'re skipping the landing page)
        window.addEventListener(\'DOMContentLoaded\', function() {
            console.log(\'Auto-loading content...\');
            renderContent();
        });

    ';

    $html = preg_replace('/([\s\S]*?)(<\/script>\s*<\/body>)/', '$1' . $autoLoadScript . '$2', $html, 1);

    logMsg("  Landing page removed, auto-load added");

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

// Merge all events
logMsg("Merging all events...");
$allEvents = array_merge($recurringEvents, $colonialEvents, $oaksEvents, $steelCityEvents, $mollyEvents);
logMsg("  Total merged: " . count($allEvents) . " events");

// Transform events
$formattedEvents = transformEvents($allEvents);

// Inject into HTML
$finalHtml = injectDataIntoHtml($DATA_DIR, $TEMPLATE_FILE, $formattedEvents, $AREA_NAME, $AREA_TAGLINE, $META_TITLE);

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
