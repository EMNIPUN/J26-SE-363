<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "form">
        <form id="kc-logout-confirm" class="form" action="${url.logoutConfirmAction}" method="POST" data-loading-form>
            <input type="hidden" name="session_code" value="${logoutConfirm.code}">

            <button id="kc-logout" name="confirmLogout" type="submit" class="btn btn-primary" data-loading-text="Signing out…">
                <span class="spinner" aria-hidden="true"></span>
                <@layout.icon name="log-out" class="icon arrow"/>
                <span class="btn-label">Sign out</span>
            </button>

            <#if !logoutConfirm.skipLink && (client.baseUrl)?has_content>
                <a href="${client.baseUrl}" class="btn btn-ghost">Stay signed in</a>
            </#if>
        </form>
    </#if>
</@layout.registrationLayout>
