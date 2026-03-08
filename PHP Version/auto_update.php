<?php
/**
 * LOCALSPOT AUTO-UPDATE SCRIPT (PHP Server Version)
 * ==================================================
 * Runs automatically via Hostinger Cron Job at midnight.
 * Replaces the entire Python pipeline - no Python needed!
 *
 * What it does:
 *   1. Generates recurring events (Farmers Market, First Friday, Blobfest)
 *   2. Scrapes Colonial Theatre for new shows
 *   3. Scrapes Expo Center for new events
 *   4. Merges all events
 *   5. Formats dates and filters past events
 *   6. Loads dining, outings, curated plans from JSON files
 *   7. Injects all data into HTML template
 *   8. Removes landing page
 *   9. Deploys to public_html/app.html
 *   10. Logs everything
 *
 * Setup:
 *   Place in: ~/localspot/auto_update.php
 *   Cron:     0 5 * * * /usr/bin/php /home/u277879645/localspot/auto_update.php >> /home/u277879645/localspot/logs/update.log 2>&1
 */

// ============================================================
// CONFIGURATION
// ============================================================

$HOME_DIR = '/home/u277879645';
$SCRIPT_DIR = $HOME_DIR . '/localspot';
$PUBLIC_HTML = $HOME_DIR . '/domains/localspothq.com/public_html';
// Alternative path - uncomment if yours is different:
// $PUBLIC_HTML = $HOME_DIR . '/public_html';
$LOG_DIR = $SCRIPT_DIR . '/logs';
$BACKUP_DIR = $SCRIPT_DIR . '/backups';

// ============================================================
// LOGGING
// ============================================================

function logMsg($message) {
    $timestamp = date('Y-m-d H:i:s');
    echo "[{$timestamp}] {$message}\n";
}

// ============================================================
// STEP 1: GENERATE RECURRING EVENTS
// ============================================================

