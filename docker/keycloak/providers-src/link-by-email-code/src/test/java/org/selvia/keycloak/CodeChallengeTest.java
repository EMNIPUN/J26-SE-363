package org.selvia.keycloak;

import static org.junit.jupiter.api.Assertions.*;

import java.security.SecureRandom;
import org.junit.jupiter.api.Test;
import org.selvia.keycloak.CodeChallenge.Outcome;

class CodeChallengeTest {

    private static final long T0 = 1_000_000L;
    private final SecureRandom random = new SecureRandom();

    @Test
    void theEmailedCodeIsSixDigits() {
        for (int i = 0; i < 200; i++) {
            assertTrue(CodeChallenge.issue(null, T0, random).code().matches("\\d{6}"));
        }
    }

    @Test
    void theRightCodeIsAccepted() {
        var issued = CodeChallenge.issue(null, T0, random);
        assertEquals(Outcome.OK, issued.challenge().check(issued.code(), T0 + 1000).outcome());
    }

    @Test
    void spacesAroundTheCodeAreIgnored() {
        var issued = CodeChallenge.issue(null, T0, random);
        String spaced = " " + issued.code().substring(0, 3) + " " + issued.code().substring(3) + " ";
        assertEquals(Outcome.OK, issued.challenge().check(spaced, T0 + 1000).outcome());
    }

    @Test
    void aWrongCodeIsRefusedAndCounted() {
        var issued = CodeChallenge.issue(null, T0, random);
        String wrong = issued.code().equals("000000") ? "000001" : "000000";

        var first = issued.challenge().check(wrong, T0 + 1000);

        assertEquals(Outcome.WRONG, first.outcome());
        assertEquals(CodeChallenge.MAX_ATTEMPTS - 1, first.next().attemptsLeft());
    }

    @Test
    void notSixDigitsIsWrong() {
        var issued = CodeChallenge.issue(null, T0, random);
        for (String guess : new String[] {null, "", "12345", "1234567", "abcdef"}) {
            assertEquals(Outcome.WRONG, issued.challenge().check(guess, T0 + 1000).outcome(), String.valueOf(guess));
        }
    }

    @Test
    void afterFiveWrongTriesEvenTheRightCodeIsLocked() {
        var issued = CodeChallenge.issue(null, T0, random);
        String wrong = issued.code().equals("000000") ? "000001" : "000000";
        CodeChallenge challenge = issued.challenge();
        for (int i = 0; i < CodeChallenge.MAX_ATTEMPTS; i++) {
            challenge = challenge.check(wrong, T0 + 1000).next();
        }

        assertEquals(Outcome.LOCKED, challenge.check(issued.code(), T0 + 2000).outcome());
    }

    @Test
    void aCodeExpiresAfterTenMinutes() {
        var issued = CodeChallenge.issue(null, T0, random);

        assertEquals(Outcome.OK, issued.challenge().check(issued.code(), T0 + CodeChallenge.TTL_MS - 1).outcome());
        assertEquals(Outcome.EXPIRED, issued.challenge().check(issued.code(), T0 + CodeChallenge.TTL_MS).outcome());
    }

    @Test
    void aNewCodeResetsTheTriesButKeepsCountingSends() {
        var first = CodeChallenge.issue(null, T0, random);
        var locked = first.challenge();
        for (int i = 0; i < CodeChallenge.MAX_ATTEMPTS; i++) {
            locked = locked.check("not-a-code", T0).next();
        }

        var second = CodeChallenge.issue(locked, T0 + 120_000, random);

        assertEquals(CodeChallenge.MAX_ATTEMPTS, second.challenge().attemptsLeft());
        assertEquals(Outcome.OK, second.challenge().check(second.code(), T0 + 121_000).outcome());
        assertTrue(second.challenge().canSendAnother());
        var third = CodeChallenge.issue(second.challenge(), T0 + 240_000, random);
        assertFalse(third.challenge().canSendAnother(), "three emails is the limit");
    }

    @Test
    void anOldCodeStopsWorkingWhenANewOneIsIssued() {
        var first = CodeChallenge.issue(null, T0, random);
        var second = CodeChallenge.issue(first.challenge(), T0 + 120_000, random);

        // the new challenge only accepts the new code (the old one hashes differently)
        if (!first.code().equals(second.code())) {
            assertEquals(Outcome.WRONG, second.challenge().check(first.code(), T0 + 121_000).outcome());
        }
    }

    @Test
    void thereIsAWaitBeforeSendingAgain() {
        var issued = CodeChallenge.issue(null, T0, random);

        assertFalse(issued.challenge().mayResend(T0 + 1000));
        assertEquals(59, issued.challenge().secondsUntilResend(T0 + 1000));
        assertTrue(issued.challenge().mayResend(T0 + CodeChallenge.RESEND_AFTER_MS));
    }

    @Test
    void itSurvivesBeingStoredAsText() {
        var issued = CodeChallenge.issue(null, T0, random);
        var restored = CodeChallenge.parse(issued.challenge().serialize());

        assertEquals(Outcome.OK, restored.check(issued.code(), T0 + 1000).outcome());
        assertFalse(issued.challenge().serialize().contains(issued.code()), "the code itself is never stored");
    }

    @Test
    void junkIsNotAChallenge() {
        assertNull(CodeChallenge.parse(null));
        assertNull(CodeChallenge.parse("nope"));
        assertNull(CodeChallenge.parse("a:b:c:d:e:f"));
    }
}
