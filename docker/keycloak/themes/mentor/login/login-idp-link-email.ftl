<#import "template.ftl" as layout>
<@layout.registrationLayout; section>
    <#if section = "header">
        ${msg("emailLinkIdpTitle", idpDisplayName)}
    <#elseif section = "form">
        <p class="text">${msg("emailLinkIdp1", idpDisplayName, brokerContext.username, realm.displayName)}</p>
        <p class="text">${msg("emailLinkIdp2")} <a href="${url.loginAction}">${msg("doClickHere")}</a> ${msg("emailLinkIdp3")}</p>
        <p class="text">${msg("emailLinkIdp4")} <a href="${url.loginAction}">${msg("doClickHere")}</a> ${msg("emailLinkIdp5")}</p>
    </#if>
</@layout.registrationLayout>
