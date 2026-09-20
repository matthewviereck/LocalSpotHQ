<?php
// promote_webhook.php - Stripe webhook for "Promote this event".
//
// Deployed to the docroot root by build-deploy.yml, next to subscribe.php.
// Stripe POSTs checkout.session.completed here. A verified, paid session whose
// client_reference_id is "<area-slug>__<event-slug>" (set by the promote page)
// becomes a row in two files:
//   ../promoted_log.json   private, one level above the docroot: every purchase
//                          ever, with the payer's email and the Stripe session id
//   ./promoted.json        public: the pins, {area, slug, from, until}
// The app and the Thursday digest read the public file and filter by date
// themselves, because this file is only rewritten when the next purchase lands.
//
// Secret: ../.stripe_webhook_secret holds the "whsec_..." signing secret from
// Stripe > Developers > Webhooks. Fails closed with 503 while it is absent.
// PROMOTE_DAYS must match "days" in config/promote.json.

const PROMOTE_DAYS = 7;
const OWNER_EMAIL = 'matthewviereck@gmail.com';
const TOLERANCE_SECONDS = 300;

header('Content-Type: application/json');

$secretFile = dirname(__DIR__) . '/.stripe_webhook_secret';
$logFile    = dirname(__DIR__) . '/promoted_log.json';
$publicFile = __DIR__ . '/promoted.json';

function finish($code, $message) {
    http_response_code($code);
    echo json_encode(['ok' => $code < 400, 'message' => $message]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') finish(405, 'POST required');
if (!file_exists($secretFile)) finish(503, 'webhook secret not configured');

$secret  = trim(file_get_contents($secretFile));
$payload = file_get_contents('php://input');
$header  = $_SERVER['HTTP_STRIPE_SIGNATURE'] ?? '';

// Stripe-Signature: t=<unix>,v1=<hmac>[,v1=<hmac>]
$ts = 0; $sigs = [];
foreach (explode(',', $header) as $part) {
    $kv = explode('=', trim($part), 2);
    if (count($kv) !== 2) continue;
    if ($kv[0] === 't') $ts = (int)$kv[1];
    elseif ($kv[0] === 'v1') $sigs[] = $kv[1];
}
if (!$ts || !$sigs) finish(400, 'missing signature');
if (abs(time() - $ts) > TOLERANCE_SECONDS) finish(400, 'stale signature');
$expected = hash_hmac('sha256', $ts . '.' . $payload, $secret);
$valid = false;
foreach ($sigs as $s) { if (hash_equals($expected, $s)) { $valid = true; break; } }
if (!$valid) finish(400, 'bad signature');

$event = json_decode($payload, true);
if (!$event || ($event['type'] ?? '') !== 'checkout.session.completed') finish(200, 'ignored');
$session = $event['data']['object'] ?? [];
if (($session['payment_status'] ?? '') !== 'paid') finish(200, 'not paid');

$ref = (string)($session['client_reference_id'] ?? '');
if (!preg_match('/^([a-z0-9-]+)__([a-z0-9-]+)$/', $ref, $m)) finish(200, 'no event reference');
$area = $m[1];
$slug = $m[2];
$sessionId = (string)($session['id'] ?? '');

$log = file_exists($logFile) ? (json_decode(file_get_contents($logFile), true) ?: []) : [];
foreach ($log as $row) {
    if (($row['session'] ?? '') === $sessionId) finish(200, 'already recorded');
}

$from  = new DateTime('today');
$until = (clone $from)->modify('+' . (PROMOTE_DAYS - 1) . ' days'); // inclusive: today counts
$custom = [];
foreach (($session['custom_fields'] ?? []) as $cf) {
    $key = $cf['key'] ?? '';
    $custom[$key] = $cf['text']['value'] ?? ($cf['dropdown']['value'] ?? ($cf['numeric']['value'] ?? ''));
}
$row = [
    'session'  => $sessionId,
    'area'     => $area,
    'slug'     => $slug,
    'paid_at'  => date('Y-m-d H:i:s'),
    'from'     => $from->format('Y-m-d'),
    'until'    => $until->format('Y-m-d'),
    'email'    => $session['customer_details']['email'] ?? '',
    'amount'   => $session['amount_total'] ?? null,
    'currency' => $session['currency'] ?? '',
    'custom'   => $custom,
];
$log[] = $row;
if (file_put_contents($logFile, json_encode($log, JSON_PRETTY_PRINT), LOCK_EX) === false) finish(500, 'could not write log');
@chmod($logFile, 0600);

$today = date('Y-m-d');
$active = [];
foreach ($log as $r) {
    if (($r['until'] ?? '') >= $today) {
        $active[] = ['area' => $r['area'], 'slug' => $r['slug'], 'from' => $r['from'] ?? '', 'until' => $r['until']];
    }
}
file_put_contents($publicFile, json_encode($active), LOCK_EX);

@mail(
    OWNER_EMAIL,
    "LocalSpot: event promoted in {$area}",
    "Event: https://www.localspothq.com/{$area}/events/{$slug}/\n"
        . "Pinned {$row['from']} to {$row['until']}\n"
        . "Buyer: {$row['email']}\n"
        . 'Amount: ' . (is_int($row['amount']) ? number_format($row['amount'] / 100, 2) : '?') . ' ' . strtoupper($row['currency']) . "\n"
        . "Facebook post still to do (that part is by hand).\n",
    'From: noreply@localspothq.com'
);

finish(200, 'recorded');
