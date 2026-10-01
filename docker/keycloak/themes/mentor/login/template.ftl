<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex, nofollow">
    <title>Sign in to SELVIA</title>
    <link rel="icon" type="image/png" href="${url.resourcesPath}/img/selvia-mark.png" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
</head>
<body class="bg-background text-foreground min-h-screen">
    <div class="login-wrapper">
        <!-- ------------------------------------------------------------- -->
        <!-- LEFT: Brand Showcase (Desktop only)                           -->
        <!-- ------------------------------------------------------------- -->
        <section class="showcase-section">
            <!-- Subtle dot grid background -->
            <div class="grid-overlay"></div>

            <!-- Ambient atmospheric glows -->
            <div class="glow glow-top"></div>
            <div class="glow glow-bottom"></div>

            <!-- Brand Header -->
            <div class="showcase-header">
                <div class="logo-lockup">
                    <img src="${url.resourcesPath}/img/selvia-mark.png" alt="SELVIA" class="logo-mark" width="42" height="42" />
                    <div class="brand-text">
                        <div class="brand-title-row">
                            <span class="brand-name">SELVIA</span>
                            <span class="ai-badge">AI</span>
                        </div>
                        <span class="brand-tagline">Engineering Workspace</span>
                    </div>
                </div>
            </div>

            <!-- Value Proposition -->
            <div class="showcase-content">
                <h1 class="showcase-headline">
                    Intelligent project planning and continuous learning support.
                </h1>
                <p class="showcase-subhead">
                    Streamlining software project tracking, automated quality gates, and real-time team guidance into a single unified workspace.
                </p>

                <!-- Testimonial Card -->
                <div class="testimonial-card">
                    <p class="testimonial-quote">
                        &ldquo;SELVIA brings project requirements, team contributions, and intelligent tutoring together with seamless clarity.&rdquo;
                    </p>
                    <div class="testimonial-author">
                        <div class="avatar-badge">S</div>
                        <div>
                            <p class="author-title">Engineering Workspace</p>
                            <p class="author-sub">Continuous Quality Assurance</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Left Footer -->
            <div class="showcase-footer">
                <span>&copy; 2026 SELVIA. All rights reserved.</span>
            </div>
        </section>

        <!-- ------------------------------------------------------------- -->
        <!-- RIGHT: Authentication Panel                                   -->
        <!-- ------------------------------------------------------------- -->
        <section class="auth-section">
            <!-- Mobile Brand Header -->
            <div class="mobile-header">
                <div class="logo-lockup">
                    <img src="${url.resourcesPath}/img/selvia-mark.png" alt="SELVIA" class="logo-mark" width="32" height="32" />
                    <span class="brand-name" style="font-size: 16px;">SELVIA</span>
                </div>
            </div>

            <!-- Centered Form Container -->
            <div class="form-container">
                <div class="form-header">
                    <#if pageId?? && pageId == "logout-confirm">
                        <h2 class="form-title">Confirm Sign Out</h2>
                        <p class="form-subtitle">Please confirm that you want to end your current session.</p>
                    <#elseif pageId?? && pageId == "info">
                        <h2 class="form-title">Session Notice</h2>
                        <p class="form-subtitle">Status update from the identity provider.</p>
                    <#elseif pageId?? && pageId == "error">
                        <h2 class="form-title">Authentication Notice</h2>
                        <p class="form-subtitle">An issue occurred during your authentication request.</p>
                    <#else>
                        <h2 class="form-title">Sign in to SELVIA</h2>
                        <p class="form-subtitle">Welcome back! Please enter your details to continue.</p>
                    </#if>
                </div>

                <!-- Error / Alert Banner -->
                <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
                    <div class="alert-box alert-${message.type}">
                        <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <span>${kcSanitize(message.summary)?no_esc}</span>
                    </div>
                </#if>

                <!-- Form injected by login.ftl -->
                <#nested "form">
            </div>

            <!-- Footer -->
            <footer class="auth-footer">
                <span>&copy; 2026 SELVIA Platform. All rights reserved.</span>
                <span class="footer-links">Privacy &amp; Terms</span>
            </footer>
        </section>
    </div>
</body>
</html>
</#macro>
