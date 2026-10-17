<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password') displayInfo=(realm.password && realm.registrationAllowed && !registrationDisabled??); section>
    <#if section = "header">
        Sign in
    <#elseif section = "form">
        <#assign loginError = messagesPerField.existsError('username','password')>
        <@layout.socialProviders/>
        <form id="kc-form-login" class="form" action="${url.loginAction}" method="post">
            <#if !usernameHidden??>
                <div class="field">
                    <label for="username" class="label"><#if realm.loginWithEmailAllowed && !realm.registrationEmailAsUsername>Email or username<#else>Email</#if></label>
                    <input id="username" name="username" class="input" type="text" value="${(login.username!'')}"
                           autocomplete="username" autocapitalize="none" spellcheck="false" required autofocus
                           <#if loginError>aria-invalid="true"</#if>>
                </div>
            </#if>
            <div class="field">
                <div class="field-head">
                    <label for="password" class="label">Password</label>
                    <#if realm.resetPasswordAllowed>
                        <a class="small-link" href="${url.loginResetCredentialsUrl}">Forgot password?</a>
                    </#if>
                </div>
                <div class="control">
                    <input id="password" name="password" class="input has-action" type="password"
                           autocomplete="current-password" required <#if usernameHidden??>autofocus</#if>
                           <#if loginError>aria-invalid="true"</#if>>
                    <@layout.passwordToggle target="password"/>
                </div>
                <#if loginError>
                    <p class="field-error" aria-live="polite">${kcSanitize(messagesPerField.getFirstError('username','password'))?no_esc}</p>
                </#if>
            </div>
            <input type="hidden" name="credentialId" <#if auth.selectedCredential?has_content>value="${auth.selectedCredential}"</#if>>
            <button id="kc-login" class="btn btn-primary" type="submit" data-busy-label="Signing in…">Sign in</button>
        </form>
    <#elseif section = "info">
        New to SELVIA? <a href="${url.registrationUrl}">Create an account</a>
    </#if>
</@layout.registrationLayout>
