<#import "template.ftl" as layout>

<#function fieldValue name>
    <#if profile?? && profile.attributes??>
        <#list profile.attributes as attribute>
            <#if attribute.name == name>
                <#return attribute.value!''>
            </#if>
        </#list>
    </#if>
    <#if register?? && register.formData??>
        <#return register.formData[name]!''>
    </#if>
    <#return ''>
</#function>

<#function invalid name>
    <#return messagesPerField.existsError(name)>
</#function>

<@layout.registrationLayout displayMessage=messagesPerField.exists('global') displayRequiredFields=true; section>
    <#if section = "form">
        <#assign standardFields = ["username", "email", "firstName", "lastName"]>

        <form id="kc-register-form" class="form" action="${url.registrationAction}" method="post" data-loading-form>
            <div class="form-row two">
                <div class="field">
                    <label for="firstName" class="label">First name<span class="req" aria-hidden="true">*</span></label>
                    <div class="control">
                        <@layout.icon name="user"/>
                        <input id="firstName" name="firstName" class="input" type="text"
                               value="${fieldValue('firstName')}" placeholder="Amara"
                               autocomplete="given-name" required autofocus
                               <#if invalid('firstName')>aria-invalid="true" aria-describedby="firstName-error"</#if> />
                    </div>
                    <@layout.fieldError name="firstName"/>
                </div>

                <div class="field">
                    <label for="lastName" class="label">Last name<span class="req" aria-hidden="true">*</span></label>
                    <div class="control">
                        <@layout.icon name="user"/>
                        <input id="lastName" name="lastName" class="input" type="text"
                               value="${fieldValue('lastName')}" placeholder="Silva"
                               autocomplete="family-name" required
                               <#if invalid('lastName')>aria-invalid="true" aria-describedby="lastName-error"</#if> />
                    </div>
                    <@layout.fieldError name="lastName"/>
                </div>
            </div>

            <div class="field">
                <label for="email" class="label">Email address<span class="req" aria-hidden="true">*</span></label>
                <div class="control">
                    <@layout.icon name="mail"/>
                    <input id="email" name="email" class="input" type="email"
                           value="${fieldValue('email')}" placeholder="you@university.edu"
                           autocomplete="email" autocapitalize="none" spellcheck="false" required
                           <#if invalid('email')>aria-invalid="true" aria-describedby="email-error"</#if> />
                </div>
                <#if invalid('email')>
                    <@layout.fieldError name="email"/>
                <#else>
                    <span class="field-hint">Use your university email so your lecturer can find you.</span>
                </#if>
            </div>

            <#if !realm.registrationEmailAsUsername>
                <div class="field">
                    <label for="username" class="label">Username<span class="req" aria-hidden="true">*</span></label>
                    <div class="control">
                        <@layout.icon name="at-sign"/>
                        <input id="username" name="username" class="input" type="text"
                               value="${fieldValue('username')}" placeholder="e.g. it21123456"
                               autocomplete="username" autocapitalize="none" spellcheck="false" required
                               <#if invalid('username')>aria-invalid="true" aria-describedby="username-error"</#if> />
                    </div>
                    <#if invalid('username')>
                        <@layout.fieldError name="username"/>
                    <#else>
                        <span class="field-hint">You can sign in with this or your email.</span>
                    </#if>
                </div>
            </#if>

            <#if profile?? && profile.attributes??>
                <#list profile.attributes as attribute>
                    <#if !standardFields?seq_contains(attribute.name) && !(attribute.readOnly!false)>
                        <div class="field">
                            <label for="${attribute.name}" class="label">
                                ${advancedMsg(attribute.displayName!attribute.name)}<#if attribute.required><span class="req" aria-hidden="true">*</span></#if>
                            </label>
                            <div class="control">
                                <input id="${attribute.name}" name="${attribute.name}" class="input no-icon" type="text"
                                       value="${attribute.value!''}"
                                       <#if attribute.required>required</#if>
                                       <#if invalid(attribute.name)>aria-invalid="true" aria-describedby="${attribute.name}-error"</#if> />
                            </div>
                            <@layout.fieldError name=attribute.name/>
                        </div>
                    </#if>
                </#list>
            </#if>

            <#if passwordRequired??>
                <div class="field">
                    <label for="password" class="label">Password<span class="req" aria-hidden="true">*</span></label>
                    <div class="control">
                        <@layout.icon name="lock"/>
                        <input id="password" name="password" class="input has-action" type="password"
                               placeholder="Create a password"
                               autocomplete="new-password" required
                               data-strength="password-strength"
                               data-capslock="password-capslock"
                               <#if invalid('password')>aria-invalid="true" aria-describedby="password-error"</#if> />
                        <@layout.passwordToggle target="password"/>
                    </div>
                    <span id="password-capslock" class="field-hint capslock" hidden>
                        <@layout.icon name="alert-triangle"/>Caps Lock is on
                    </span>
                    <@layout.fieldError name="password"/>
                    <div id="password-strength" class="strength" data-score="0" aria-live="polite">
                        <div class="strength-bar" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
                        <div class="strength-meta">
                            <span>Password strength</span>
                            <span class="strength-label" data-strength-label>Not set</span>
                        </div>
                        <ul class="checklist">
                            <li data-rule="length">At least 8 characters</li>
                            <li data-rule="case">Upper &amp; lower case</li>
                            <li data-rule="number">A number</li>
                            <li data-rule="symbol">A symbol</li>
                        </ul>
                    </div>
                </div>

                <div class="field">
                    <label for="password-confirm" class="label">Confirm password<span class="req" aria-hidden="true">*</span></label>
                    <div class="control">
                        <@layout.icon name="lock"/>
                        <input id="password-confirm" name="password-confirm" class="input has-action" type="password"
                               placeholder="Re-enter your password"
                               autocomplete="new-password" required
                               data-match="password" data-match-hint="password-match"
                               <#if invalid('password-confirm')>aria-invalid="true" aria-describedby="password-confirm-error"</#if> />
                        <@layout.passwordToggle target="password-confirm"/>
                    </div>
                    <@layout.fieldError name="password-confirm"/>
                    <span id="password-match" class="field-hint" hidden></span>
                </div>
            </#if>

            <#if termsAcceptanceRequired??>
                <div class="field">
                    <label class="checkbox" for="termsAccepted">
                        <input type="checkbox" id="termsAccepted" name="termsAccepted" required
                               <#if invalid('termsAccepted')>aria-invalid="true"</#if> />
                        <span>${msg("acceptTerms")}</span>
                    </label>
                    <@layout.fieldError name="termsAccepted"/>
                </div>
            </#if>

            <#if recaptchaRequired?? && (recaptchaVisible!true)>
                <div class="g-recaptcha" data-size="compact" data-sitekey="${recaptchaSiteKey}" data-action="${recaptchaAction!''}"></div>
            </#if>

            <button id="kc-register" type="submit" class="btn btn-primary" data-loading-text="Creating your account…">
                <span class="spinner" aria-hidden="true"></span>
                <span class="btn-label">Create account</span>
                <@layout.icon name="arrow-right" class="icon arrow"/>
            </button>

            <p class="terms">
                By creating an account you agree to use SELVIA responsibly for your coursework.
            </p>
        </form>

        <div class="stack" style="margin-top: 1.25rem;">
            <div class="divider">Already have an account?</div>
            <a href="${url.loginUrl}" class="btn btn-secondary">
                <@layout.icon name="arrow-left"/>
                <span>Back to sign in</span>
            </a>
        </div>
    </#if>
</@layout.registrationLayout>
