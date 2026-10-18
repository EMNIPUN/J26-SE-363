<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('password','password-confirm'); section>
    <#if section = "header">
        Choose a new password
    <#elseif section = "form">
        <form id="kc-passwd-update-form" class="form" action="${url.loginAction}" method="post">
            <input type="text" name="username" value="${username!''}" autocomplete="username" readonly hidden>
            <div class="field">
                <label for="password-new" class="label">New password</label>
                <div class="control">
                    <input id="password-new" name="password-new" class="input has-action" type="password"
                           autocomplete="new-password" required autofocus
                           <#if messagesPerField.existsError('password')>aria-invalid="true"</#if>>
                    <@layout.passwordToggle target="password-new"/>
                </div>
                <@layout.fieldError name="password"/>
            </div>
            <div class="field">
                <label for="password-confirm" class="label">Confirm password</label>
                <input id="password-confirm" name="password-confirm" class="input" type="password"
                       autocomplete="new-password" required
                       <#if messagesPerField.existsError('password-confirm')>aria-invalid="true"</#if>>
                <@layout.fieldError name="password-confirm"/>
            </div>
            <#if isAppInitiatedAction??><input type="hidden" name="logout-sessions" value="on"></#if>
            <div class="actions">
                <button class="btn btn-primary" type="submit" data-busy-label="Saving…">Update password</button>
                <#if isAppInitiatedAction??>
                    <button class="btn btn-outline" type="submit" name="cancel-aia" value="true" formnovalidate>Cancel</button>
                </#if>
            </div>
        </form>
    </#if>
</@layout.registrationLayout>