function generateRecurringEvents() {
    logMsg("STEP 1: Generating recurring events...");
    
    $events = [];
    
    // --- FARMERS MARKET (Every Saturday) ---
    $start = new DateTime('next Saturday');
    $end = new DateTime('2026-12-31');
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
    $firstFridayDates = [
        [2026, 2, 7], [2026, 3, 6], [2026, 4, 3], [2026, 5, 1],
        [2026, 6, 5], [2026, 7, 3], [2026, 8, 7], [2026, 9, 4],
        [2026, 10, 2], [2026, 11, 6], [2026, 12, 4]
    ];
    
    $ffCount = 0;
    $today = new DateTime('today');
    
    foreach ($firstFridayDates as [$year, $month, $day]) {
        $eventDate = new DateTime("{$year}-{$month}-{$day}");
        if ($eventDate < $today) continue;
        
        $monthName = $eventDate->format('F');
        $description = ($month == 12) ? 'Tree Lighting Ceremony with Santa!' : 'Live music, craft vendors, open-air dining';
        $special = ($month == 12) ? 'Tree Lighting' : 'Street Festival';
        
        $events[] = [
            'id' => 'first_friday_' . $eventDate->format('Ymd'),
            'type' => 'event',
            'title' => "First Friday - {$monthName}",
            'venue_info' => [
                'name' => 'Downtown Phoenixville',
                'location' => ['lat' => 40.1304, 'lng' => -75.5155]
            ],
            'raw_date_string' => $eventDate->format('M d, Y'),
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
    }
    logMsg("  Added {$ffCount} First Friday events");
    
    // --- BLOBFEST ---
    $blobfestDays = [
        ['date' => '2026-07-10', 'title' => 'Blobfest - Opening Night', 'time' => 'Evening'],
        ['date' => '2026-07-11', 'title' => 'Blobfest - Street Fair', 'time' => 'All Day'],
        ['date' => '2026-07-12', 'title' => 'Blobfest - 5K/10K/Half Marathon', 'time' => '7am Start']
    ];
    
    foreach ($blobfestDays as $blob) {
        $blobDate = new DateTime($blob['date']);
        if ($blobDate < $today) continue;
        
        $events[] = [
            'id' => 'blobfest_' . $blobDate->format('Ymd'),
            'type' => 'event',
            'title' => $blob['title'],
            'venue_info' => [
                'name' => 'The Colonial Theatre & Downtown',
                'location' => ['lat' => 40.1304, 'lng' => -75.5155]
            ],
            'raw_date_string' => $blobDate->format('M d, Y'),
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
    logMsg("  Added " . count($blobfestDays) . " Blobfest events");
    
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
    
    // Find event rows
    $eventCards = $xpath->query("//div[contains(@class, 'eventrow')]");
    logMsg("  Found {$eventCards->length} events");
    
    foreach ($eventCards as $card) {
        try {
            // Title
            $titleNodes = $xpath->query(".//h3[contains(@class, 'eventrow-title')]", $card);
            $title = $titleNodes->length > 0 ? trim($titleNodes->item(0)->textContent) : 'Unknown Event';
            $title = str_replace(['Rising Sun Presents ', 'The Colonial Presents '], '', $title);
            
            // Link
            $btnNodes = $xpath->query(".//a[contains(@class, 'btn')]", $card);
            $link = $btnNodes->length > 0 ? $btnNodes->item(0)->getAttribute('href') : '#';
            
            // Date
            $dateNodes = $xpath->query(".//time[contains(@class, 'eventrow-date')]", $card);
            $dateText = $dateNodes->length > 0 ? trim($dateNodes->item(0)->textContent) : 'Check website';
            
            // Image
            $imgNodes = $xpath->query(".//div[contains(@class, 'eventrow-img')]//img", $card);
            $imgSrc = '';
            if ($imgNodes->length > 0) {
                $img = $imgNodes->item(0);
                $imgSrc = $img->getAttribute('data-src') ?: $img->getAttribute('src');
            }
            
            // Category tag
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
            // Title & Link
            $titleNodes = $xpath->query(".//h4[contains(@class, 'mec-event-title')]//a", $card);
            $title = $titleNodes->length > 0 ? trim($titleNodes->item(0)->textContent) : 'Unknown Event';
            $link = $titleNodes->length > 0 ? $titleNodes->item(0)->getAttribute('href') : '#';
            
            // Date
            $startDateNodes = $xpath->query(".//span[contains(@class, 'mec-start-date-label')]", $card);
            $endDateNodes = $xpath->query(".//span[contains(@class, 'mec-end-date-label')]", $card);
            $dateText = '';
            if ($startDateNodes->length > 0) $dateText .= trim($startDateNodes->item(0)->textContent);
            if ($endDateNodes->length > 0) $dateText .= trim($endDateNodes->item(0)->textContent);
            
            // Image
            $imgNodes = $xpath->query(".//div[contains(@class, 'mec-event-image')]//img", $card);
            $imgSrc = $imgNodes->length > 0 ? $imgNodes->item(0)->getAttribute('src') : '';
            
            // Location
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
// STEP 4-5: MERGE & TRANSFORM EVENTS
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
    
    return str_replace([', 2026', ' 2026', ', 2027', ' 2027'], '', $dateString);
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
    logMsg("STEP 5: Transforming and formatting events...");
    
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
    
    logMsg("  Transformed " . count($transformed) . " upcoming events (skipped {$skipped} past events)");
    return $transformed;
}

// ============================================================
// STEP 6-8: INJECT DATA INTO HTML
// ============================================================

function injectDataIntoHtml($scriptDir, $events) {
    logMsg("STEP 6: Loading static data files...");
    
    // Load dining data
    $diningFile = $scriptDir . '/dining_curated.json';
    $dining = file_exists($diningFile) ? json_decode(file_get_contents($diningFile), true) : [];
    logMsg("  Loaded " . count($dining) . " dining spots");
    
    // Load outings data
    $outingsFile = $scriptDir . '/outings_curated.json';
    $outings = file_exists($outingsFile) ? json_decode(file_get_contents($outingsFile), true) : [];
    logMsg("  Loaded " . count($outings) . " outings");
    
    // Load curated plans
    $plansFile = $scriptDir . '/curated_plans.json';
    $plans = file_exists($plansFile) ? json_decode(file_get_contents($plansFile), true) : [];
    logMsg("  Loaded " . count($plans) . " curated plans");
    
    // Load HTML template
    logMsg("STEP 7: Injecting data into HTML template...");
    $templateFile = $scriptDir . '/phoenixville.html';
    if (!file_exists($templateFile)) {
        logMsg("  ERROR: Template file not found: {$templateFile}");
        return false;
    }
    $html = file_get_contents($templateFile);
    logMsg("  Loaded template (" . strlen($html) . " characters)");
    
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
    
    // STEP 8: Remove landing page
    logMsg("STEP 8: Removing landing page...");
    
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
// STEP 9: BACKUP & DEPLOY
// ============================================================

function backupCurrentApp($publicHtml, $backupDir) {
    if (!is_dir($backupDir)) mkdir($backupDir, 0755, true);
    
    $currentApp = $publicHtml . '/app.html';
    if (file_exists($currentApp)) {
        $dateStr = date('Ymd_His');
        $backupPath = $backupDir . "/app_{$dateStr}.html";
        copy($currentApp, $backupPath);
        logMsg("  Backed up current app.html");
        
        // Keep only last 7 backups
        $backups = glob($backupDir . '/app_*.html');
        sort($backups);
        while (count($backups) > 7) {
            $old = array_shift($backups);
            unlink($old);
            logMsg("  Removed old backup: " . basename($old));
        }
    }
}

function deploy($html, $publicHtml) {
    $destination = $publicHtml . '/app.html';
    $size = strlen($html);
    
    if ($size < 50000) {
        logMsg("  WARNING: Generated HTML seems too small ({$size} bytes). Skipping deploy.");
        return false;
    }
    
    file_put_contents($destination, $html);
    logMsg("  Deployed app.html ({$size} bytes) to {$destination}");
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

// Step 1: Generate recurring events
$recurringEvents = generateRecurringEvents();

// Step 2: Scrape Colonial Theatre
$colonialEvents = scrapeColonial();
if ($colonialEvents === false) {
    logMsg("  Using cached colonial data...");
    $cachedFile = $SCRIPT_DIR . '/colonial_events.json';
    $colonialEvents = file_exists($cachedFile) ? json_decode(file_get_contents($cachedFile), true) : [];
    logMsg("  Loaded " . count($colonialEvents) . " cached Colonial events");
} else {
    // Save fresh data as cache
    file_put_contents($SCRIPT_DIR . '/colonial_events.json', json_encode($colonialEvents, JSON_PRETTY_PRINT));
}

// Step 3: Scrape Expo Center
$oaksEvents = scrapeOaks();
if ($oaksEvents === false) {
    logMsg("  Using cached oaks data...");
    $cachedFile = $SCRIPT_DIR . '/oaks_events.json';
    $oaksEvents = file_exists($cachedFile) ? json_decode(file_get_contents($cachedFile), true) : [];
    logMsg("  Loaded " . count($oaksEvents) . " cached Expo events");
} else {
    // Save fresh data as cache
    file_put_contents($SCRIPT_DIR . '/oaks_events.json', json_encode($oaksEvents, JSON_PRETTY_PRINT));
}

// Step 4: Merge all events
logMsg("STEP 4: Merging all events...");
$allEvents = array_merge($recurringEvents, $colonialEvents, $oaksEvents);
logMsg("  Total merged: " . count($allEvents) . " events");

// Step 5: Transform events
$formattedEvents = transformEvents($allEvents);

// Steps 6-8: Inject into HTML
$finalHtml = injectDataIntoHtml($SCRIPT_DIR, $formattedEvents);

if ($finalHtml === false) {
    logMsg(str_repeat('=', 60));
    logMsg("AUTO-UPDATE FAILED - Could not generate HTML");
    logMsg("Site was NOT updated (previous version still live)");
    logMsg(str_repeat('=', 60));
    exit(1);
}

// Step 9: Backup & Deploy
logMsg("STEP 9: Backing up and deploying...");
backupCurrentApp($PUBLIC_HTML, $BACKUP_DIR);

if (deploy($finalHtml, $PUBLIC_HTML)) {
    logMsg(str_repeat('=', 60));
    logMsg("AUTO-UPDATE COMPLETE!");
    logMsg("Events: " . count($formattedEvents));
    logMsg("Site is now live with fresh data.");
    logMsg(str_repeat('=', 60));
} else {
    logMsg(str_repeat('=', 60));
    logMsg("AUTO-UPDATE FAILED - Deploy error");
    logMsg("Site was NOT updated (previous version still live)");
    logMsg(str_repeat('=', 60));
    exit(1);
}
