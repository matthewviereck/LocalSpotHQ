<?php
/**
 * send_digest.php - the Thursday email: "This week in <Area>".
 *
 * Runs ON THE SERVER, because subscribers.json never leaves Hostinger, but is
 * TRIGGERED from GitHub Actions over SSH every Thursday morning
 * (.github/workflows/thursday-digest.yml). Shared hosting exposes no crontab
 * to this account and the hPanel cron was never re-created after the 2026-07
 * cutover, which is why zero digests had ever gone out when this was checked
 * on 2026-09-20. build-deploy.yml copies this file to
 * ~/domains/localspothq.com/scripts/send_digest.php on every deploy.
 *
 * Sends go through web/mailer.php (authenticated SMTP from a real mailbox);
 * PHP mail() on this host accepts everything and delivers nothing.
 *
 * Per area it:
 *   - reads the DEPLOYED site's eventsData (no scraping, no build)
 *   - takes the next 7 days, with promoted pins (/promoted.json) first
 *   - mails every subscriber routed to that area, tokenized unsubscribe link
 *   - is idempotent per area per ISO week via a marker file
 *
 * Flags:
 *   --dry-run       render each area to logs/digest-preview-<area>.html, send nothing
 *   --to=<email>    send one copy per area to that address only (a real test); no marker
 *   --area=<slug>   restrict to one area
 */

$HOME_DIR   = getenv('HOME') ?: '/home/u277879645';
$DOMAIN_DIR = $HOME_DIR . '/domains/localspothq.com';
$DOCROOT    = $DOMAIN_DIR . '/public_html';
$SUBS_FILE  = $DOMAIN_DIR . '/subscribers.json';
$SALT_FILE  = $DOMAIN_DIR . '/.subscribe_salt';
$LOG_DIR    = $DOMAIN_DIR . '/logs';
$MARKER     = $LOG_DIR . '/.last_digest_week';
$PROMOTED   = $DOCROOT . '/promoted.json';
$SITE       = 'https://www.localspothq.com/';
$PRICE      = '$19';
$MAX_ROWS   = 18;
$WINDOW_DAYS = 7;

// The only sender that delivers on this host (see web/mailer.php).
require_once $DOCROOT . '/mailer.php';

// Subscribers are routed by the `source` subscribe.php stored: the app posts
// the area name, event pages post "event-page:<area-slug>", the promote page
// posts "promote:<event-slug>". Anything unmatched (the legacy "app") goes to
// the first area.
$AREAS = [
    ['slug' => 'phoenixville', 'name' => 'Phoenixville', 'aliases' => ['phoenixville']],
    ['slug' => 'west-chester', 'name' => 'West Chester', 'aliases' => ['west-chester', 'west_chester', 'west chester']],
];

$opts = ['dry-run' => false, 'to' => '', 'area' => ''];
foreach (array_slice($argv ?? [], 1) as $arg) {
    if ($arg === '--dry-run') $opts['dry-run'] = true;
    elseif (strpos($arg, '--to=') === 0) $opts['to'] = substr($arg, 5);
    elseif (strpos($arg, '--area=') === 0) $opts['area'] = substr($arg, 7);
}

@mkdir($LOG_DIR, 0755, true);

function digestLog($msg) {
    global $LOG_DIR;
    $line = '[' . date('Y-m-d H:i:s') . "] {$msg}\n";
    echo $line;
    @file_put_contents($LOG_DIR . '/digest.log', $line, FILE_APPEND | LOCK_EX);
}

function digestSalt($saltFile) {
    if (!file_exists($saltFile)) {
        file_put_contents($saltFile, bin2hex(random_bytes(16)), LOCK_EX);
        @chmod($saltFile, 0600);
    }
    return trim(file_get_contents($saltFile));
}

function loadEvents($docroot, $areaSlug) {
    $html = @file_get_contents("{$docroot}/{$areaSlug}/index.html");
    if (!$html || !preg_match('/const eventsData = (\[[\s\S]*?\]);/', $html, $m)) return null;
    return json_decode($m[1], true) ?: [];
}

function loadPromoted($file, $areaSlug, $today) {
    $rows = file_exists($file) ? (json_decode(file_get_contents($file), true) ?: []) : [];
    $live = [];
    foreach ($rows as $p) {
        if (($p['area'] ?? '') !== $areaSlug) continue;
        if (!empty($p['until']) && $p['until'] < $today) continue;
        if (!empty($p['from']) && $p['from'] > $today) continue;
        if (!empty($p['slug'])) $live[$p['slug']] = true;
    }
    return $live;
}

