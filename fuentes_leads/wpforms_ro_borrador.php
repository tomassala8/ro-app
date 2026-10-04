<?php
/**
 * BORRADOR PARA REVISIÓN. No instalado, no cron, no administración ni activación.
 * Requiere WordPress y tabla provisionada aparte. Captura y envío apagados
 * salvo constantes explícitas RO_WPFORMS_CAPTURE_ENABLED / SEND_ENABLED === true.
 * Fuente: https://wpforms.com/developers/wpforms_process_complete/
 */
if (!defined('ABSPATH')) { return; }

function ro_wpforms_config() {
    return array(
        'capture' => defined('RO_WPFORMS_CAPTURE_ENABLED') && RO_WPFORMS_CAPTURE_ENABLED === true,
        'send' => defined('RO_WPFORMS_SEND_ENABLED') && RO_WPFORMS_SEND_ENABLED === true,
        'forms' => defined('RO_WPFORMS_FORMS') && is_array(RO_WPFORMS_FORMS) ? RO_WPFORMS_FORMS : array(),
        'endpoint' => defined('RO_WPFORMS_ENDPOINT') ? RO_WPFORMS_ENDPOINT : '',
        'key_id' => defined('RO_WPFORMS_KEY_ID') ? RO_WPFORMS_KEY_ID : '',
        'secret' => defined('RO_WPFORMS_SECRET') ? RO_WPFORMS_SECRET : ''
    );
}

function ro_wpforms_endpoint_valido($url) {
    if (!is_string($url) || $url === '') { return false; }
    $u = wp_parse_url($url);
    return is_array($u) && isset($u['scheme'], $u['host']) && $u['scheme'] === 'https'
        && !isset($u['user']) && !isset($u['pass']) && !isset($u['query']) && !isset($u['fragment']);
}

