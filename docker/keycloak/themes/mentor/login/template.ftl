<#macro icon name class="icon">
<svg class="${class}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><#switch name>
<#case "mail"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/><#break>
<#case "lock"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><#break>
<#case "key"><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/><#break>
<#case "user"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/><#break>
<#case "user-plus"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M22 11h-6"/><#break>
<#case "at-sign"><circle cx="12" cy="12" r="4"/><path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8"/><#break>
<#case "arrow-right"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/><#break>
<#case "arrow-left"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/><#break>
<#case "alert-circle"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/><#break>
<#case "alert-triangle"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/><#break>
<#case "info"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/><#break>
<#case "check"><path d="M20 6 9 17l-5-5"/><#break>
<#case "check-circle"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/><#break>
<#case "log-out"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/><#break>
<#case "eye"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/><#break>
<#case "eye-off"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.53 13.53 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><path d="M2 2l20 20"/><#break>
<#case "sun"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/><#break>
<#case "moon"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/><#break>
<#case "graduation-cap"><path d="M22 10v6"/><path d="M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/><#break>
<#case "presentation"><path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/><path d="m7 21 5-5 5 5"/><#break>
<#case "shield-check"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/><#break>
<#case "book-open"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/><#break>
<#case "bar-chart"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/><#break>
<#case "bot"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/><#break>
<#default><circle cx="12" cy="12" r="10"/>
</#switch></svg>
</#macro>

<#macro passwordToggle target>
<button type="button" class="input-action" data-toggle-password="${target}" aria-controls="${target}" aria-pressed="false" aria-label="Show password">
    <@icon name="eye" class="icon icon-eye"/>
    <@icon name="eye-off" class="icon icon-eye-off"/>
</button>
</#macro>

<#macro fieldError name>
<#if messagesPerField.existsError(name)>
<span id="${name}-error" class="field-error" aria-live="polite">
    <@icon name="alert-circle"/>
    <span>${kcSanitize(messagesPerField.get(name))?no_esc}</span>
</span>
</#if>
</#macro>

<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<#assign currentPage = (pageId!(.main_template_name!''))?remove_ending('.ftl')>
<#assign isRegister = currentPage == "register">
<#switch currentPage>
    <#case "login">
        <#assign pageTitle = "Welcome back">
        <#assign pageSubtitle = "Sign in to continue to your SELVIA workspace.">
        <#assign pageIcon = "">
        <#break>
    <#case "register">
        <#assign pageTitle = "Create your account">
        <#assign pageSubtitle = "Join your team's workspace. It only takes a minute.">
        <#assign pageIcon = "">
        <#break>
    <#case "login-reset-password">
        <#assign pageTitle = "Forgot your password?">
        <#assign pageSubtitle = "Enter the email you use for SELVIA and we'll send you a link to reset it.">
        <#assign pageIcon = "key">
        <#break>
    <#case "login-update-password">
        <#assign pageTitle = "Set a new password">
        <#assign pageSubtitle = "Choose a strong password that you haven't used before.">
        <#assign pageIcon = "lock">
        <#break>
    <#case "logout-confirm">
        <#assign pageTitle = "Sign out of SELVIA?">
        <#assign pageSubtitle = "You'll need to sign in again to get back to your workspace.">
        <#assign pageIcon = "log-out">
        <#break>
    <#case "error">
        <#assign pageTitle = "Something went wrong">
        <#assign pageSubtitle = "We couldn't complete your request.">
        <#assign pageIcon = "alert-triangle">
        <#break>
    <#case "info">
        <#assign pageTitle = (messageHeader??)?then(msg(messageHeader!''), "Just so you know")>
        <#assign pageSubtitle = "">
        <#assign pageIcon = "info">
        <#break>
    <#default>
        <#assign pageTitle = "">
        <#assign pageSubtitle = "">
        <#assign pageIcon = "shield-check">
</#switch>
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex, nofollow">
    <meta name="color-scheme" content="light dark">
    <title><#if isRegister>Create your account · SELVIA<#elseif currentPage == "login">Sign in · SELVIA<#else>SELVIA</#if></title>
    <link rel="icon" type="image/png" href="${url.resourcesPath}/img/selvia-mark.png" />
    <link rel="apple-touch-icon" href="${url.resourcesPath}/img/selvia-mark.png" />
    <script>
        (function () {
            var theme = null;
            try { theme = localStorage.getItem('selvia-auth-theme'); } catch (e) {}
            if (theme !== 'light' && theme !== 'dark') {
                theme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            }
            document.documentElement.setAttribute('data-theme', theme);
        })();
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <#if properties.scripts?has_content>
        <#list properties.scripts?split(' ') as script>
            <script src="${url.resourcesPath}/${script}" defer></script>
        </#list>
    </#if>
    <#if scripts??>
        <#list scripts as script>
            <script src="${script}" defer></script>
        </#list>
    </#if>
