<?php
/**
 * send_digest.php - "LocalSpot weekly" digest email.
 *
 * Standalone so it survives the eventual retirement of auto_update.php:
 * reads the DEPLOYED site's eventsData (no scraping, no build), composes a
 * Fri-Sun digest, and mails every subscriber with a tokenized unsubscribe
 * link. Idempotent per ISO week via a marker file.
 *
 * Invoked two ways:
 *   - require'd by auto_update.php on Fridays (current setup)
 *   - directly by its own weekly cron after cutover:
 *     0 12 * * 5 /usr/bin/php /home/u277879645/localspot/deploy/send_digest.php >> /home/u277879645/localspot/logs/digest.log 2>&1
 */

$DIGEST_HOME = '/home/u277879645';
$DIGEST_DOMAIN_DIR = $DIGEST_HOME . '/domains/localspothq.com';
$DIGEST_SITE_HTML = $DIGEST_DOMAIN_DIR . '/public_html/phoenixville/index.html';
$DIGEST_SUBS_FILE = $DIGEST_DOMAIN_DIR . '/subscribers.json';
$DIGEST_SALT_FILE = $DIGEST_DOMAIN_DIR . '/.subscribe_salt';
$DIGEST_MARKER = $DIGEST_HOME . '/localspot/logs/.last_digest_week';
$DIGEST_SITE_URL = 'https://www.localspothq.com/phoenixville/';

if (!function_exists('digestLog')) {
    function digestLog($msg) {
        if (function_exists('logMsg')) { logMsg($msg); }
        else { echo '[' . date('Y-m-d H:i:s') . "] {$msg}\n"; }
    }
}

function digestSalt($saltFile) {
    if (!file_exists($saltFile)) {
        file_put_contents($saltFile, bin2hex(random_bytes(16)), LOCK_EX);
        @chmod($saltFile, 0600);
    }
    return trim(file_get_contents($saltFile));
}

function sendWeeklyDigest() {
    global $DIGEST_SITE_HTML, $DIGEST_SUBS_FILE, $DIGEST_SALT_FILE, $DIGEST_MARKER, $DIGEST_SITE_URL;

    $week = date('o-W'); // ISO year-week
    if (file_exists($DIGEST_MARKER) && trim(file_get_contents($DIGEST_MARKER)) === $week) {
        digestLog('Digest: already sent for week ' . $week);
        return;
    }

    $subs = file_exists($DIGEST_SUBS_FILE)
        ? (json_decode(file_get_contents($DIGEST_SUBS_FILE), true) ?: []) : [];
    if (!$subs) { digestLog('Digest: no subscribers yet'); return; }

    $html = @file_get_contents($DIGEST_SITE_HTML);
    if (!$html || !preg_match('/const eventsData = (\[[\s\S]*?\]);/', $html, $m)) {
        digestLog('Digest: could not read eventsData from deployed site');
        return;
    }
    $events = json_decode($m[1], true) ?: [];

    // Upcoming Fri-Sun window (in the server's local time, same as the build)
    $today = new DateTime('today');
    $dow = (int)$today->format('w'); // 0=Sun .. 6=Sat
    $friOffset = $dow === 0 ? -2 : ($dow === 6 ? -1 : 5 - $dow);
    $friday = (clone $today)->modify(($friOffset >= 0 ? '+' : '') . $friOffset . ' days');
    $sunday = (clone $friday)->modify('+2 days');

    $weekend = array_values(array_filter($events, function ($ev) use ($friday, $sunday, $today) {
        if (!isset($ev['_sort_date']) || $ev['_sort_date'] == 9999999999) return false;
        $d = (new DateTime('@' . $ev['_sort_date']))->setTime(12, 0);
        return $d >= max($friday, $today) && $d <= $sunday;
    }));
    if (!$weekend) { digestLog('Digest: no weekend events - skipping this week'); return; }
    usort($weekend, function ($a, $b) { return $a['_sort_date'] - $b['_sort_date']; });
    $weekend = array_slice($weekend, 0, 12);

    $rangeLabel = $friday->format('M j') . '-' . $sunday->format('j');
    $rows = '';
    foreach ($weekend as $ev) {
        $title = htmlspecialchars($ev['title']);
        $loc = htmlspecialchars($ev['loc'] ?? '');
        $date = htmlspecialchars($ev['date'] ?? '');
        $link = filter_var($ev['link'] ?? '', FILTER_VALIDATE_URL) ?: $DIGEST_SITE_URL;
        $rows .= "<tr><td style=\"padding:10px 0;border-bottom:1px solid #e2e8f0;\">"
            . "<a href=\"{$link}\" style=\"color:#1d4ed8;font-weight:bold;text-decoration:none;\">{$title}</a><br>"
            . "<span style=\"color:#64748b;font-size:13px;\">{$date} &middot; {$loc}</span></td></tr>";
    }

    $salt = digestSalt($DIGEST_SALT_FILE);
    $sent = 0;
    foreach ($subs as $s) {
        $email = $s['email'] ?? '';
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) continue;
        $token = md5(strtolower($email) . $salt);
        $unsub = 'https://www.localspothq.com/unsubscribe.php?e=' . urlencode($email) . '&t=' . $token;
        $body = "<!doctype html><html><body style=\"font-family:-apple-system,Segoe UI,Arial,sans-serif;color:#0f172a;max-width:560px;margin:0 auto;padding:16px;\">"
            . "<a href=\"{$DIGEST_SITE_URL}\"><img src=\"{$DIGEST_SITE_URL}weekend-card.png\" alt=\"This weekend in Phoenixville\" style=\"width:100%;border-radius:12px;margin-bottom:12px;\"></a>"
            . "<h2 style=\"margin:0 0 4px;\">This weekend in Phoenixville</h2>"
            . "<p style=\"color:#64748b;margin:0 0 16px;\">{$rangeLabel} &middot; picked from <a href=\"{$DIGEST_SITE_URL}\" style=\"color:#1d4ed8;\">LocalSpot</a></p>"
            . "<table style=\"width:100%;border-collapse:collapse;\">{$rows}</table>"
            . "<p style=\"margin:20px 0 0;\"><a href=\"{$DIGEST_SITE_URL}\" style=\"color:#1d4ed8;font-weight:bold;\">See everything happening &rarr;</a></p>"
            . "<p style=\"color:#94a3b8;font-size:12px;margin-top:28px;\">You signed up for the LocalSpot weekly on localspothq.com. "
            . "<a href=\"{$unsub}\" style=\"color:#94a3b8;\">Unsubscribe</a></p>"
            . "</body></html>";
        $headers = "MIME-Version: 1.0\r\nContent-Type: text/html; charset=UTF-8\r\n"
            . "From: LocalSpot <noreply@localspothq.com>\r\n"
            . "List-Unsubscribe: <{$unsub}>";
        if (@mail($email, "This weekend in Phoenixville ({$rangeLabel})", $body, $headers)) {
            $sent++;
        }
    }

    file_put_contents($DIGEST_MARKER, $week);
    digestLog("Digest: sent to {$sent}/" . count($subs) . ' subscribers (' . count($weekend) . ' events)');
}

// Run immediately when invoked directly (not require'd by auto_update.php)
if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === realpath(__FILE__)) {
    sendWeeklyDigest();
}
