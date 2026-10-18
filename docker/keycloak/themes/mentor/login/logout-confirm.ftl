<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "header">
        Sign out
    <#elseif section = "form">
        <p class="text">Do you want to sign out of SELVIA?</p>
        <form class="actions" action="${url.logoutConfirmAction}" method="post">
            <input type="hidden" name="session_code" value="${logoutConfirm.code}">
            <button class="btn btn-primary" type="submit" name="confirmLogout" value="Logout">Sign out</button>
            <#if (client.baseUrl)?has_content>
                <a class="btn btn-outline" href="${client.baseUrl}">Stay signed in</a>
            </#if>
        </form>
    </#if>
</@layout.registrationLayout>
