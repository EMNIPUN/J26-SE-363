<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "form">
        <div id="kc-error-wrapper" class="form">
            <div class="alert alert-error" role="alert">
                <@layout.icon name="alert-circle"/>
                <span>${kcSanitize(message.summary)?no_esc}</span>
            </div>

            <#if !skipLink?? && client?? && client.baseUrl?has_content>
                <a href="${client.baseUrl}" class="btn btn-primary">
                    <span>Return to SELVIA</span>
                    <@layout.icon name="arrow-right" class="icon arrow"/>
                </a>
            </#if>
            <a href="${url.loginUrl}" class="back-link">
                <@layout.icon name="arrow-left"/>
                <span>Back to sign in</span>
            </a>
        </div>
    </#if>
</@layout.registrationLayout>