function routeSubscribers($subs, $areas) {
    $byArea = [];
    foreach ($areas as $a) $byArea[$a['slug']] = [];
    foreach ($subs as $s) {
        $email = $s['email'] ?? '';
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) continue;
        $src = strtolower($s['source'] ?? '');
        $target = $areas[0]['slug'];
        foreach ($areas as $a) {
            foreach ($a['aliases'] as $alias) {
                if ($alias !== '' && strpos($src, $alias) !== false) { $target = $a['slug']; break 2; }
            }
        }
        $byArea[$target][] = $email;
    }
    return $byArea;
}

function eventLink($site, $areaSlug, $ev) {
    if (!empty($ev['slug'])) return "{$site}{$areaSlug}/events/" . rawurlencode($ev['slug']) . '/';
    $link = filter_var($ev['link'] ?? '', FILTER_VALIDATE_URL);
    return $link ?: "{$site}{$areaSlug}/";
}

function rowHtml($site, $areaSlug, $ev, $promoted = false) {
    $title = htmlspecialchars($ev['title'] ?? '');
    $bits = array_filter([$ev['date'] ?? '', $ev['time'] ?? '', $ev['loc'] ?? '']);
    $meta = htmlspecialchars(implode(' · ', $bits));
    $link = eventLink($site, $areaSlug, $ev);
    $chip = $promoted
        ? '<span style="display:inline-block;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;'
          . 'background:#fde8d7;color:#b4470f;padding:2px 7px;border-radius:999px;margin-right:6px;">Promoted</span>'
        : '';
    return "<tr><td style=\"padding:10px 0;border-bottom:1px solid #e2e8f0;\">"
        . "{$chip}<a href=\"{$link}\" style=\"color:#1d4ed8;font-weight:bold;text-decoration:none;\">{$title}</a><br>"
        . "<span style=\"color:#64748b;font-size:13px;\">{$meta}</span></td></tr>";
}

function buildDigest($area, $events, $promotedSlugs, $site, $price, $maxRows, $windowDays) {
    $today = new DateTime('today');
    $end = (clone $today)->modify('+' . ($windowDays - 1) . ' days');
    $startTs = $today->getTimestamp();
    $endTs = (clone $end)->setTime(23, 59, 59)->getTimestamp();

    $pinned = []; $dated = []; $ongoing = [];
    foreach ($events as $ev) {
        $ts = $ev['_sort_date'] ?? null;
        $slug = $ev['slug'] ?? '';
        if ($slug && isset($promotedSlugs[$slug])) { $pinned[] = $ev; continue; }
        if (!is_numeric($ts) || $ts >= 9000000000) continue;
        if ($ts >= $startTs && $ts <= $endTs) $dated[] = $ev;
        elseif ($ts < $startTs && !empty($ev['ongoing'])) $ongoing[] = $ev;
    }
    usort($dated, function ($a, $b) { return $a['_sort_date'] <=> $b['_sort_date']; });
    $list = array_slice(array_merge($dated, $ongoing), 0, max(0, $maxRows - count($pinned)));
    if (!$pinned && !$list) return null;

    $areaSlug = $area['slug']; $name = $area['name'];
    $rangeLabel = $today->format('M j') . '-' . ($today->format('M') === $end->format('M') ? $end->format('j') : $end->format('M j'));
    $rows = '';
    foreach ($pinned as $ev) $rows .= rowHtml($site, $areaSlug, $ev, true);
    foreach ($list as $ev) $rows .= rowHtml($site, $areaSlug, $ev);

    $areaUrl = "{$site}{$areaSlug}/";
    $body = "<!doctype html><html><body style=\"font-family:-apple-system,Segoe UI,Arial,sans-serif;color:#0f172a;max-width:560px;margin:0 auto;padding:16px;\">"
        . "<h2 style=\"margin:0 0 4px;\">This week in " . htmlspecialchars($name) . "</h2>"
        . "<p style=\"color:#64748b;margin:0 0 16px;\">{$rangeLabel} &middot; picked from <a href=\"{$areaUrl}\" style=\"color:#1d4ed8;\">LocalSpot</a></p>"
        . "<table style=\"width:100%;border-collapse:collapse;\">{$rows}</table>"
        . "<p style=\"margin:20px 0 0;\"><a href=\"{$areaUrl}\" style=\"color:#1d4ed8;font-weight:bold;\">See everything happening &rarr;</a>"
        . " &nbsp;&middot;&nbsp; <a href=\"{$areaUrl}this-weekend/\" style=\"color:#1d4ed8;\">Just the weekend</a></p>"
        . "<p style=\"color:#64748b;font-size:13px;margin-top:24px;padding-top:14px;border-top:1px solid #e2e8f0;\">"
        . "Running something in " . htmlspecialchars($name) . "? <a href=\"{$areaUrl}promote/\" style=\"color:#1d4ed8;\">Promote it for {$price} a week</a>"
        . " or <a href=\"{$site}submit.html\" style=\"color:#1d4ed8;\">add a free listing</a>.</p>"
        . "<p style=\"color:#94a3b8;font-size:12px;margin-top:20px;\">You signed up for the LocalSpot " . htmlspecialchars($name) . " email on localspothq.com. "
        . "<a href=\"{{UNSUB}}\" style=\"color:#94a3b8;\">Unsubscribe</a></p>"
        . "</body></html>";

    return [
        'subject' => "This week in {$name} ({$rangeLabel})",
        'body' => $body,
        'count' => count($pinned) + count($list),
        'pinned' => count($pinned),
    ];
}

