package org.selvia.keycloak;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Locale;
import org.keycloak.broker.provider.BrokeredIdentityContext;

/**
 * What the provider told Keycloak about the person who just signed in, for showing only.
 * Nothing here can be edited by the person.
 */
record ProfileInfo(String name, String email, String picture) {

    private static final String[] PICTURE_FIELDS = {"picture", "avatar_url", "photo", "image"};

    static ProfileInfo from(BrokeredIdentityContext context) {
        String first = nullToEmpty(context.getFirstName());
        String last = nullToEmpty(context.getLastName());
        String name = (first + " " + last).trim();
        if (name.isEmpty()) name = nullToEmpty(context.getUsername());
        return new ProfileInfo(name, nullToEmpty(context.getEmail()), findPicture(context));
    }

    /** The provider's own profile data (OIDC user info, GitHub's user object) may carry a picture URL. */
    private static String findPicture(BrokeredIdentityContext context) {
        for (Object value : context.getContextData().values()) {
            if (value instanceof JsonNode node) {
                for (String field : PICTURE_FIELDS) {
                    JsonNode picture = node.get(field);
                    if (picture != null && picture.isTextual() && isWebAddress(picture.asText())) {
                        return picture.asText();
                    }
                }
            }
        }
        for (String field : PICTURE_FIELDS) {
            String attribute = context.getUserAttribute(field);
            if (attribute != null && isWebAddress(attribute)) return attribute;
        }
        return "";
    }

    /** Only http(s) addresses are shown as images, so nothing else can end up in the page. */
    static boolean isWebAddress(String value) {
        String lower = value.toLowerCase(Locale.ROOT);
        return lower.startsWith("https://") || lower.startsWith("http://");
    }

    String initials() {
        StringBuilder out = new StringBuilder();
        for (String part : name.split("\\s+")) {
            if (!part.isEmpty() && out.length() < 2) out.append(Character.toUpperCase(part.charAt(0)));
        }
        return out.length() == 0 ? "?" : out.toString();
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }
}
