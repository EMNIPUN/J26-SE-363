<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "form">
        <div id="kc-logout-confirm" class="content-area">
            <p class="logout-description" style="color: #a1a1aa; font-size: 0.925rem; line-height: 1.5; margin-bottom: 1.5rem; text-align: center;">
                Are you sure you want to log out of your MENTOR workspace session?
            </p>

            <form class="form-actions" action="${url.logoutConfirmAction}" method="POST" style="display: flex; flex-direction: column; gap: 0.85rem;">
                <input type="hidden" name="session_code" value="${logoutConfirm.code}">
                
                <button tabindex="1" class="btn-submit" name="confirmLogout" id="kc-logout" type="submit" style="width: 100%; cursor: pointer;">
                    <span>Confirm Sign Out</span>
                    <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                        <polyline points="16 17 21 12 16 7"></polyline>
                        <line x1="21" y1="12" x2="9" y2="12"></line>
                    </svg>
                </button>

                <#if (client.baseUrl)??>
                    <a href="${client.baseUrl}" style="display: block; text-align: center; font-size: 0.85rem; color: #71717a; text-decoration: none; padding: 0.5rem; transition: color 0.15s;" onmouseover="this.style.color='#f4f4f5'" onmouseout="this.style.color='#71717a'">
                        Cancel and return to application
                    </a>
                </#if>
            </form>
        </div>
    </#if>
</@layout.registrationLayout>
