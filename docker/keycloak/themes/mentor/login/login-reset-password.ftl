<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username') displayInfo=true; section>
    <#if section = "header">
        Reset your password
    <#elseif section = "form">
        <p class="text">Enter your email and we will send you a link to choose a new password.</p>
        <form id="kc-reset-password-form" class="form" action="${url.loginAction}" method="post">
            <div class="field">
                <label for="username" class="label">Email</label>
                <input id="username" name="username" class="input" type="text" value="${(auth.attemptedUsername!'')}"
                       autocomplete="username" autocapitalize="none" spellcheck="false" required autofocus
                       <#if messagesPerField.existsError('username')>aria-invalid="true"</#if>>
                <@layout.fieldError name="username"/>
            </div>
            <button class="btn btn-primary" type="submit" data-busy-label="Sending…">Send link</button>
        </form>
    <#elseif section = "info">
        <a href="${url.loginUrl}">Back to sign in</a>
    </#if>
</@layout.registrationLayout>
