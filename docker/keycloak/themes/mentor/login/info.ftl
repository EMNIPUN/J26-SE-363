<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "form">
        <div id="kc-info-wrapper" class="form">
            <p class="notice-text">
                ${kcSanitize(message.summary)?no_esc}<#if requiredActions??>: <strong><#list requiredActions as reqActionItem>${kcSanitize(msg("requiredAction.${reqActionItem}"))?no_esc}<#sep>, </#list></strong></#if>
            </p>

            <#if skipLink??>
            <#elseif pageRedirectUri?has_content>
                <a href="${pageRedirectUri}" class="btn btn-primary">
                    <span>Continue</span>
                    <@layout.icon name="arrow-right" class="icon arrow"/>
                </a>
            <#elseif actionUri?has_content>
                <a href="${actionUri}" class="btn btn-primary">
                    <span>Continue</span>
                    <@layout.icon name="arrow-right" class="icon arrow"/>
                </a>
            <#elseif (client.baseUrl)?has_content>
                <a href="${client.baseUrl}" class="btn btn-primary">
                    <span>Return to SELVIA</span>
                    <@layout.icon name="arrow-right" class="icon arrow"/>
                </a>
            <#else>
                <a href="${url.loginUrl}" class="back-link">
                    <@layout.icon name="arrow-left"/>
                    <span>Back to sign in</span>
                </a>
            </#if>
        </div>
    </#if>
</@layout.registrationLayout>
