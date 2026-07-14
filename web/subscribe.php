<?php
// subscribe.php - stores weekly-email signups from the area apps.
// Deployed to the docroot root by deploy/auto_update.php (and the GitHub
// Actions workflow), so the apps can POST to /subscribe.php from any area.
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => 'POST required']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
$email = filter_var(trim($input['email'] ?? ''), FILTER_VALIDATE_EMAIL);

if (!$email || strlen($email) > 254) {
    echo json_encode(['success' => false, 'error' => 'Invalid email address']);
    exit;
}

// One level ABOVE the docroot so the list is never web-fetchable.
$file = dirname(__DIR__) . '/subscribers.json';
$subs = file_exists($file) ? (json_decode(file_get_contents($file), true) ?: []) : [];

foreach ($subs as $s) {
    if (strcasecmp($s['email'], $email) === 0) {
        echo json_encode(['success' => true]); // already subscribed - treat as success
        exit;
    }
}

if (count($subs) >= 50000) {
    echo json_encode(['success' => false, 'error' => 'List is full']);
    exit;
}

$subs[] = [
    'email' => $email,
    'source' => mb_substr(strip_tags($input['source'] ?? 'app'), 0, 50),
    'date' => date('Y-m-d H:i:s')
];

if (file_put_contents($file, json_encode($subs, JSON_PRETTY_PRINT), LOCK_EX) === false) {
    echo json_encode(['success' => false, 'error' => 'Could not save']);
    exit;
}

echo json_encode(['success' => true]);
