<?php
/**
 * PHP Proxy Shim for Flask API
 * 
 * This script acts as a reverse proxy between Apache (HTTPS) and Flask (HTTP).
 * Apache handles SSL with Let's Encrypt certificates, PHP forwards requests
 * to the Flask backend running on localhost:5000.
 * 
 * Flow: Browser (HTTPS) → Apache → This PHP script → Flask (HTTP localhost:5000)
 * 
 * Deployment: Place in /home/gravityc/public_html/dndchat.gravitycar.com/
 */

// Configuration
define('FLASK_HOST', '127.0.0.1');
define('FLASK_PORT', '5000');
define('FLASK_TIMEOUT', 120); // Match gunicorn timeout

// Build Flask URL from request
$request_uri = $_SERVER['REQUEST_URI'];
$flask_url = 'http://' . FLASK_HOST . ':' . FLASK_PORT . $request_uri;

// Get request method
$method = $_SERVER['REQUEST_METHOD'];

// Get origin for CORS
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$allowed_origins = ['https://react.gravitycar.com', 'https://gravitycar.com'];
$is_allowed_origin = in_array($origin, $allowed_origins);

// Handle OPTIONS preflight request directly (don't forward to Flask)
if ($method === 'OPTIONS') {
    if ($is_allowed_origin) {
        header("Access-Control-Allow-Origin: $origin");
        header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
        header('Access-Control-Allow-Headers: Content-Type, Authorization');
        header('Access-Control-Allow-Credentials: true');
        header('Access-Control-Max-Age: 3600');
        http_response_code(200);
        exit;
    } else {
        http_response_code(403);
        exit;
    }
}

// Initialize cURL
$ch = curl_init($flask_url);

// Set request method
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);

// Forward request body (for POST, PUT, PATCH)
if (in_array($method, ['POST', 'PUT', 'PATCH'])) {
    $request_body = file_get_contents('php://input');
    curl_setopt($ch, CURLOPT_POSTFIELDS, $request_body);
}

// Return response instead of outputting
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HEADER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, FLASK_TIMEOUT);

// Forward request headers to Flask
$headers = [];

// Use getallheaders() if available, otherwise build from $_SERVER
if (function_exists('getallheaders')) {
    $all_headers = getallheaders();
} else {
    // Fallback for CGI/FastCGI environments
    $all_headers = [];
    foreach ($_SERVER as $name => $value) {
        if (substr($name, 0, 5) == 'HTTP_') {
            $header_name = str_replace(' ', '-', ucwords(strtolower(str_replace('_', ' ', substr($name, 5)))));
            $all_headers[$header_name] = $value;
        }
    }
}

foreach ($all_headers as $name => $value) {
    // Skip Host header (will be set to localhost:5000)
    if (strtolower($name) === 'host') {
        continue;
    }
    $headers[] = "$name: $value";
}

// Add X-Forwarded headers for Flask to know original client
$headers[] = 'X-Forwarded-For: ' . $_SERVER['REMOTE_ADDR'];
$headers[] = 'X-Forwarded-Proto: https';
$headers[] = 'X-Forwarded-Host: ' . $_SERVER['HTTP_HOST'];
$headers[] = 'X-Real-IP: ' . $_SERVER['REMOTE_ADDR'];

curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

// Execute request to Flask
$response = curl_exec($ch);

// Check for cURL errors
if (curl_errno($ch)) {
    http_response_code(502); // Bad Gateway
    header('Content-Type: application/json');
    echo json_encode([
        'error' => 'Backend connection failed',
        'message' => 'Unable to connect to Flask backend',
        'details' => curl_error($ch)
    ]);
    curl_close($ch);
    exit;
}

// Get response info
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);

curl_close($ch);

// Split headers and body
$response_headers = substr($response, 0, $header_size);
$response_body = substr($response, $header_size);

// Set HTTP response code
http_response_code($http_code);

// Set CORS headers for actual response (not just OPTIONS)
if ($is_allowed_origin) {
    header("Access-Control-Allow-Origin: $origin");
    header('Access-Control-Allow-Credentials: true');
}

// Forward response headers from Flask to client
$header_lines = explode("\r\n", $response_headers);
foreach ($header_lines as $header) {
    // Skip empty lines and HTTP status line
    if (empty($header) || strpos($header, 'HTTP/') === 0) {
        continue;
    }
    
    // Skip headers that PHP shouldn't forward
    $header_lower = strtolower($header);
    if (strpos($header_lower, 'transfer-encoding:') === 0 ||
        strpos($header_lower, 'connection:') === 0 ||
        strpos($header_lower, 'access-control-') === 0) {  // Skip Flask's CORS headers
        continue;
    }
    
    header($header, false);
}

// Output response body
echo $response_body;
?>
