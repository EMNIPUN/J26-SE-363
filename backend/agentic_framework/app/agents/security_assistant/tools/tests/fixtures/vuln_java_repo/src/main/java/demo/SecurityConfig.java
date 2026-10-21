package demo;

import org.springframework.security.crypto.password.NoOpPasswordEncoder;

public class SecurityConfig {
    Object encoder() { return NoOpPasswordEncoder.getInstance(); } // V3
    void configure(Object http) { http.csrf().disable(); } // V3
}
