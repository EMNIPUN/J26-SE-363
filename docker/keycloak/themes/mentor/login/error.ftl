<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "header">
        Something went wrong
    <#elseif section = "form">
        <p class="text">${(message.summary)!'Please try again.'}</p>
        <#if client?? && client.baseUrl?has_content>
            <a class="btn btn-outline" href="${client.baseUrl}">Back to the app</a>
        <#else>
            <a class="btn btn-outline" href="${url.loginUrl!'#'}">Back to sign in</a>
        </#if>
    </#if>
</@layout.registrationLayout>
