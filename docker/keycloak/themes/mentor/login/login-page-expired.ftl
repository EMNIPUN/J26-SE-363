<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "header">
        This page has expired
    <#elseif section = "form">
        <p class="text">Your sign-in took too long. Start again to continue.</p>
        <a class="btn btn-primary" href="${url.loginRestartFlowUrl}">Start again</a>
    </#if>
</@layout.registrationLayout>
