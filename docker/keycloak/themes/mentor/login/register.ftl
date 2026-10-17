<#import "template.ftl" as layout>

<#function fieldValue name>
    <#if register?? && register.formData??>
        <#return register.formData[name]!''>
    </#if>
    <#return ''>
</#function>

<#--
  Three steps in one form (details, password, terms). Without JavaScript every step is shown at once.
  The agreement box has no name on purpose: it only gates the button. The agreement that counts is
  recorded by the app during onboarding (consent version and time).
-->
<@layout.registrationLayout displayMessage=messagesPerField.exists('global') displayInfo=true; section>
    <#if section = "header">
        Create your account
    <#elseif section = "form">
        <form id="kc-register-form" class="form" action="${url.registrationAction}" method="post" data-steps>
            <div class="progress" data-progress hidden>
                <div class="progress-bar"><span></span><span></span><span></span></div>
                <p class="progress-label" data-progress-label></p>
            </div>

            <fieldset class="step" data-step data-title="Your details">
                <@layout.socialProviders/>
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
                <div class="nav" data-nav>
                    <button class="btn btn-primary" type="button" data-next>Continue</button>
                </div>
            </fieldset>

            <fieldset class="step" data-step data-title="Password">
                <div class="field">
                    <label for="password" class="label">Password</label>
                    <div class="control">
                        <input id="password" name="password" class="input has-action" type="password"
                               autocomplete="new-password" minlength="10" required
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
                <div class="nav" data-nav>
                    <button class="btn btn-outline btn-back" type="button" data-back>Back</button>
                    <button class="btn btn-primary" type="button" data-next>Continue</button>
                </div>
            </fieldset>

            <fieldset class="step" data-step data-title="Terms">
                <p class="text" data-summary hidden>Creating an account for <strong data-summary-email></strong></p>
                <label class="check">
                    <input id="terms" type="checkbox" required>
                    <span>I agree to the
                        <#if properties.termsUrl?has_content>
                            <a href="${properties.termsUrl}" target="_blank" rel="noopener noreferrer">terms of use and privacy policy</a>
                        <#else>
                            terms of use and privacy policy
                        </#if>
                    </span>
                </label>
                <div class="nav" data-nav>
                    <button class="btn btn-outline btn-back" type="button" data-back>Back</button>
                    <button class="btn btn-primary" type="submit" data-busy-label="Creating account…">Create account</button>
                </div>
            </fieldset>
        </form>
    <#elseif section = "info">
        Already have an account? <a href="${url.loginUrl}">Sign in</a>
    </#if>
</@layout.registrationLayout>
