<?php
// mailer.php - the one way LocalSpot sends email.
//
// PHP's mail() on this Hostinger account accepts every message and delivers
// none of them (tested 2026-09-20: digest copies and a control message from a
// real mailbox all vanished, no bounce, no log). So everything goes out over
// authenticated SMTP from a real mailbox on the domain, which Hostinger also
// DKIM-signs. Credentials live one level above the docroot in .smtp.json:
//
//   {"host": "smtp.hostinger.com", "port": 465,
//    "user": "hello@localspothq.com", "pass": "...",
//    "from": "hello@localspothq.com", "from_name": "LocalSpot"}
//
// Without that file localspot_mail() falls back to mail() so nothing fatals,
// and returns false so callers can log "not configured".
//
// Deployed to the docroot by build-deploy.yml (subscribe.php and the Stripe
// webhook include it from there); deploy/send_digest.php includes it from
// public_html/mailer.php. A direct GET of this file does nothing.

if (!function_exists('localspot_mail')) {

function localspot_smtp_config() {
    static $cfg = null;
    if ($cfg !== null) return $cfg;
    $file = dirname(__DIR__) . '/.smtp.json';
    $cfg = false;
    if (file_exists($file)) {
        $data = json_decode(file_get_contents($file), true);
        if (is_array($data) && !empty($data['host']) && !empty($data['user']) && !empty($data['pass'])) {
            $cfg = $data + ['port' => 465, 'from' => $data['user'], 'from_name' => 'LocalSpot'];
        }
    }
    return $cfg;
}

function _smtp_read($fp) {
    $lines = [];
    while (($line = fgets($fp, 1024)) !== false) {
        $lines[] = rtrim($line, "\r\n");
        if (strlen($line) < 4 || $line[3] !== '-') break; // "250 " ends, "250-" continues
    }
    return $lines ? end($lines) : '';
}

function _smtp_cmd($fp, $cmd, $expect) {
    fwrite($fp, $cmd . "\r\n");
    $reply = _smtp_read($fp);
    if (substr($reply, 0, 1) !== (string)$expect[0]) {
        throw new RuntimeException("SMTP: '" . substr($cmd, 0, 12) . "' got '" . $reply . "'");
    }
    return $reply;
}

/**
 * Send one HTML email. $extraHeaders is an assoc array (e.g. List-Unsubscribe).
 * $fromName is prefixed to the configured sender ("LocalSpot Phoenixville").
 * Returns true when the SMTP server accepted the message.
 */
function localspot_mail($to, $subject, $html, $fromName = '', $extraHeaders = []) {
    $cfg = localspot_smtp_config();
    if (!$cfg) {
        // Kept so nothing fatals before the mailbox exists; delivery is not expected.
        $h = "MIME-Version: 1.0\r\nContent-Type: text/html; charset=UTF-8\r\nFrom: LocalSpot <noreply@localspothq.com>";
        @mail($to, $subject, $html, $h);
        return false;
    }
    $from = $cfg['from'];
    $name = trim($fromName) !== '' ? $fromName : $cfg['from_name'];
    $host = ((int)$cfg['port'] === 465 ? 'ssl://' : '') . $cfg['host'];

    $fp = @stream_socket_client($host . ':' . (int)$cfg['port'], $errno, $errstr, 20);
    if (!$fp) return false;
    stream_set_timeout($fp, 20);
    try {
        if (substr(_smtp_read($fp), 0, 1) !== '2') throw new RuntimeException('SMTP: bad greeting');
        _smtp_cmd($fp, 'EHLO localspothq.com', '250');
        if ((int)$cfg['port'] !== 465) {
            _smtp_cmd($fp, 'STARTTLS', '220');
            if (!stream_socket_enable_crypto($fp, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) throw new RuntimeException('SMTP: TLS failed');
            _smtp_cmd($fp, 'EHLO localspothq.com', '250');
        }
        _smtp_cmd($fp, 'AUTH LOGIN', '334');
        _smtp_cmd($fp, base64_encode($cfg['user']), '334');
        _smtp_cmd($fp, base64_encode($cfg['pass']), '235');
        _smtp_cmd($fp, 'MAIL FROM:<' . $from . '>', '250');
        _smtp_cmd($fp, 'RCPT TO:<' . $to . '>', '250');
        _smtp_cmd($fp, 'DATA', '354');

        $encName = '=?UTF-8?B?' . base64_encode($name) . '?=';
        $encSubject = '=?UTF-8?B?' . base64_encode($subject) . '?=';
        $headers = [
            'Date: ' . date('r'),
            'From: ' . $encName . ' <' . $from . '>',
            'To: <' . $to . '>',
            'Subject: ' . $encSubject,
            'Message-ID: <' . bin2hex(random_bytes(12)) . '@localspothq.com>',
            'MIME-Version: 1.0',
            'Content-Type: text/html; charset=UTF-8',
            'Content-Transfer-Encoding: base64',
        ];
        foreach ($extraHeaders as $k => $v) $headers[] = $k . ': ' . $v;
        $body = chunk_split(base64_encode($html), 76, "\r\n");
        fwrite($fp, implode("\r\n", $headers) . "\r\n\r\n" . $body . "\r\n.\r\n");
        $reply = _smtp_read($fp);
        if (substr($reply, 0, 1) !== '2') throw new RuntimeException('SMTP: DATA got ' . $reply);
        fwrite($fp, "QUIT\r\n");
        fclose($fp);
        return true;
    } catch (Throwable $e) {
        @fwrite($fp, "QUIT\r\n");
        @fclose($fp);
        error_log('localspot_mail: ' . $e->getMessage());
        return false;
    }
}

} // function_exists guard
