<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password'); section>
    <#if section = "form">
        <form id="kc-form-login" onsubmit="document.getElementById('kc-login').disabled = true; return true;" action="${url.loginAction}" method="post" class="login-form">
            <!-- Username or Email Field -->
            <div class="field-group">
                <label for="username" class="field-label">Email or Username</label>
                <div class="input-wrapper">
                    <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect width="20" height="16" x="2" y="4" rx="2"></rect>
                        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"></path>
                    </svg>
                    <input tabindex="1" id="username" class="text-input" name="username" value="${(login.username!'')}" type="text" autofocus autocomplete="username" placeholder="name@organization.com" required />
                </div>
            </div>

            <!-- Password Field -->
            <div class="field-group">
                <div class="field-label-row">
                    <label for="password" class="field-label">Password</label>
                    <#if realm.resetPasswordAllowed>
                        <a tabindex="5" href="${url.loginResetCredentialsUrl}" class="link-forgot">Forgot password?</a>
                    </#if>
                </div>
                <div class="input-wrapper">
                    <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect width="18" height="11" x="3" y="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                    </svg>
                    <input tabindex="2" id="password" class="text-input text-input-pass" name="password" type="password" autocomplete="current-password" placeholder="••••••••" required />
                    <button type="button" class="btn-toggle-pass" onclick="togglePasswordVisibility()" aria-label="Toggle password visibility">
                        <svg id="eye-icon" class="eye-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                    </button>
                </div>
            </div>

            <!-- Remember Me Checkbox -->
            <#if realm.rememberMe && !usernameHidden??>
                <div class="checkbox-row">
                    <label class="checkbox-label">
                        <input tabindex="3" id="rememberMe" name="rememberMe" type="checkbox" <#if login.rememberMe??>checked</#if>>
                        <span>Remember this device</span>
                    </label>
                </div>
            </#if>

            <!-- Submit Button -->
            <button tabindex="4" class="btn-submit" name="login" id="kc-login" type="submit">
                <span>Sign in</span>
                <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M5 12h14"></path>
                    <path d="m12 5 7 7-7 7"></path>
                </svg>
            </button>

            <!-- Registration Link -->
            <#if realm.password && realm.registrationAllowed && !registrationDisabled??>
                <div class="signup-prompt">
                    <span>Don't have an account?</span>
                    <a tabindex="6" href="${url.registrationUrl}" class="link-signup">Sign up</a>
                </div>
            </#if>
        </form>

        <script>
            function togglePasswordVisibility() {
                var input = document.getElementById("password");
                if (input.type === "password") {
                    input.type = "text";
                } else {
                    input.type = "password";
                }
            }
        </script>
    </#if>
</@layout.registrationLayout>
