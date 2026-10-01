<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('password','password-confirm'); section>
    <#if section = "form">
        <form id="kc-passwd-update-form" class="form" action="${url.loginAction}" method="post" data-loading-form>
            <input type="text" id="username" name="username" value="${(username!'')}" autocomplete="username" readonly hidden />

            <div class="field">
                <label for="password-new" class="label">New password</label>
                <div class="control">
                    <@layout.icon name="lock"/>
                    <input id="password-new" name="password-new" class="input has-action" type="password"
                           placeholder="Create a new password"
                           autocomplete="new-password" required autofocus
                           data-strength="password-strength"
                           data-capslock="password-capslock"
                           <#if messagesPerField.existsError('password')>aria-invalid="true" aria-describedby="password-error"</#if> />
                    <@layout.passwordToggle target="password-new"/>
                </div>
                <span id="password-capslock" class="field-hint capslock" hidden>
                    <@layout.icon name="alert-triangle"/>Caps Lock is on
                </span>
                <@layout.fieldError name="password"/>
                <div id="password-strength" class="strength" data-score="0" aria-live="polite">
                    <div class="strength-bar" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
                    <div class="strength-meta">
                        <span>Password strength</span>
                        <span class="strength-label" data-strength-label>Not set</span>
                    </div>
                    <ul class="checklist">
                        <li data-rule="length">At least 8 characters</li>
                        <li data-rule="case">Upper &amp; lower case</li>
                        <li data-rule="number">A number</li>
                        <li data-rule="symbol">A symbol</li>
                    </ul>
                </div>
            </div>

            <div class="field">
                <label for="password-confirm" class="label">Confirm new password</label>
                <div class="control">
                    <@layout.icon name="lock"/>
                    <input id="password-confirm" name="password-confirm" class="input has-action" type="password"
                           placeholder="Re-enter your new password"
                           autocomplete="new-password" required
                           data-match="password-new" data-match-hint="password-match"
                           <#if messagesPerField.existsError('password-confirm')>aria-invalid="true" aria-describedby="password-confirm-error"</#if> />
                    <@layout.passwordToggle target="password-confirm"/>
                </div>
                <@layout.fieldError name="password-confirm"/>
                <span id="password-match" class="field-hint" hidden></span>
            </div>

            <label class="checkbox" for="logout-sessions">
                <input type="checkbox" id="logout-sessions" name="logout-sessions" value="on" checked>
                <span>Sign out of all other devices</span>
            </label>

            <div class="stack">
                <button id="kc-update-password" type="submit" class="btn btn-primary" data-loading-text="Saving…">
                    <span class="spinner" aria-hidden="true"></span>
                    <span class="btn-label">Save new password</span>
                    <@layout.icon name="arrow-right" class="icon arrow"/>
                </button>
                <#if isAppInitiatedAction??>
                    <button type="submit" name="cancel-aia" value="true" class="btn btn-ghost" formnovalidate>Cancel</button>
                </#if>
            </div>
        </form>
    </#if>
</@layout.registrationLayout>
