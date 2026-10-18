<#--
  SELVIA login theme. One centred card on the app's canvas: logo, heading, message, form.
  Colours and radius mirror frontend/src/index.css, so sign-in looks like the rest of the app.
-->
<#macro icon name>
<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><#switch name>
<#case "alert"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/><#break>
<#case "check"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/><#break>
<#case "info"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/><#break>
<#case "eye"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/><#break>
<#case "eye-off"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.53 13.53 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><path d="M2 2l20 20"/><#break>
<#default><circle cx="12" cy="12" r="10"/>
</#switch></svg>
</#macro>

<#-- Brand icons for the social buttons (single colour, so they work in both themes). -->
<#macro providerIcon alias>
<svg class="provider-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><#switch alias>
<#case "google"><path d="M21.35 11.1H12v2.98h5.35c-.23 1.4-1.64 4.1-5.35 4.1a5.9 5.9 0 0 1 0-11.8c1.87 0 3.12.8 3.84 1.48l2.1-2.03C20.6 4.5 18.5 3.6 12 3.6a8.4 8.4 0 0 0 0 16.8c4.85 0 8.07-3.4 8.07-8.2 0-.55-.06-.97-.14-1.4z"/><#break>
<#case "microsoft"><path d="M3 3h8.5v8.5H3zM12.5 3H21v8.5h-8.5zM3 12.5h8.5V21H3zM12.5 12.5H21V21h-8.5z"/><#break>
<#case "github"><path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.1-1.46-1.1-1.46-.9-.62.07-.6.07-.6 1 .07 1.52 1.03 1.52 1.03.89 1.52 2.34 1.08 2.9.83.09-.64.35-1.08.63-1.33-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.5 9.5 0 0 1 5 0c1.9-1.29 2.74-1.02 2.74-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0 0 12 2z"/><#break>
<#default><circle cx="12" cy="12" r="9"/>
</#switch></svg>
</#macro>

<#macro passwordToggle target>
<button type="button" class="input-action" data-toggle-password="${target}" aria-controls="${target}" aria-pressed="false" aria-label="Show password">
    <span class="when-hidden"><@icon name="eye"/></span>
    <span class="when-shown"><@icon name="eye-off"/></span>
</button>
</#macro>

<#macro fieldError name>
<#if messagesPerField.existsError(name)>
<p id="${name}-error" class="field-error" aria-live="polite">${kcSanitize(messagesPerField.get(name))?no_esc}</p>
</#if>
</#macro>

<#--
  The "confirm your details" form: the account's profile attributes (email, first and last name...).
  Used after signing in with a provider (idp-review-user-profile) and for the update-profile action.
-->
<#macro profileForm cancellable=false>
<form id="kc-update-profile-form" class="form" action="${url.loginAction}" method="post">
    <#if profile?? && profile.attributes??>
        <#list profile.attributes as attribute>
            <#if attribute.name != "username" || !realm.registrationEmailAsUsername>
            <div class="field">
                <label for="${attribute.name}" class="label">${attribute.displayName!attribute.name}</label>
                <input id="${attribute.name}" name="${attribute.name}" class="input"
                       type="<#if attribute.name == 'email'>email<#else>text</#if>" value="${attribute.value!''}"
                       <#if attribute.required>required</#if> <#if attribute.readOnly>readonly</#if>
                       <#if messagesPerField.existsError(attribute.name)>aria-invalid="true"</#if>>
                <@fieldError name=attribute.name/>
            </div>
            </#if>
        </#list>
    </#if>
    <div class="actions">
        <button class="btn btn-primary" type="submit" data-busy-label="Saving…">Continue</button>
        <#if cancellable>
            <button class="btn btn-outline" type="submit" name="cancel-aia" value="true" formnovalidate>Cancel</button>
        </#if>
    </div>
</form>
</#macro>

<#--
  Sign-in and sign-up with Google, Microsoft or GitHub. Only the providers configured in the
  realm are listed (docker/keycloak/README.md), and nothing is drawn when there are none.
-->
<#macro socialProviders>
<#if social?? && social.providers?? && social.providers?has_content>
<div class="providers">
    <#list social.providers as provider>
    <a id="social-${provider.alias}" class="btn btn-outline" href="${provider.loginUrl}">
        <@providerIcon alias=provider.alias/>
        <span>Continue with ${provider.displayName!provider.alias}</span>
    </a>
    </#list>
</div>
<div class="divider"><span>or</span></div>
</#if>
</#macro>

<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html lang="${(locale.currentLanguageTag)!'en'}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">
    <meta name="color-scheme" content="light dark">
    <title>SELVIA</title>
    <link rel="icon" type="image/svg+xml" href="${url.resourcesPath}/img/favicon.svg">
    <link rel="preload" href="${url.resourcesPath}/fonts/geist-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
    <link rel="stylesheet" href="${url.resourcesPath}/${style}">
        </#list>
    </#if>
    <#if properties.scripts?has_content>
        <#list properties.scripts?split(' ') as script>
    <script src="${url.resourcesPath}/${script}" defer></script>
        </#list>
    </#if>
</head>
<body>
<div class="shell">
<aside class="aside" aria-hidden="true">
    <span class="brand brand-light">
        <img src="${url.resourcesPath}/img/selvia-mark-128.png" alt="" width="32" height="32">
        <span>SELVIA</span>
    </span>
    <div class="aside-body">
        <h2 class="aside-title">A mentor for every software project</h2>
        <#-- A small picture of the app: plan, review, tutor. Decorative only. -->
        <div class="preview">
            <div class="mock mock-plan">
                <div class="mock-head"><span>Sprint plan</span><span class="mock-pill">3 of 5</span></div>
                <div class="mock-bar"><span style="width: 60%"></span></div>
                <ul class="mock-tasks">
                    <li class="done"><@icon name="check"/>Set up the repository</li>
                    <li class="done"><@icon name="check"/>Design the database</li>
                    <li><span class="dot"></span>Build the sign-in page</li>
                </ul>
            </div>
            <div class="mock mock-review">
                <div class="mock-head"><span>Code review</span><span class="mock-pill warn">Security</span></div>
                <div class="mock-code">
                    <span style="width: 62%"></span>
                    <span style="width: 40%"></span>
                    <span class="flag" style="width: 74%"></span>
                    <span style="width: 52%"></span>
                </div>
                <p class="mock-note">Validate this input before using it</p>
            </div>
            <div class="mock mock-tutor">
                <span class="mock-avatar"><@icon name="info"/></span>
                <p>Try splitting this into two smaller functions.</p>
            </div>
        </div>
    </div>
    <span></span>
</aside>

<main class="main">
    <a class="brand brand-mobile" href="${(client.baseUrl)!'#'}" aria-label="SELVIA">
        <img src="${url.resourcesPath}/img/selvia-mark-128.png" alt="" width="32" height="32">
        <span>SELVIA</span>
    </a>

    <div class="card">
        <h1 class="title"><#nested "header"></h1>

        <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
        <div class="alert alert-${message.type}" role="<#if message.type == 'error'>alert<#else>status</#if>">
            <#if message.type = 'success'><@icon name="check"/><#elseif message.type = 'error' || message.type = 'warning'><@icon name="alert"/><#else><@icon name="info"/></#if>
            <span>${kcSanitize(message.summary)?no_esc}</span>
        </div>
        </#if>

        <#nested "form">

        <#if displayInfo>
        <div class="card-foot"><#nested "info"></div>
        </#if>
    </div>
</main>
</div>
</body>
</html>
</#macro>
