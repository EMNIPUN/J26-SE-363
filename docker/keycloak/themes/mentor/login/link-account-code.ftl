<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=true displayInfo=true; section>
    <#if section = "header">
        Enter the code
    <#elseif section = "form">
        <p class="text">We sent a 6 digit code to <strong>${maskedEmail}</strong>. It works for 10 minutes.</p>
        <form id="kc-code-form" class="form" action="${url.loginAction}" method="post">
            <div class="field">
                <label for="code" class="label">Code</label>
                <input id="code" name="code" class="input code-input" type="text" inputmode="numeric"
                       autocomplete="one-time-code" maxlength="7" pattern="[0-9 ]{6,7}" required autofocus
                       <#if message?has_content && message.type = 'error'>aria-invalid="true"</#if>>
            </div>
            <button class="btn btn-primary" type="submit" name="action" value="verify" data-busy-label="Checking…">Link account</button>
        </form>
        <#if canResend>
            <form class="form resend" action="${url.loginAction}" method="post">
                <button class="btn btn-outline" type="submit" name="action" value="resend" formnovalidate
                        <#if secondsUntilResend gt 0>disabled</#if> data-busy-label="Sending…">
                    Send a new code<#if secondsUntilResend gt 0> (in ${secondsUntilResend}s)</#if>
                </button>
            </form>
        </#if>
    <#elseif section = "info">
        Not you? <a href="${url.loginRestartFlowUrl}">Use a different account</a>
    </#if>
</@layout.registrationLayout>
