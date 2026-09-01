<?php
/**
 * community.php - LocalSpot community board.
 *
 * Moderated by design: a submission lands in a pending file and nothing is
 * public until it is approved in community_moderate.php. There are no accounts
 * and no passwords, which keeps the attack surface to "someone can fill in a
 * form" rather than "someone can create an identity".
 *
 * Storage follows the submit_event.php convention: JSON one level ABOVE the
 * docroot, so post bodies and submitter IPs are never web-fetchable. The
 * .htaccess also denies *.json in the docroot as a second line of defence.
 *
 *   GET  community.php?action=list[&limit=N]  -> JSON of approved posts
 *   GET  community.php                        -> the board page + post form
 *   POST community.php                        -> submit a post (to pending)
 */

declare(strict_types=1);

const MAX_BODY   = 1200;   // characters
const MAX_AUTHOR = 40;
const RATE_MAX   = 3;      // posts per IP...
const RATE_WINDOW = 3600;  // ...per hour
const MIN_FILL_SECONDS = 4; // a human takes longer than this to write a post

$AREA   = '{{AREA_NAME}}';
$TOPICS = ['Recommendation', 'Question', 'Heads-up', 'Lost & found', 'For sale', 'Thanks'];

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
$RATE_FILE     = $DATA_DIR . '/community_rate.json';

/* ---------------------------------------------------------------- helpers */

function load_json(string $path): array {
    if (!file_exists($path)) return [];
    $raw = file_get_contents($path);
    if ($raw === false || $raw === '') return [];
    $data = json_decode($raw, true);
    return is_array($data) ? $data : [];
}

