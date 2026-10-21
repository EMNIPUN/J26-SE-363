/**
 * @name Controller method uses a client-supplied id without checking the authenticated user
 * @description A Spring request handler passes a request parameter to a database call, but is not
 *              covered by an authorisation rule (method security, a role rule in a
 *              SecurityFilterChain) and never refers to the authenticated user.
 * @kind problem
 * @problem.severity warning
 * @security-severity 7.5
 * @precision low
 * @id security-assistant/java/missing-ownership-check
 * @tags security
 *       external/cwe/cwe-639
 *       external/cwe/cwe-862
 *       external/security-assistant/V1
 */

import java
import semmle.code.java.dataflow.TaintTracking
import semmle.code.java.frameworks.spring.SpringController

/**
 * Every string literal written inside an annotation. Spring is not on the classpath (CodeQL runs with
 * --build-mode=none), so annotation types are unresolved and elements cannot be read by name.
 */
string annotationStrings(Annotation a) {
  exists(StringLiteral s | s.getParent*() = a and result = s.getValue())
}

/** URL paths declared by a mapping annotation (GetMapping, RequestMapping(path = "/x"), ...). */
string mappingPaths(Annotation a) {
  a.getType().getName() in
    ["GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping", "RequestMapping"] and
  result = annotationStrings(a) and
  result.matches("/%")
}

/** Full URL paths of a handler: class-level mapping + method-level mapping. */
string handlerPath(SpringRequestMappingMethod m) {
  exists(string base, string sub |
    (
      base = mappingPaths(m.getDeclaringType().getAnAnnotation())
      or
      not exists(mappingPaths(m.getDeclaringType().getAnAnnotation())) and base = ""
    ) and
    (
      sub = mappingPaths(m.getAnAnnotation())
      or
      not exists(mappingPaths(m.getAnAnnotation())) and sub = ""
    ) and
    result = base + sub
  )
}

/**
 * Method security that really authorises: @Secured, @RolesAllowed, or @PreAuthorize /
 * @PostAuthorize with an expression that is more than "the user is logged in".
 */
predicate hasAuthorizingAnnotation(SpringRequestMappingMethod m) {
  exists(Annotation a | a = m.getAnAnnotation() or a = m.getDeclaringType().getAnAnnotation() |
    a.getType().getName() in ["Secured", "RolesAllowed"]
    or
    a.getType().getName() in ["PreAuthorize", "PostAuthorize"] and
    not exists(string expr | expr = annotationStrings(a) |
      expr.regexpMatch("(?i)\\s*(isAuthenticated\\(\\)|isFullyAuthenticated\\(\\)|permitAll\\(\\)|true)\\s*")
    )
  )
}

/**
 * A rule in a SecurityFilterChain that requires a role or authority for the handler's path
 * (`requestMatchers("/admin/**").hasRole("ADMIN")`, or `anyRequest().hasRole(..)`).
 * `authenticated()` is not enough: any logged-in user could still read another user's data.
 */
predicate coveredByFilterChainRule(SpringRequestMappingMethod m) {
  exists(MethodCall rule, MethodCall matcher |
    rule.getMethod().getName() in
      ["hasRole", "hasAnyRole", "hasAuthority", "hasAnyAuthority", "access"] and
    // the rule is inside a method that returns SecurityFilterChain (the call may sit in a lambda)
    exists(Method chain |
      chain.getReturnType().(RefType).getName() = "SecurityFilterChain" and
      rule.getFile() = chain.getFile() and
      rule.getLocation().getStartLine() >= chain.getLocation().getStartLine() and
      rule.getLocation().getEndLine() <= chain.getBody().getLocation().getEndLine()
    ) and
    matcher = rule.getQualifier() and
    (
      matcher.getMethod().getName() = "anyRequest"
      or
      matcher.getMethod().getName() in ["requestMatchers", "antMatchers", "mvcMatchers"] and
      exists(string pattern, string path |
        pattern = matcher.getAnArgument().(StringLiteral).getValue() and path = handlerPath(m)
      |
        pattern = path
        or
        pattern.matches("%/**") and path.matches(pattern.prefix(pattern.length() - 3) + "%")
      )
    )
  )
}

/** The handler mentions the logged-in user. */
predicate refersToAuthenticatedUser(SpringRequestMappingMethod m) {
  exists(Parameter p | p = m.getAParameter() |
    p.getType().(RefType).getName() in ["Principal", "Authentication", "UserDetails", "OAuth2User", "Jwt"]
    or
    p.getAnAnnotation().getType().getName() in ["AuthenticationPrincipal", "CurrentUser"]
  )
  or
  exists(MethodCall ma | ma.getEnclosingCallable() = m |
    ma.getMethod().getName() in
      ["getPrincipal", "getUserPrincipal", "getAuthentication", "getCurrentUser", "getRemoteUser"]
  )
  or
  exists(TypeAccess t | t.getEnclosingCallable() = m | t.getType().getName() = "SecurityContextHolder")
}

/** A call that reads or changes a record. */
predicate isRecordAccess(MethodCall call) {
  call.getMethod().getName() in
    [
      "execute", "executeQuery", "executeUpdate", "prepareStatement", "createQuery",
      "createNativeQuery", "queryForObject", "queryForList", "query", "update", "findById",
      "getById", "getReferenceById", "getOne", "deleteById", "existsById"
    ]
}

from SpringRequestMappingMethod m, Parameter p, MethodCall call, Expr arg
where
  p = m.getAParameter() and
  p.getAnAnnotation().getType().getName() in ["PathVariable", "RequestParam", "RequestBody"] and
  call.getEnclosingCallable() = m and
  isRecordAccess(call) and
  arg = call.getAnArgument() and
  TaintTracking::localExprTaint(p.getAnAccess(), arg) and
  not hasAuthorizingAnnotation(m) and
  not coveredByFilterChainRule(m) and
  not refersToAuthenticatedUser(m)
select call,
  "Controller method '" + m.getName() + "' uses parameter '" + p.getName() +
    "' in a database call without an authorisation rule or a check of the authenticated user."
