<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password'); section>
    <#if section = "form">
        <#assign hasLoginError = messagesPerField.existsError('username','password')>
        <#if realm.loginWithEmailAllowed && !realm.registrationEmailAsUsername>
            <#assign usernameLabel = "Email or username">
        <#elseif realm.registrationEmailAsUsername>
            <#assign usernameLabel = "Email">
        <#else>
            <#assign usernameLabel = "Username">
        </#if>

        <form id="kc-form-login" class="form" action="${url.loginAction}" method="post" data-loading-form>
            <#if !usernameHidden??>
                <div class="field">
                    <label for="username" class="label">${usernameLabel}</label>
                    <div class="control">
                        <@layout.icon name="mail"/>
                        <input id="username" name="username" class="input" type="text"
                               value="${(login.username!'')}"
                               placeholder="you@university.edu"
                               autocomplete="username" autocapitalize="none" spellcheck="false"
                               required autofocus
                               <#if hasLoginError>aria-invalid="true" aria-describedby="login-error"</#if> />
                    </div>
                </div>
            </#if>

            <div class="field">
                <div class="field-head">
                    <label for="password" class="label">Password</label>
                    <#if realm.resetPasswordAllowed>
                        <a href="${url.loginResetCredentialsUrl}" class="label-link">Forgot password?</a>
                    </#if>
                </div>
                <div class="control">
                    <@layout.icon name="lock"/>
                    <input id="password" name="password" class="input has-action" type="password"
                           placeholder="Enter your password"
                           autocomplete="current-password" required
                           data-capslock="password-capslock"
                           <#if usernameHidden??>autofocus</#if>
                           <#if hasLoginError>aria-invalid="true" aria-describedby="login-error"</#if> />
                    <@layout.passwordToggle target="password"/>
                </div>
                <span id="password-capslock" class="field-hint capslock" hidden>
                    <@layout.icon name="alert-triangle"/>Caps Lock is on
                </span>
                <#if hasLoginError>
                    <span id="login-error" class="field-error" aria-live="polite">
                        <@layout.icon name="alert-circle"/>
                        <span>${kcSanitize(messagesPerField.getFirstError('username','password'))?no_esc}</span>
                    </span>
                </#if>
            </div>

            <#if realm.rememberMe && !usernameHidden??>
                <div class="form-options">
                    <label class="checkbox" for="rememberMe">
                        <input id="rememberMe" name="rememberMe" type="checkbox" <#if login.rememberMe??>checked</#if>>
                        <span>Keep me signed in on this device</span>
                    </label>
                </div>
            </#if>

            <input type="hidden" id="id-hidden-input" name="credentialId" <#if auth.selectedCredential?has_content>value="${auth.selectedCredential}"</#if>/>

            <button id="kc-login" name="login" type="submit" class="btn btn-primary" data-loading-text="Signing in…">
                <span class="spinner" aria-hidden="true"></span>
                <span class="btn-label">Sign in</span>
                <@layout.icon name="arrow-right" class="icon arrow"/>
            </button>
        </form>

        <#if realm.password && social.providers?? && social.providers?has_content>
            <div class="stack" style="margin-top: 1.25rem;">
                <div class="divider">or continue with</div>
                <div class="social-grid">
                    <#list social.providers as p>
                        <a id="social-${p.alias}" class="btn btn-secondary" href="${p.loginUrl}">${p.displayName!}</a>
                    </#list>
                </div>
            </div>
        </#if>

        <#if realm.password && realm.registrationAllowed && !registrationDisabled??>
            <div class="stack" style="margin-top: 1.25rem;">
                <div class="divider">New to SELVIA?</div>
                <a href="${url.registrationUrl}" class="btn btn-secondary">
                    <@layout.icon name="user-plus"/>
                    <span>Create an account</span>
                </a>
            </div>
        </#if>
    </#if>
</@layout.registrationLayout>
