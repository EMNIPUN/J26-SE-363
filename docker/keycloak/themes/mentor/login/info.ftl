<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "header">
        <#if messageHeader??>${messageHeader}<#else>Notice</#if>
    <#elseif section = "form">
        <p class="text">${(message.summary)!''}<#if requiredActions??><#list requiredActions><b><#items as reqActionItem> ${kcSanitize(msg("requiredAction.${reqActionItem}"))?no_esc}<#sep>, </#items></b></#list></#if></p>
        <#if skipLink??>
        <#elseif pageRedirectUri?has_content>
            <a class="btn btn-primary" href="${pageRedirectUri}">Back to the app</a>
        <#elseif actionUri?has_content>
            <a class="btn btn-primary" href="${actionUri}">Continue</a>
        <#elseif (client.baseUrl)?has_content>
            <a class="btn btn-primary" href="${client.baseUrl}">Back to the app</a>
        </#if>
    </#if>
</@layout.registrationLayout>
