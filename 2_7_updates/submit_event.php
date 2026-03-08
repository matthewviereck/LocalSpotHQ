<?php
// submit_event.php - Handles community event submissions
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => 'POST required']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);

if (!$input || empty($input['name']) || empty($input['date']) || empty($input['location'])) {
    echo json_encode(['success' => false, 'error' => 'Missing required fields']);
    exit;
}

// Sanitize inputs
$event = [
    'id' => uniqid('sub_'),
    'type' => htmlspecialchars($input['type'] ?? 'Other'),
    'name' => htmlspecialchars($input['name']),
    'date' => htmlspecialchars($input['date']),
    'time' => htmlspecialchars($input['time'] ?? ''),
    'location' => htmlspecialchars($input['location']),
    'description' => htmlspecialchars($input['description'] ?? ''),
    'link' => filter_var($input['link'] ?? '', FILTER_SANITIZE_URL),
    'contactName' => htmlspecialchars($input['contactName'] ?? ''),
    'contactEmail' => filter_var($input['contactEmail'] ?? '', FILTER_SANITIZE_EMAIL),
    'recurring' => !empty($input['recurring']),
    'recurringPattern' => htmlspecialchars($input['recurringPattern'] ?? ''),
    'submitted' => date('Y-m-d H:i:s'),
    'status' => 'pending'
];

// Save to submissions file
$submissionsFile = __DIR__ . '/submissions.json';
$submissions = [];
if (file_exists($submissionsFile)) {
    $submissions = json_decode(file_get_contents($submissionsFile), true) ?: [];
}
$submissions[] = $event;
file_put_contents($submissionsFile, json_encode($submissions, JSON_PRETTY_PRINT));

// Send email notification
$to = 'contact@localspothq.com';
$subject = 'New Event Submission: ' . $event['name'];
$message = "New event submitted to LocalSpot!\n\n";
$message .= "Event: " . $event['name'] . "\n";
$message .= "Type: " . $event['type'] . "\n";
$message .= "Date: " . $event['date'] . "\n";
$message .= "Time: " . $event['time'] . "\n";
$message .= "Location: " . $event['location'] . "\n";
$message .= "Description: " . $event['description'] . "\n";
$message .= "Link: " . $event['link'] . "\n";
$message .= "Contact: " . $event['contactName'] . " (" . $event['contactEmail'] . ")\n";
if ($event['recurring']) {
    $message .= "Recurring: " . $event['recurringPattern'] . "\n";
}
$message .= "\n---\nReview submissions at: submissions.json\n";

$headers = "From: noreply@localspothq.com\r\n";
$headers .= "Reply-To: " . ($event['contactEmail'] ?: 'contact@localspothq.com') . "\r\n";

@mail($to, $subject, $message, $headers);

// Log it
$logFile = __DIR__ . '/logs/submissions.log';
$logDir = dirname($logFile);
if (!is_dir($logDir)) mkdir($logDir, 0755, true);
file_put_contents($logFile, date('Y-m-d H:i:s') . " - New submission: " . $event['name'] . "\n", FILE_APPEND);

echo json_encode(['success' => true, 'id' => $event['id']]);
