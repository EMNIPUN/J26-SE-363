<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=messagesPerField.exists('global'); section>
    <#if section = "header">
        Confirm your details
    <#elseif section = "form">
        <@layout.profileForm/>
    </#if>
</@layout.registrationLayout>
