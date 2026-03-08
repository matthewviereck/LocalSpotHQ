<?php
// eventbrite_scraper.php - Scrapes Eventbrite for Phoenixville area events
// This file gets included by auto_update.php

function scrapeEventbrite($scriptDir) {
    logMsg("Scraping Eventbrite for Phoenixville area events...");
    
    $cacheFile = $scriptDir . '/eventbrite_events.json';
    $events = [];
    
    // Search terms to find local events
    $searches = [
        'phoenixville',
        'collegeville+pa',
        'oaks+pa+19456'
    ];
    
    foreach ($searches as $search) {
        $url = "https://www.eventbrite.com/d/pa--phoenixville/" . $search . "/?page=1";
        
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT => 30,
            CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            CURLOPT_HTTPHEADER => [
                'Accept: text/html,application/xhtml+xml',
                'Accept-Language: en-US,en;q=0.9',
            ]
        ]);
        
        $html = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($httpCode !== 200 || !$html) {
            logMsg("  Failed to fetch Eventbrite for '$search' (HTTP $httpCode)");
            continue;
        }
        
        // Try to extract JSON-LD structured data first (most reliable)
        if (preg_match_all('/<script type="application\/ld\+json">(.*?)<\/script>/s', $html, $jsonMatches)) {
            foreach ($jsonMatches[1] as $jsonStr) {
                $data = json_decode($jsonStr, true);
                if (!$data) continue;
                
                // Handle array of events
                $items = isset($data['@type']) ? [$data] : (isset($data[0]) ? $data : []);
                
                foreach ($items as $item) {
                    if (($item['@type'] ?? '') !== 'Event') continue;
                    
                    $title = $item['name'] ?? '';
                    if (empty($title)) continue;
                    
                    $events[] = [
                        'title' => html_entity_decode($title),
                        'raw_date_string' => $item['startDate'] ?? '',
                        'loc' => $item['location']['name'] ?? ($item['location']['address']['addressLocality'] ?? 'Phoenixville Area'),
                        'type' => 'Eventbrite',
                        'link' => $item['url'] ?? '',
                        'img' => $item['image'] ?? '',
                        'desc' => mb_substr(strip_tags($item['description'] ?? ''), 0, 200),
                        'source' => 'eventbrite'
                    ];
                }
            }
        }
        
        // Fallback: parse HTML for event cards
        if (preg_match_all('/data-testid="event-card".*?<a[^>]*href="(https:\/\/www\.eventbrite\.com\/e\/[^"]*)"[^>]*>.*?<h3[^>]*>(.*?)<\/h3>.*?<p[^>]*>(.*?)<\/p>/s', $html, $cardMatches, PREG_SET_ORDER)) {
            foreach ($cardMatches as $match) {
                $title = strip_tags(html_entity_decode($match[2]));
                if (empty($title)) continue;
                
                // Check if we already have this event
                $isDupe = false;
                foreach ($events as $existing) {
                    if (mb_strtolower(trim($existing['title'])) === mb_strtolower(trim($title))) {
                        $isDupe = true;
                        break;
                    }
                }
                if ($isDupe) continue;
                
                $events[] = [
                    'title' => $title,
                    'raw_date_string' => strip_tags(html_entity_decode($match[3])),
                    'loc' => 'Phoenixville Area',
                    'type' => 'Eventbrite',
                    'link' => $match[1],
                    'img' => '',
                    'desc' => '',
                    'source' => 'eventbrite'
                ];
            }
        }
        
        logMsg("  Found " . count($events) . " events so far from '$search'");
        
        // Be nice to Eventbrite
        usleep(500000); // 0.5 second delay between requests
    }
    
    // Deduplicate
    $seen = [];
    $unique = [];
    foreach ($events as $ev) {
        $key = mb_strtolower(trim($ev['title']));
        if (isset($seen[$key])) continue;
        $seen[$key] = true;
        $unique[] = $ev;
    }
    
    logMsg("  Total unique Eventbrite events: " . count($unique));
    
    // Cache results
    if (count($unique) > 0) {
        file_put_contents($cacheFile, json_encode($unique, JSON_PRETTY_PRINT));
        logMsg("  Cached " . count($unique) . " Eventbrite events");
    } else {
        logMsg("  No events found, using cache if available");
        if (file_exists($cacheFile)) {
            $unique = json_decode(file_get_contents($cacheFile), true) ?: [];
            logMsg("  Loaded " . count($unique) . " events from cache");
        }
    }
    
    return $unique;
}
