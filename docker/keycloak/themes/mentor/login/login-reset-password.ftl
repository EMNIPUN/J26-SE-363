<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username'); section>
    <#if section = "form">
        <#if realm.loginWithEmailAllowed && !realm.registrationEmailAsUsername>
            <#assign usernameLabel = "Email or username">
        <#elseif realm.registrationEmailAsUsername>
            <#assign usernameLabel = "Email">
        <#else>
            <#assign usernameLabel = "Username">
        </#if>

        <form id="kc-reset-password-form" class="form" action="${url.loginAction}" method="post" data-loading-form>
            <div class="field">
                <label for="username" class="label">${usernameLabel}</label>
                <div class="control">
                    <@layout.icon name="mail"/>
                    <input id="username" name="username" class="input" type="text"
                           value="${(auth.attemptedUsername!'')}"
                           placeholder="you@university.edu"
                           autocomplete="username" autocapitalize="none" spellcheck="false"
                           required autofocus
                           <#if messagesPerField.existsError('username')>aria-invalid="true" aria-describedby="username-error"</#if> />
                </div>
                <#if messagesPerField.existsError('username')>
                    <@layout.fieldError name="username"/>
                <#else>
                    <span class="field-hint">
                        <@layout.icon name="info"/>
                        <span>The link expires shortly, so check your inbox (and spam folder) soon.</span>
                    </span>
                </#if>
            </div>

            <button id="kc-reset-submit" type="submit" class="btn btn-primary" data-loading-text="Sending link…">
                <span class="spinner" aria-hidden="true"></span>
                <span class="btn-label">Send reset link</span>
                <@layout.icon name="arrow-right" class="icon arrow"/>
            </button>

            <a href="${url.loginUrl}" class="back-link">
                <@layout.icon name="arrow-left"/>
                <span>Back to sign in</span>
            </a>
        </form>
    </#if>
</@layout.registrationLayout>
