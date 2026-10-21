package demo;

import java.sql.Statement;
import org.springframework.web.bind.annotation.*;

@RestController
public class UserController {
    @GetMapping("/users/{id}/orders")
    public String orders(@PathVariable String id, @RequestParam String name, Statement st) throws Exception {
        // V1: id is never compared to the authenticated user
        st.executeQuery("SELECT * FROM orders WHERE user_id = " + id + " AND name = '" + name + "'"); // V2
        return "ok";
    }

    @PostMapping("/login")
    public String login() {
        return io.jsonwebtoken.Jwts.builder().setSubject("u").signWith(null).compact(); // V3: no expiry
    }
}
