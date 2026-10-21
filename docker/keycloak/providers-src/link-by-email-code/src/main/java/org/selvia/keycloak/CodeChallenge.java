package org.selvia.keycloak;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.HexFormat;

/**
 * A six digit code that was emailed to someone, and how many times they may try it.
 *
 * Only a salted hash of the code is kept (in the login session), never the code itself. A
 * challenge is immutable: checking a guess returns the challenge to keep for the next try.
 */
final class CodeChallenge {

    static final int DIGITS = 6;
    static final long TTL_MS = 10 * 60 * 1000L;
    static final int MAX_ATTEMPTS = 5;
    static final long RESEND_AFTER_MS = 60 * 1000L;
    static final int MAX_SENDS = 3;

    enum Outcome { OK, WRONG, EXPIRED, LOCKED }

    /** A new challenge and the code to email. */
    record Issued(CodeChallenge challenge, String code) {}

    /** The answer to a guess, and the challenge to keep. */
    record Check(Outcome outcome, CodeChallenge next) {}

    private final String salt;
    private final String hash;
    private final long expiresAt;
    private final long sentAt;
    private final int attempts;
    private final int sends;

    private CodeChallenge(String salt, String hash, long expiresAt, long sentAt, int attempts, int sends) {
        this.salt = salt;
        this.hash = hash;
        this.expiresAt = expiresAt;
        this.sentAt = sentAt;
        this.attempts = attempts;
        this.sends = sends;
    }

    /** A fresh code. `previous` (or null) carries how many codes have been sent already. */
    static Issued issue(CodeChallenge previous, long now, SecureRandom random) {
        int bound = (int) Math.pow(10, DIGITS);
        String code = String.format("%0" + DIGITS + "d", random.nextInt(bound));
        byte[] saltBytes = new byte[16];
        random.nextBytes(saltBytes);
        String salt = HexFormat.of().formatHex(saltBytes);
        int sends = previous == null ? 1 : previous.sends + 1;
        return new Issued(new CodeChallenge(salt, hash(salt, code), now + TTL_MS, now, 0, sends), code);
    }

    Check check(String guess, long now) {
        if (attempts >= MAX_ATTEMPTS) return new Check(Outcome.LOCKED, this);
        if (now >= expiresAt) return new Check(Outcome.EXPIRED, this);
        CodeChallenge tried = new CodeChallenge(salt, hash, expiresAt, sentAt, attempts + 1, sends);
        String cleaned = guess == null ? "" : guess.replaceAll("\\s", "");
        boolean right = cleaned.matches("\\d{" + DIGITS + "}")
                && MessageDigest.isEqual(
                        hash(salt, cleaned).getBytes(StandardCharsets.UTF_8), hash.getBytes(StandardCharsets.UTF_8));
        return new Check(right ? Outcome.OK : Outcome.WRONG, tried);
    }

    int attemptsLeft() {
        return Math.max(0, MAX_ATTEMPTS - attempts);
    }

    boolean canSendAnother() {
        return sends < MAX_SENDS;
    }

    /** True once the wait since the last email is over. */
    boolean mayResend(long now) {
        return now - sentAt >= RESEND_AFTER_MS;
    }

    long secondsUntilResend(long now) {
        return Math.max(0, (RESEND_AFTER_MS - (now - sentAt) + 999) / 1000);
    }

    String serialize() {
        return String.join(":", salt, hash, Long.toString(expiresAt), Long.toString(sentAt),
                Integer.toString(attempts), Integer.toString(sends));
    }

    static CodeChallenge parse(String text) {
        if (text == null) return null;
        String[] parts = text.split(":");
        if (parts.length != 6) return null;
        try {
            return new CodeChallenge(parts[0], parts[1], Long.parseLong(parts[2]), Long.parseLong(parts[3]),
                    Integer.parseInt(parts[4]), Integer.parseInt(parts[5]));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static String hash(String salt, String code) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest((salt + ":" + code).getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
