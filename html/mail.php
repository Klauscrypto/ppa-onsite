<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false]);
    exit;
}

$raw = file_get_contents('php://input');
$d = json_decode($raw, true);
if (!$d) {
    http_response_code(400);
    echo json_encode(['success' => false]);
    exit;
}

$to      = 'info@pilsner-vertrieb.de';
$type    = isset($d['type']) ? $d['type'] : 'Kontaktanfrage';
$name    = isset($d['name'])    ? strip_tags(trim($d['name']))    : '';
$email   = isset($d['email'])   ? strip_tags(trim($d['email']))   : '';
$firma   = isset($d['firma'])   ? strip_tags(trim($d['firma']))   : '';
$tel     = isset($d['tel'])     ? strip_tags(trim($d['tel']))     : '';
$nachricht = isset($d['nachricht']) ? strip_tags(trim($d['nachricht'])) : '';
$verbrauch = isset($d['verbrauch']) ? strip_tags(trim($d['verbrauch'])) : '';
$dach    = isset($d['dach'])    ? strip_tags(trim($d['dach']))    : '';

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(422);
    echo json_encode(['success' => false, 'message' => 'Ungültige E-Mail']);
    exit;
}

$subject = "[$type] Neue Anfrage von $name" . ($firma ? " ($firma)" : '') . ' — PPA-Onsite.de';

$body  = "Neue $type von PPA-Onsite.de\n";
$body .= str_repeat('=', 50) . "\n\n";
$body .= "Name:    $name\n";
$body .= "E-Mail:  $email\n";
if ($firma)     $body .= "Firma:   $firma\n";
if ($tel)       $body .= "Telefon: $tel\n";
if ($verbrauch) $body .= "Jahresstromverbrauch: $verbrauch kWh\n";
if ($dach)      $body .= "Dachfläche: $dach m²\n";
if ($nachricht) $body .= "\nNachricht:\n$nachricht\n";
$body .= "\n" . str_repeat('-', 50) . "\n";
$body .= "Gesendet: " . date('d.m.Y H:i') . " Uhr\n";
$body .= "IP: " . $_SERVER['REMOTE_ADDR'] . "\n";

$headers  = "From: noreply@ppa-onsite.de\r\n";
$headers .= "Reply-To: $email\r\n";
$headers .= "X-Mailer: PPA-Onsite/1.0\r\n";
$headers .= "Content-Type: text/plain; charset=UTF-8\r\n";

$ok = mail($to, $subject, $body, $headers);
echo json_encode(['success' => $ok]);
