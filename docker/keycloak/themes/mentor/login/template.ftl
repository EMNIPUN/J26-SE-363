<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex, nofollow">
    <title>Sign in to MENTOR</title>
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
                    <svg width="38" height="38" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="logo-svg">
                        <path d="M20 4L35 12.5V27.5L20 36L5 27.5V12.5L20 4Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.3"/>
                        <line x1="20" y1="4" x2="20" y2="18" stroke="currentColor" stroke-width="1.2" opacity="0.35"/>
                        <line x1="5" y1="12.5" x2="14" y2="18" stroke="currentColor" stroke-width="1.2" opacity="0.35"/>
                        <line x1="35" y1="12.5" x2="26" y2="18" stroke="currentColor" stroke-width="1.2" opacity="0.35"/>
                        <path d="M10 29V15L20 24L30 15V29" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                        <circle cx="20" cy="4" r="2" fill="currentColor"/>
                        <circle cx="35" cy="12.5" r="2" fill="currentColor"/>
                        <circle cx="35" cy="27.5" r="2" fill="currentColor"/>
                        <circle cx="20" cy="36" r="2" fill="currentColor"/>
                        <circle cx="5" cy="27.5" r="2" fill="currentColor"/>
                        <circle cx="5" cy="12.5" r="2" fill="currentColor"/>
                        <path d="M20 13L22 17L26 18L22 19L20 23L18 19L14 18L18 17L20 13Z" fill="#3b82f6"/>
                    </svg>
                    <div class="brand-text">
                        <div class="brand-title-row">
                            <span class="brand-name">MENTOR</span>
                            <span class="ai-badge">AI</span>
                        </div>
                        <span class="brand-tagline">Engineering Workspace</span>
                    </div>
                </div>
            </div>

            <!-- Value Proposition -->
            <div class="showcase-content">
                <h1 class="showcase-headline">
                    Intelligent project planning and continuous mentoring.
                </h1>
                <p class="showcase-subhead">
                    Streamlining software project tracking, automated quality gates, and real-time team mentoring into a single unified workspace.
                </p>

                <!-- Testimonial Card -->
                <div class="testimonial-card">
                    <p class="testimonial-quote">
                        &ldquo;MENTOR brings project requirements, team contributions, and intelligent tutoring together with seamless clarity.&rdquo;
                    </p>
                    <div class="testimonial-author">
                        <div class="avatar-badge">M</div>
                        <div>
                            <p class="author-title">Engineering Workspace</p>
                            <p class="author-sub">Continuous Quality Assurance</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Left Footer -->
            <div class="showcase-footer">
                <span>&copy; 2026 MENTOR. All rights reserved.</span>
            </div>
        </section>

        <!-- ------------------------------------------------------------- -->
        <!-- RIGHT: Authentication Panel                                   -->
        <!-- ------------------------------------------------------------- -->
        <section class="auth-section">
            <!-- Mobile Brand Header -->
            <div class="mobile-header">
                <div class="logo-lockup">
                    <svg width="32" height="32" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="logo-svg">
                        <path d="M20 4L35 12.5V27.5L20 36L5 27.5V12.5L20 4Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.3"/>
                        <path d="M10 29V15L20 24L30 15V29" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M20 13L22 17L26 18L22 19L20 23L18 19L14 18L18 17L20 13Z" fill="#3b82f6"/>
                    </svg>
                    <span class="brand-name" style="font-size: 16px;">MENTOR</span>
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
                        <h2 class="form-title">Sign in to MENTOR</h2>
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
                <span>&copy; 2026 MENTOR Platform. All rights reserved.</span>
                <span class="footer-links">Privacy &amp; Terms</span>
            </footer>
        </section>
    </div>
</body>
</html>
</#macro>
