<#import "template.ftl" as layout>
<@layout.registrationLayout; section>
    <#if section = "header">
        ${msg("confirmLinkIdpTitle")}
    <#elseif section = "form">
        <form id="kc-register-form" class="actions" action="${url.loginAction}" method="post">
            <button class="btn btn-primary" type="submit" name="submitAction" value="linkAccount">${msg("confirmLinkIdpContinue", idpDisplayName)}</button>
            <button class="btn btn-outline" type="submit" name="submitAction" value="updateProfile">${msg("confirmLinkIdpReviewProfile")}</button>
        </form>
    </#if>
</@layout.registrationLayout>
