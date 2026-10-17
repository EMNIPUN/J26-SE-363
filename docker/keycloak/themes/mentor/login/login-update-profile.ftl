<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=messagesPerField.exists('global'); section>
    <#if section = "header">
        Confirm your details
    <#elseif section = "form">
        <form id="kc-update-profile-form" class="form" action="${url.loginAction}" method="post">
            <#if profile?? && profile.attributes??>
                <#list profile.attributes as attribute>
                    <#if attribute.name != "username" || !realm.registrationEmailAsUsername>
                    <div class="field">
                        <label for="${attribute.name}" class="label">${attribute.displayName!attribute.name}</label>
                        <input id="${attribute.name}" name="${attribute.name}" class="input"
                               type="<#if attribute.name == 'email'>email<#else>text</#if>" value="${attribute.value!''}"
                               <#if attribute.required>required</#if> <#if attribute.readOnly>readonly</#if>
                               <#if messagesPerField.existsError(attribute.name)>aria-invalid="true"</#if>>
                        <@layout.fieldError name=attribute.name/>
                    </div>
                    </#if>
                </#list>
            </#if>
            <div class="actions">
                <button class="btn btn-primary" type="submit" data-busy-label="Saving…">Continue</button>
                <#if isAppInitiatedAction??>
                    <button class="btn btn-outline" type="submit" name="cancel-aia" value="true" formnovalidate>Cancel</button>
                </#if>
            </div>
        </form>
    </#if>
</@layout.registrationLayout>
