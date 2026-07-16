<?php
// unsubscribe.php - one-click removal from the LocalSpot weekly list.
// Links in the digest carry ?e=<email>&t=md5(lowercase-email + salt); the
// salt lives next to subscribers.json, one level above the docroot.

$domainDir = dirname(__DIR__);
$subsFile = $domainDir . '/subscribers.json';
$saltFile = $domainDir . '/.subscribe_salt';

function respond($title, $message) {
    http_response_code(200);
    echo "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>{$title} - LocalSpot</title></head>"
        . "<body style=\"font-family:-apple-system,Segoe UI,Arial,sans-serif;color:#0f172a;max-width:480px;margin:80px auto;padding:0 16px;text-align:center;\">"
        . "<h2>{$title}</h2><p style=\"color:#64748b;\">{$message}</p>"
        . "<p><a href=\"https://www.localspothq.com/\" style=\"color:#1d4ed8;font-weight:bold;\">Back to LocalSpot</a></p></body></html>";
    exit;
}

$email = trim($_GET['e'] ?? '');
$token = trim($_GET['t'] ?? '');

if (!filter_var($email, FILTER_VALIDATE_EMAIL) || !$token || !file_exists($saltFile)) {
    respond('Invalid link', 'This unsubscribe link is incomplete or expired.');
}

$salt = trim(file_get_contents($saltFile));
if (!hash_equals(md5(strtolower($email) . $salt), $token)) {
    respond('Invalid link', 'This unsubscribe link is incomplete or expired.');
}

$subs = file_exists($subsFile) ? (json_decode(file_get_contents($subsFile), true) ?: []) : [];
$before = count($subs);
$subs = array_values(array_filter($subs, function ($s) use ($email) {
    return strcasecmp($s['email'] ?? '', $email) !== 0;
}));

if (count($subs) < $before) {
    file_put_contents($subsFile, json_encode($subs, JSON_PRETTY_PRINT), LOCK_EX);
}

respond('Unsubscribed', htmlspecialchars($email) . ' will no longer receive the LocalSpot weekly.');
