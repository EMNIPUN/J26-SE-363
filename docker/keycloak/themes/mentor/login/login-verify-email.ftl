<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=true; section>
    <#if section = "header">
        Verify your email
    <#elseif section = "form">
        <p class="text">We sent a link to <strong>${(user.email)!''}</strong>. Open it to continue.</p>
        <form class="form" action="${url.loginAction}" method="post">
            <button class="btn btn-outline" type="submit" data-busy-label="Sending…">Send it again</button>
        </form>
    <#elseif section = "info">
        <a href="${url.loginRestartFlowUrl}">Back to sign in</a>
    </#if>
</@layout.registrationLayout>