function sendDigest($areas, $opts) {
    global $DOCROOT, $SUBS_FILE, $SALT_FILE, $LOG_DIR, $MARKER, $PROMOTED, $SITE, $PRICE, $MAX_ROWS, $WINDOW_DAYS;

    $week = date('o-W');
    $today = date('Y-m-d');
    $sentWeeks = file_exists($MARKER) ? (json_decode(file_get_contents($MARKER), true) ?: []) : [];
    $subs = file_exists($SUBS_FILE) ? (json_decode(file_get_contents($SUBS_FILE), true) ?: []) : [];
    $byArea = routeSubscribers($subs, $areas);
    $salt = digestSalt($SALT_FILE);
    $testOnly = $opts['to'] !== '';
    $dry = $opts['dry-run'];
    if (!localspot_smtp_config()) {
        digestLog('SMTP not configured (.smtp.json missing above the docroot): PHP mail() on this host delivers nothing, so sends will not arrive');
    }

    foreach ($areas as $area) {
        $slug = $area['slug'];
        if ($opts['area'] !== '' && $opts['area'] !== $slug) continue;
        $recipients = $testOnly ? [$opts['to']] : ($byArea[$slug] ?? []);

        if (!$dry && !$testOnly && ($sentWeeks[$slug] ?? '') === $week) {
            digestLog("{$slug}: already sent for week {$week}");
            continue;
        }
        if (!$dry && !$recipients) {
            digestLog("{$slug}: no subscribers routed here, nothing to send");
            continue;
        }
        $events = loadEvents($DOCROOT, $slug);
        if ($events === null) {
            digestLog("{$slug}: could not read eventsData from the deployed site");
            continue;
        }
        $promoted = loadPromoted($PROMOTED, $slug, $today);
        $digest = buildDigest($area, $events, $promoted, $SITE, $PRICE, $MAX_ROWS, $WINDOW_DAYS);
        if (!$digest) {
            digestLog("{$slug}: no events in the next {$WINDOW_DAYS} days, skipping this week");
            continue;
        }

        if ($dry) {
            $preview = "{$LOG_DIR}/digest-preview-{$slug}.html";
            file_put_contents($preview, str_replace('{{UNSUB}}', '#', $digest['body']));
            digestLog("{$slug}: DRY RUN, {$digest['count']} events ({$digest['pinned']} promoted), "
                . count($byArea[$slug] ?? []) . " subscribers, subject \"{$digest['subject']}\", preview {$preview}");
            continue;
        }

        $sent = 0;
        foreach ($recipients as $email) {
            $token = md5(strtolower($email) . $salt);
            $unsub = $SITE . 'unsubscribe.php?e=' . urlencode($email) . '&t=' . $token;
            $body = str_replace('{{UNSUB}}', $unsub, $digest['body']);
            if (localspot_mail($email, $digest['subject'], $body, 'LocalSpot ' . $area['name'],
                               ['List-Unsubscribe' => "<{$unsub}>", 'List-Unsubscribe-Post' => 'List-Unsubscribe=One-Click'])) $sent++;
        }
        digestLog("{$slug}: sent {$sent}/" . count($recipients) . " ({$digest['count']} events, {$digest['pinned']} promoted)"
            . ($testOnly ? ' [test copy only]' : ''));
        if (!$testOnly && $sent > 0) {
            $sentWeeks[$slug] = $week;
            file_put_contents($MARKER, json_encode($sentWeeks), LOCK_EX);
        }
    }
}

// Legacy entry point: auto_update.php used to require this file and call
// sendWeeklyDigest() on Fridays. Kept so that path still works if the hPanel
// cron is ever re-created; the marker keeps it from double-sending.
function sendWeeklyDigest() {
    global $AREAS;
    sendDigest($AREAS, ['dry-run' => false, 'to' => '', 'area' => '']);
}

if (PHP_SAPI === 'cli' && realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === realpath(__FILE__)) {
    sendDigest($AREAS, $opts);
}
