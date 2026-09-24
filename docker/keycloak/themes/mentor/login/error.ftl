<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "form">
        <div id="kc-error-wrapper" class="content-area" style="text-align: center; padding: 1rem 0;">
            <p style="color: #f87171; font-size: 0.95rem; line-height: 1.5; margin-bottom: 1.5rem;">
                ${message.summary}
            </p>

            <#if client?? && client.baseUrl?has_content>
                <a href="${client.baseUrl}" class="btn-submit" style="display: inline-flex; align-items: center; justify-content: center; text-decoration: none; width: 100%;">
                    <span>Return to Application</span>
                </a>
            <#else>
                <a href="${url.loginUrl}" class="btn-submit" style="display: inline-flex; align-items: center; justify-content: center; text-decoration: none; width: 100%;">
                    <span>Back to Sign In</span>
                </a>
            </#if>
        </div>
    </#if>
</@layout.registrationLayout>