function ro_wpforms_capture($fields, $ignored_post, $form_data, $entry_id) {
    // Nunca leer $ignored_post: es $_POST original, no un objeto saneado.
    $cfg = ro_wpforms_config();
    if (!$cfg['capture'] || !is_array($fields) || !is_array($form_data)) { return; }
    $form_id = isset($form_data['id']) ? absint($form_data['id']) : 0;
    if (!isset($cfg['forms'][$form_id])) { return; }
    $scope = $cfg['forms'][$form_id];
    if (!is_array($scope) || !isset($scope['cliente_id'], $scope['source_id'])
        || !is_string($scope['cliente_id']) || !is_string($scope['source_id'])
        || !preg_match('/^[a-zA-Z0-9_-]{1,100}$/', $scope['cliente_id'])
        || !preg_match('/^[a-zA-Z0-9_-]{1,100}$/', $scope['source_id'])) { return; }
    global $wpdb;
    $old = $wpdb->suppress_errors(true);
    try {
        $table = $wpdb->prefix . 'ro_wpforms_outbox';
        // Límite total de filas: no borrar pendientes ni bloquear el formulario.
        $pending = $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
        if ($pending === null || (int)$pending >= 1000) {
            error_log('RO WPForms: copia secundaria no guardada; revisar cola.');
            return;
        }
        $entry_id = absint($entry_id);
        // Entry ID local es estable solo dentro de source_id + form_id.
        $dedup_key = $entry_id > 0
            ? hash('sha256', $scope['source_id'] . ':' . $scope['cliente_id'] . ':' . $form_id . ':' . $entry_id)
            : null;
        if ($dedup_key !== null && $wpdb->get_var($wpdb->prepare(
            "SELECT event_id FROM {$table} WHERE dedup_key=%s", $dedup_key))) { return; }
        // Lite: UUID generado una vez y persistido junto al payload en la misma fila.
        $event_id = wp_generate_uuid4();
        $event = array('schema_version'=>1, 'event'=>'form_submission_accepted',
            'event_id'=>$event_id, 'source_id'=>(string)$scope['source_id'],
            'cliente_id'=>(string)$scope['cliente_id'], 'form_id'=>$form_id,
            'entry_id'=>$entry_id > 0 ? $entry_id : null,
            'occurred_at'=>gmdate('Y-m-d\TH:i:s\Z'), 'private_fields'=>array());
        // Allowlist fija de IDs => nombres semánticos. No etiquetas, IP, URL, UA ni todo el POST.
        foreach (isset($scope['fields']) && is_array($scope['fields']) ? $scope['fields'] : array() as $id=>$name) {
            if (!is_int($id) || !is_string($name) || !preg_match('/^[a-z][a-z0-9_]{0,39}$/', $name)) { continue; }
            $v = isset($fields[$id]['value']) ? $fields[$id]['value'] : null;
            if (!is_string($v)) { continue; } // Adjuntos/arrays no entran en este borrador.
            $event['private_fields'][$name] = substr(sanitize_text_field($v), 0, 2048);
        }
        $body = wp_json_encode($event, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        if (!is_string($body) || strlen($body) > 16384) {
            error_log('RO WPForms: copia secundaria excede límite o no se pudo serializar.');
            return;
        }
        $saved = $wpdb->insert($table, array('event_id'=>$event_id, 'dedup_key'=>$dedup_key,
            'payload'=>$body, 'status'=>'pending', 'attempts'=>0, 'next_attempt'=>time(),
            'lease_until'=>0, 'lease_token'=>'', 'created_at'=>gmdate('Y-m-d H:i:s'), 'last_code'=>0));
        if ($saved !== 1) { error_log('RO WPForms: fallo guardando copia secundaria.'); }
        // No transporte HTTP en este hook: la ruta principal de WPForms/GHL no cambia.
    } catch (Throwable $e) {
        error_log('RO WPForms: fallo de copia secundaria; formulario principal continúa.');
    } finally {
        $wpdb->suppress_errors($old);
    }
}
add_action('wpforms_process_complete', 'ro_wpforms_capture', 10, 4);

function ro_wpforms_drain_borrador() {
    // Sin scheduler ni endpoint admin. Invocación futura explícita por administrador.
    if (!current_user_can('manage_options')) { return; }
    $cfg = ro_wpforms_config();
    if (!$cfg['capture'] || !$cfg['send'] || !ro_wpforms_endpoint_valido($cfg['endpoint'])
        || !is_string($cfg['secret']) || strlen($cfg['secret']) < 32
        || !is_string($cfg['key_id']) || !preg_match('/^[a-zA-Z0-9_-]{1,64}$/', $cfg['key_id'])) { return; }
    global $wpdb;
    $old = $wpdb->suppress_errors(true);
    try {
        $table = $wpdb->prefix . 'ro_wpforms_outbox';
        $now = time();
        // Diez filas por llamada y cinco intentos por fila; lease recuperable tras caída.
        $rows = $wpdb->get_results($wpdb->prepare(
            "SELECT event_id FROM {$table} WHERE status IN ('pending','sending') AND attempts<5 AND next_attempt<=%d AND lease_until<%d ORDER BY next_attempt,event_id LIMIT 10", $now, $now), ARRAY_A);
        foreach (is_array($rows) ? $rows : array() as $row) {
            $token = wp_generate_uuid4();
            $claimed = $wpdb->query($wpdb->prepare(
                "UPDATE {$table} SET status='sending', attempts=attempts+1, lease_until=%d, lease_token=%s WHERE event_id=%s AND status IN ('pending','sending') AND attempts<5 AND next_attempt<=%d AND lease_until<%d",
                $now + 120, $token, $row['event_id'], $now, $now));
            if ($claimed !== 1) { continue; }
            $item = $wpdb->get_row($wpdb->prepare(
                "SELECT payload,attempts FROM {$table} WHERE event_id=%s AND lease_token=%s", $row['event_id'], $token), ARRAY_A);
            if (!$item) { continue; }
            $stamp = (string)time();
            $signature = hash_hmac('sha256', $stamp . '.' . $item['payload'], $cfg['secret']);
            $response = wp_remote_post($cfg['endpoint'], array('timeout'=>8, 'redirection'=>0,
                'sslverify'=>true, 'reject_unsafe_urls'=>true, 'limit_response_size'=>4096,
                'headers'=>array('Content-Type'=>'application/json', 'X-RO-Key-ID'=>$cfg['key_id'],
                    'X-RO-Timestamp'=>$stamp, 'X-RO-Signature'=>'v1=' . $signature,
                    'X-RO-Event-ID'=>$row['event_id']), 'body'=>$item['payload']));
            $code = is_wp_error($response) ? 0 : (int)wp_remote_retrieve_response_code($response);
            $ack = is_wp_error($response) ? null : json_decode(wp_remote_retrieve_body($response), true);
            // Solo ack de la MISMA identidad tras persistencia duradera del receptor.
            $ok = $code >= 200 && $code < 300 && is_array($ack)
                && isset($ack['event_id']) && hash_equals($row['event_id'], (string)$ack['event_id'])
                && isset($ack['durable']) && $ack['durable'] === true;
            $state = $ok ? 'delivered' : ((int)$item['attempts'] >= 5 ? 'failed' : 'pending');
            $wpdb->query($wpdb->prepare(
                "UPDATE {$table} SET status=%s,next_attempt=%d,lease_until=0,lease_token='',last_code=%d,payload=%s WHERE event_id=%s AND lease_token=%s",
                $state, time() + min(3600, 60 * (2 ** (int)$item['attempts'])), $code,
                $ok ? '{}' : $item['payload'], $row['event_id'], $token));
        }
        // Un crash del quinto envío debe terminar en failed, no quedar sending para siempre.
        $wpdb->query($wpdb->prepare(
            "UPDATE {$table} SET status='failed',lease_token='' WHERE status='sending' AND attempts>=5 AND lease_until<%d", time()));
    } catch (Throwable $e) {
        error_log('RO WPForms: fallo del worker secundario; revisar cola privada.');
    } finally {
        $wpdb->suppress_errors($old);
    }
}