function save_json(string $path, array $data): bool {
    $tmp = $path . '.tmp';
    $ok = file_put_contents($tmp, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
    if ($ok === false) return false;
    return rename($tmp, $path);   // atomic, so a crash mid-write can't truncate the board
}

function client_ip(): string {
    return $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
}

/** Coarse per-IP throttle. Not a security boundary — moderation is. */
function rate_limited(string $file): bool {
    $now = time();
    $log = load_json($file);
    $ip  = client_ip();
    $log = array_filter($log, fn($e) => ($e['t'] ?? 0) > $now - RATE_WINDOW);
    $mine = array_filter($log, fn($e) => ($e['ip'] ?? '') === $ip);
    if (count($mine) >= RATE_MAX) return true;
    $log[] = ['ip' => $ip, 't' => $now];
    save_json($file, array_values($log));
    return false;
}

function human_ago(string $iso): string {
    $t = strtotime($iso);
    if ($t === false) return '';
    $d = time() - $t;
    if ($d < 3600)  return max(1, (int)($d / 60)) . 'm ago';
    if ($d < 86400) return (int)($d / 3600) . 'h ago';
    if ($d < 604800) return (int)($d / 86400) . 'd ago';
    return date('M j', $t);
}

function e(?string $s): string {
    return htmlspecialchars((string)$s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/* ------------------------------------------------------------- JSON list  */

if (($_GET['action'] ?? '') === 'list') {
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: public, max-age=60');
    $limit = min(50, max(1, (int)($_GET['limit'] ?? 20)));
    $posts = array_slice(array_reverse(load_json($APPROVED_FILE)), 0, $limit);
    $out = array_map(fn($p) => [
        'author' => $p['author'] ?? 'A neighbour',
        'topic'  => $p['topic'] ?? '',
        'body'   => $p['body'] ?? '',
        'date'   => $p['approved_at'] ?? ($p['submitted'] ?? ''),
        'ago'    => human_ago($p['approved_at'] ?? ($p['submitted'] ?? '')),
    ], $posts);
    echo json_encode(['posts' => $out], JSON_UNESCAPED_UNICODE);
    exit;
}

/* ---------------------------------------------------------------- submit  */

$notice = null;
$error  = null;
$old    = ['author' => '', 'topic' => '', 'body' => ''];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Honeypot: a field hidden from people, irresistible to naive bots.
    $trap = trim((string)($_POST['website'] ?? ''));
    // Time trap: the render timestamp is echoed back in a hidden field.
    $started = (int)($_POST['t'] ?? 0);
    $elapsed = time() - $started;

    $author = trim((string)($_POST['author'] ?? ''));
    $topic  = trim((string)($_POST['topic'] ?? ''));
    $body   = trim((string)($_POST['body'] ?? ''));
    $old = ['author' => $author, 'topic' => $topic, 'body' => $body];

    if ($trap !== '' || $started <= 0 || $elapsed < MIN_FILL_SECONDS) {
        // Silent accept: telling a bot why it failed just helps it retry.
        $notice = 'Thanks - your post is in the queue.';
    } elseif ($body === '') {
        $error = 'Write something first.';
    } elseif (mb_strlen($body) > MAX_BODY) {
        $error = 'That is longer than ' . MAX_BODY . ' characters. Trim it a little.';
    } elseif ($topic !== '' && !in_array($topic, $TOPICS, true)) {
        $error = 'Pick one of the listed topics.';
    } elseif (rate_limited($RATE_FILE)) {
        $error = 'You have posted a few times just now. Try again in a little while.';
    } else {
        // Strip tags rather than escaping: the board is plain text only, so
        // there is never a reason to keep markup around to be escaped later.
        $post = [
            'id'        => bin2hex(random_bytes(8)),
            'author'    => mb_substr(strip_tags($author), 0, MAX_AUTHOR) ?: 'A neighbour',
            'topic'     => $topic,
            'body'      => mb_substr(strip_tags($body), 0, MAX_BODY),
            'area'      => $AREA,
            'ip'        => client_ip(),
            'submitted' => date('c'),
            'status'    => 'pending',
        ];
        $pending = load_json($PENDING_FILE);
        $pending[] = $post;
        save_json($PENDING_FILE, $pending);

        $to = 'contact@localspothq.com';
        @mail($to, 'LocalSpot board: new post awaiting review',
            "Area: {$AREA}\nFrom: {$post['author']}\nTopic: {$post['topic']}\n\n{$post['body']}\n\n"
            . "Approve or bin it in community_moderate.php\n",
            "From: noreply@localspothq.com\r\n");

        $notice = 'Thanks - your post is in the queue. It goes up once it has been read.';
        $old = ['author' => '', 'topic' => '', 'body' => ''];
    }
}

$posts = array_slice(array_reverse(load_json($APPROVED_FILE)), 0, 40);
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#14181f">
<title>Community board | LocalSpot <?= e($AREA) ?></title>
<meta name="description" content="The <?= e($AREA) ?> community board on LocalSpot: recommendations, questions and local heads-ups from neighbours.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://www.localspothq.com/{{AREA_SLUG}}/community.php">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&display=swap">
<link rel="stylesheet" href="localspot.css">
<style>
  .board { max-width: 680px; margin: 0 auto; padding: 0 16px 64px; }
  .board-head { padding: 26px 0 18px; }
  .backlink { font-family: var(--display); font-size: 13px; font-weight: 600;
              color: var(--ink-faint); text-decoration: none; }
  .backlink:hover { color: var(--ink); }
  .notice { border-radius: var(--radius); padding: 12px 14px; margin-bottom: 18px; font-size: 15px; }
  .notice-ok  { background: var(--good-wash); color: var(--good); border: 1px solid var(--good); }
  .notice-err { background: var(--now-wash);  color: var(--now);  border: 1px solid var(--now); }
  .rules { font-size: 13.5px; color: var(--ink-faint); margin: 10px 0 0; }
  .trap { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
</style>
</head>
<body>
<div class="board">

  <div class="board-head">
    <a class="backlink" href="./">&larr; LocalSpot <?= e($AREA) ?></a>
    <h1 style="margin-top:10px;">Community board</h1>
    <p class="lede" style="margin-top:8px;">
      Recommendations, questions, lost cats, things worth knowing.
      Every post is read before it goes up.
    </p>
  </div>

  <?php if ($notice): ?><div class="notice notice-ok"><?= e($notice) ?></div><?php endif; ?>
  <?php if ($error):  ?><div class="notice notice-err"><?= e($error) ?></div><?php endif; ?>

  <section id="post" style="margin-bottom:34px;">
    <div class="section-head"><h2>Post something</h2></div>
    <form method="post" action="community.php#post">
      <input type="hidden" name="t" value="<?= time() ?>">
      <div class="trap" aria-hidden="true">
        <label>Website<input type="text" name="website" tabindex="-1" autocomplete="off"></label>
      </div>

      <div class="field">
        <label for="author">Your name <span style="text-transform:none;letter-spacing:0;">(optional)</span></label>
        <input id="author" name="author" maxlength="<?= MAX_AUTHOR ?>"
               value="<?= e($old['author']) ?>" placeholder="A neighbour">
      </div>

      <div class="field">
        <label for="topic">Topic</label>
        <select id="topic" name="topic">
          <option value="">Choose one</option>
          <?php foreach ($TOPICS as $t): ?>
            <option value="<?= e($t) ?>" <?= $old['topic'] === $t ? 'selected' : '' ?>><?= e($t) ?></option>
          <?php endforeach; ?>
        </select>
      </div>

      <div class="field">
        <label for="body">Your post</label>
        <textarea id="body" name="body" maxlength="<?= MAX_BODY ?>" required
                  placeholder="What do you want to tell the town?"><?= e($old['body']) ?></textarea>
      </div>

      <button class="btn btn-primary" type="submit">Send for review</button>
      <p class="rules">
        Plain text only, <?= MAX_BODY ?> characters max. No links to anything you are selling,
        no abuse, no politics. Posts appear once approved.
      </p>
    </form>
  </section>

  <section>
    <div class="section-head"><h2>On the board</h2></div>
    <?php if (!$posts): ?>
      <div class="empty">
        <strong>The board is quiet</strong>
        Be the first to post something.
      </div>
    <?php else: ?>
      <div class="stack stack-md">
        <?php foreach ($posts as $p): ?>
          <div class="post">
            <div class="post-head">
              <span class="post-author"><?= e($p['author'] ?? 'A neighbour') ?></span>
              <span><?= e(human_ago($p['approved_at'] ?? ($p['submitted'] ?? ''))) ?></span>
              <?php if (!empty($p['topic'])): ?>
                <span class="chip chip-good"><?= e($p['topic']) ?></span>
              <?php endif; ?>
            </div>
            <p class="post-body"><?= nl2br(e($p['body'] ?? '')) ?></p>
          </div>
        <?php endforeach; ?>
      </div>
    <?php endif; ?>
  </section>

</div>
</body>
</html>
