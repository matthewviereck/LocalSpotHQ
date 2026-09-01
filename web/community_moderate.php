<?php
/**
 * community_moderate.php - approve or bin community board posts.
 *
 * Auth is a single shared secret read from a file ABOVE the docroot:
 *
 *     ~/domains/localspothq.com/community_token.txt      (one line, the token)
 *
 * If that file is missing or empty, moderation is DISABLED rather than open.
 * Failing closed matters here: this endpoint is the only thing standing
 * between the pending queue and the public board.
 *
 *     community_moderate.php?token=<secret>
 *
 * Deliberately not a login system. One person moderates this board; a session
 * layer would add password resets, cookies and lockout logic to protect a
 * single button, and every one of those is a bug surface.
 */

declare(strict_types=1);

// TWO levels up, not one. These scripts are deployed INTO the area directory
// (public_html/<area>/), so dirname(__DIR__) is public_html itself - the
// docroot. submit_event.php uses dirname(__DIR__) correctly because it sits at
// the docroot root; copying that expression down here put the store, and the
// moderation token, inside the web root.
$DATA_DIR = dirname(dirname(__DIR__));

// Refuse to run if the store still resolves inside the docroot.
if (is_dir($DATA_DIR . '/public_html') === false) {
    http_response_code(500);
    exit('Storage path misconfigured; refusing to start.');
}
$APPROVED_FILE = $DATA_DIR . '/community_posts.json';
$PENDING_FILE  = $DATA_DIR . '/community_pending.json';
$TOKEN_FILE    = $DATA_DIR . '/community_token.txt';

function load_json(string $p): array {
    if (!file_exists($p)) return [];
    $d = json_decode((string)file_get_contents($p), true);
    return is_array($d) ? $d : [];
}
function save_json(string $p, array $d): bool {
    $tmp = $p . '.tmp';
    if (file_put_contents($tmp, json_encode($d, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX) === false) return false;
    return rename($tmp, $p);
}
function e(?string $s): string {
    return htmlspecialchars((string)$s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/* ------------------------------------------------------------------ auth */

$expected = is_readable($TOKEN_FILE) ? trim((string)file_get_contents($TOKEN_FILE)) : '';
$given    = (string)($_GET['token'] ?? $_POST['token'] ?? '');

if ($expected === '') {
    http_response_code(503);
    exit('Moderation is not configured. Create community_token.txt above the docroot.');
}
// hash_equals: constant-time, so the token can't be recovered by timing.
if (!hash_equals($expected, $given)) {
    http_response_code(403);
    exit('Nope.');
}

/* ---------------------------------------------------------------- action */

$msg = null;
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $id     = (string)($_POST['id'] ?? '');
    $action = (string)($_POST['do'] ?? '');
    $pending = load_json($PENDING_FILE);
    $keep = [];
    $hit = null;
    foreach ($pending as $p) {
        if (($p['id'] ?? '') === $id && $hit === null) { $hit = $p; continue; }
        $keep[] = $p;
    }
    if ($hit === null) {
        $msg = 'That post is no longer in the queue.';
    } elseif ($action === 'approve') {
        $approved = load_json($APPROVED_FILE);
        $hit['status'] = 'approved';
        $hit['approved_at'] = date('c');
        unset($hit['ip']);           // no reason to keep it once published
        $approved[] = $hit;
        save_json($APPROVED_FILE, $approved);
        save_json($PENDING_FILE, $keep);
        $msg = 'Approved and live.';
    } elseif ($action === 'reject') {
        save_json($PENDING_FILE, $keep);
        $msg = 'Binned.';
    }
}

$pending  = load_json($PENDING_FILE);
$approved = load_json($APPROVED_FILE);
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Moderate the board</title>
<link rel="stylesheet" href="localspot.css">
<style>
  .mod { max-width: 720px; margin: 0 auto; padding: 24px 16px 64px; }
  .queue-item { margin-bottom: 14px; }
  .actions { display: flex; gap: 8px; margin-top: 10px; }
  .src { font-size: 12px; color: var(--ink-faint); margin-top: 8px; font-family: ui-monospace, monospace; }
</style>
</head>
<body>
<div class="mod">
  <h1>Moderation queue</h1>
  <p class="lede" style="margin-top:6px;">
    <?= count($pending) ?> waiting &middot; <?= count($approved) ?> live
  </p>

  <?php if ($msg): ?>
    <p class="notice" style="background:var(--good-wash);color:var(--good);border:1px solid var(--good);
       border-radius:var(--radius);padding:10px 13px;margin:16px 0;"><?= e($msg) ?></p>
  <?php endif; ?>

  <?php if (!$pending): ?>
    <div class="empty" style="margin-top:24px;">
      <strong>Queue is empty</strong>
      Nothing waiting for review.
    </div>
  <?php else: ?>
    <div style="margin-top:22px;">
      <?php foreach (array_reverse($pending) as $p): ?>
        <div class="post queue-item">
          <div class="post-head">
            <span class="post-author"><?= e($p['author'] ?? 'A neighbour') ?></span>
            <span><?= e($p['submitted'] ?? '') ?></span>
            <?php if (!empty($p['topic'])): ?>
              <span class="chip chip-good"><?= e($p['topic']) ?></span>
            <?php endif; ?>
          </div>
          <p class="post-body"><?= nl2br(e($p['body'] ?? '')) ?></p>
          <p class="src">ip <?= e($p['ip'] ?? '?') ?> &middot; id <?= e($p['id'] ?? '?') ?></p>
          <div class="actions">
            <form method="post" style="display:inline;">
              <input type="hidden" name="token" value="<?= e($given) ?>">
              <input type="hidden" name="id" value="<?= e($p['id'] ?? '') ?>">
              <button class="btn btn-primary btn-sm" name="do" value="approve" type="submit">Approve</button>
            </form>
            <form method="post" style="display:inline;"
                  onsubmit="return confirm('Bin this post permanently?');">
              <input type="hidden" name="token" value="<?= e($given) ?>">
              <input type="hidden" name="id" value="<?= e($p['id'] ?? '') ?>">
              <button class="btn btn-sm" name="do" value="reject" type="submit">Bin</button>
            </form>
          </div>
        </div>
      <?php endforeach; ?>
    </div>
  <?php endif; ?>
</div>
</body>
</html>