</head>
<body class="${bodyClass}">
<div class="auth-shell">
    <aside class="showcase" aria-hidden="true">
        <div class="brand">
            <img src="${url.resourcesPath}/img/selvia-mark.png" alt="" class="brand-mark" width="44" height="44" />
            <span class="brand-text">
                <span class="brand-name">SELVIA</span>
                <span class="brand-tagline">Engineering Workspace</span>
            </span>
        </div>

        <div class="showcase-body">
            <span class="eyebrow"><span class="eyebrow-dot"></span>Student &amp; Lecturer portals</span>
            <h1 class="showcase-title">
                Your software project,<br/>
                <span class="accent">all in one workspace.</span>
            </h1>
            <p class="showcase-lead">
                Plan sprints, track team performance, fix security issues and learn with an AI tutor.
                Built for student teams and the lecturers who guide them.
            </p>

            <div class="preview">
                <div class="preview-head">
                    <div>
                        <p class="preview-eyebrow">Sprint 4 &middot; Group 07</p>
                        <p class="preview-title">AEGIS &mdash; Security Assistant</p>
                    </div>
                    <span class="preview-badge"><span></span>On track</span>
                </div>

                <div class="preview-stats">
                    <div class="preview-stat">
                        <span class="preview-stat-icon blue"><@icon name="check-circle"/></span>
                        <span class="preview-stat-value">18/24</span>
                        <span class="preview-stat-label">Tasks done</span>
                    </div>
                    <div class="preview-stat">
                        <span class="preview-stat-icon green"><@icon name="bar-chart"/></span>
                        <span class="preview-stat-value">92%</span>
                        <span class="preview-stat-label">Quality gate</span>
                    </div>
                    <div class="preview-stat">
                        <span class="preview-stat-icon amber"><@icon name="shield-check"/></span>
                        <span class="preview-stat-value">2</span>
                        <span class="preview-stat-label">Open findings</span>
                    </div>
                </div>

                <div class="preview-progress">
                    <div class="preview-progress-meta"><span>Sprint progress</span><span>75%</span></div>
                    <div class="preview-progress-bar"><span style="width: 75%"></span></div>
                </div>

                <div class="preview-nudge">
                    <span class="preview-nudge-icon"><@icon name="bot"/></span>
                    <p><strong>Tutor Agent</strong> Review your story points before Friday's planning session.</p>
                </div>
            </div>

            <div class="module-row">
                <span class="module-chip"><@icon name="book-open"/>Project Planning</span>
                <span class="module-chip"><@icon name="bar-chart"/>Performance</span>
                <span class="module-chip"><@icon name="bot"/>Tutor Agent</span>
                <span class="module-chip"><@icon name="shield-check"/>AEGIS Security</span>
            </div>
        </div>

        <div class="showcase-footer">
            <span class="trust"><@icon name="lock"/>Secured with single sign-on</span>
            <span>Engineering Workspace</span>
        </div>
    </aside>

    <main class="auth-panel">
        <header class="auth-topbar">
            <span class="brand">
                <img src="${url.resourcesPath}/img/selvia-mark.png" alt="" class="brand-mark" width="36" height="36" />
                <span class="brand-text">
                    <span class="brand-name">SELVIA</span>
                </span>
            </span>
            <div class="topbar-actions">
                <button type="button" class="icon-btn" data-theme-toggle aria-label="Switch between light and dark theme" title="Toggle theme">
                    <@icon name="moon" class="icon theme-icon-light"/>
                    <@icon name="sun" class="icon theme-icon-dark"/>
                </button>
            </div>
        </header>

        <div class="auth-main">
            <div class="auth-card<#if isRegister> wide</#if>">
                <div class="auth-header">
                    <#if pageIcon?has_content>
                        <span class="auth-header-icon<#if currentPage == 'error'> danger</#if>"><@icon name=pageIcon/></span>
                    </#if>
                    <h2 class="auth-title"><#if pageTitle?has_content>${pageTitle}<#else><#nested "header"></#if></h2>
                    <#if pageSubtitle?has_content>
                        <p class="auth-subtitle">${pageSubtitle}</p>
                    </#if>
                    <#if displayRequiredFields>
                        <p class="required-note"><span class="req">*</span> Required fields</p>
                    </#if>
                </div>

                <#if auth?has_content && auth.showUsername() && !auth.showResetCredentials()>
                    <div class="attempted-user">
                        <span class="attempted-user-avatar"><@icon name="user"/></span>
                        <span class="attempted-user-name">${auth.attemptedUsername}</span>
                        <a class="attempted-user-change" href="${url.loginRestartFlowUrl}">Change</a>
                    </div>
                </#if>

                <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
                    <div class="alert alert-${message.type}" <#if message.type == 'error'>role="alert"<#else>role="status"</#if>>
                        <#switch message.type>
                            <#case "success"><@icon name="check-circle"/><#break>
                            <#case "warning"><@icon name="alert-triangle"/><#break>
                            <#case "info"><@icon name="info"/><#break>
                            <#default><@icon name="alert-circle"/>
                        </#switch>
                        <span>${kcSanitize(message.summary)?no_esc}</span>
                    </div>
                </#if>

                <#nested "form">

                <#if displayInfo>
                    <div class="auth-info">
                        <#nested "info">
                    </div>
                </#if>
            </div>
        </div>

        <footer class="auth-footer">
            <span>Trouble signing in? Contact your lecturer or project admin.</span>
            <span>&copy; ${.now?string('yyyy')} SELVIA</span>
        </footer>
    </main>
</div>
</body>
</html>
</#macro>
