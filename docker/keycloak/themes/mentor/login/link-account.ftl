<#import "template.ftl" as layout>
<#--
  Shown when someone signs in with a provider (Google, GitHub...) and an account with that email
  already exists. It only shows who is signing in: nothing here can be edited. Linking needs the
  code that is emailed from the next step.
-->
<@layout.registrationLayout displayMessage=true; section>
    <#if section = "header">
        Link your account
    <#elseif section = "form">
        <div class="profile">
            <#if profilePicture?has_content>
                <img class="avatar" src="${profilePicture}" alt="" width="48" height="48" referrerpolicy="no-referrer">
            <#else>
                <span class="avatar avatar-initials" aria-hidden="true">${profileInitials}</span>
            </#if>
            <div class="profile-text">
                <p class="profile-name">${profileName}</p>
                <p class="profile-email">${profileEmail}</p>
                <p class="profile-source">${providerName}</p>
            </div>
        </div>
        <p class="text">An account with this email already exists. To link ${providerName} to it, we send a code to ${accountEmail}.</p>
        <form id="kc-link-form" class="form" action="${url.loginAction}" method="post">
            <button class="btn btn-primary" type="submit" name="action" value="send" data-busy-label="Sending…">Send code</button>
        </form>
    <#elseif section = "info">
        Not you? <a href="${url.loginRestartFlowUrl}">Use a different account</a>
    </#if>
</@layout.registrationLayout>
