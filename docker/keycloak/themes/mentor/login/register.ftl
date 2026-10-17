<#import "template.ftl" as layout>

<#function fieldValue name>
    <#if register?? && register.formData??>
        <#return register.formData[name]!''>
    </#if>
    <#return ''>
</#function>

<@layout.registrationLayout displayMessage=messagesPerField.exists('global') displayInfo=true; section>
    <#if section = "header">
        Create your account
    <#elseif section = "form">
        <@layout.socialProviders/>
        <form id="kc-register-form" class="form" action="${url.registrationAction}" method="post">
            <div class="row">
                <div class="field">
                    <label for="firstName" class="label">First name</label>
                    <input id="firstName" name="firstName" class="input" type="text" value="${fieldValue('firstName')}"
                           autocomplete="given-name" required autofocus
                           <#if messagesPerField.existsError('firstName')>aria-invalid="true"</#if>>
                    <@layout.fieldError name="firstName"/>
                </div>
                <div class="field">
                    <label for="lastName" class="label">Last name</label>
                    <input id="lastName" name="lastName" class="input" type="text" value="${fieldValue('lastName')}"
                           autocomplete="family-name" required
                           <#if messagesPerField.existsError('lastName')>aria-invalid="true"</#if>>
                    <@layout.fieldError name="lastName"/>
                </div>
            </div>
            <div class="field">
                <label for="email" class="label">Email</label>
                <input id="email" name="email" class="input" type="email" value="${fieldValue('email')}"
                       autocomplete="email" autocapitalize="none" spellcheck="false" required
                       <#if messagesPerField.existsError('email','username')>aria-invalid="true"</#if>>
                <@layout.fieldError name="email"/>
                <#if !messagesPerField.existsError('email')><@layout.fieldError name="username"/></#if>
            </div>
            <div class="field">
                <label for="password" class="label">Password</label>
                <div class="control">
                    <input id="password" name="password" class="input has-action" type="password"
                           autocomplete="new-password" required
                           <#if messagesPerField.existsError('password')>aria-invalid="true"</#if>>
                    <@layout.passwordToggle target="password"/>
                </div>
                <@layout.fieldError name="password"/>
                <p class="hint">At least 10 characters.</p>
            </div>
            <div class="field">
                <label for="password-confirm" class="label">Confirm password</label>
                <input id="password-confirm" name="password-confirm" class="input" type="password"
                       autocomplete="new-password" required
                       <#if messagesPerField.existsError('password-confirm')>aria-invalid="true"</#if>>
                <@layout.fieldError name="password-confirm"/>
            </div>
            <button class="btn btn-primary" type="submit" data-busy-label="Creating account…">Create account</button>
        </form>
    <#elseif section = "info">
        Already have an account? <a href="${url.loginUrl}">Sign in</a>
    </#if>
</@layout.registrationLayout>
