<#-- Wraps every HTML email Keycloak sends (verify email, password reset...) in the same plain layout
     as the emails the Core API sends (backend/server/app/services/email/templates.py). -->
<#macro emailLayout>
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { margin: 0; background: #f4f4f5; }
        .wrap { padding: 32px 16px; font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        .card { max-width: 480px; margin: 0 auto; background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 28px; }
        .brand { margin: 0 0 20px; font-size: 14px; font-weight: 700; letter-spacing: 0.08em; color: #18181b; }
        .body, .body p { font-size: 14px; line-height: 1.6; color: #3f3f46; }
        .body a { color: #5146c7; }
        .foot { max-width: 480px; margin: 16px auto 0; font-size: 12px; color: #a1a1aa; }
    </style>
</head>
<body>
<div class="wrap">
    <div class="card">
        <p class="brand">SELVIA</p>
        <div class="body"><#nested></div>
    </div>
    <p class="foot">You received this because of activity on your SELVIA account.</p>
</div>
</body>
</html>
</#macro>
