<#import "template.ftl" as layout>
<@layout.emailLayout>
<p><strong>Your code</strong></p>
<p style="margin:20px 0;font-size:28px;letter-spacing:6px;font-weight:700;color:#18181b">${code}</p>
<p>Enter it to link your ${provider} sign-in to your SELVIA account. It works for ${minutes} minutes.</p>
<p style="font-size:12px;color:#6b7280">If you did not try to sign in, ignore this email. Nothing is linked without this code.</p>
</@layout.emailLayout>
