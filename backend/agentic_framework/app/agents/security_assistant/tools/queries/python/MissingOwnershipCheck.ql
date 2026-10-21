/**
 * @name Route handler uses a client-supplied id without checking the authenticated user
 * @description A route handler passes one of its parameters to a database query, but never
 *              refers to the current user, so any caller may read or change any record.
 * @kind problem
 * @problem.severity warning
 * @security-severity 7.5
 * @precision low
 * @id security-assistant/py/missing-ownership-check
 * @tags security
 *       external/cwe/cwe-639
 *       external/cwe/cwe-862
 *       external/security-assistant/V1
 */

import python
import semmle.python.Concepts
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking

/** A function registered as a web route, e.g. `@app.route(...)` or `@router.get(...)`. */
predicate isRouteHandler(Function f) {
  exists(Call d, Attribute a |
    d = f.getADecorator() and
    a = d.getFunc() and
    a.getName() in ["route", "get", "post", "put", "patch", "delete"]
  )
}

/** The function mentions the logged-in user or a login requirement. */
predicate refersToAuthenticatedUser(Function f) {
  exists(Name n |
    n.getScope() = f and
    n.getId() in ["current_user", "get_current_user", "get_jwt_identity", "session", "current_identity"]
  )
  or
  exists(Parameter p |
    p = f.getAnArg() and
    p.getName() in ["current_user", "user", "current_identity"]
  )
  or
  exists(Expr d, string name |
    d = f.getADecorator() and
    (name = d.(Name).getId() or name = d.(Attribute).getName() or name = d.(Call).getFunc().(Name).getId()) and
    name.regexpMatch("(?i).*(login_required|jwt_required|requires_auth|permission|authenticated|auth).*")
  )
}

/** A call that looks up or changes a record through an ORM. */
predicate isOrmLookup(Call c) {
  exists(Attribute a | a = c.getFunc() |
    a.getName() in ["filter_by", "get_or_404", "first_or_404", "filter"]
    or
    a.getName() = "get" and a.getObject().(Attribute).getName() in ["objects", "query"]
  )
}

from Function f, DataFlow::ParameterNode param, DataFlow::Node sink, string kind
where
  isRouteHandler(f) and
  not refersToAuthenticatedUser(f) and
  param.getParameter() = f.getAnArg() and
  not param.getParameter().isSelf() and
  (
    sink = any(SqlExecution s).getSql() and kind = "SQL query"
    or
    exists(Call c | isOrmLookup(c) and sink.asExpr() = c.getAnArg() and kind = "ORM lookup")
    or
    exists(Call c, Keyword k |
      isOrmLookup(c) and k = c.getANamedArg() and sink.asExpr() = k.getValue() and kind = "ORM lookup"
    )
  ) and
  TaintTracking::localTaint(param, sink) and
  sink.getScope() = f
select sink,
  "Route handler '" + f.getName() + "' uses parameter '" + param.getParameter().getName() +
    "' in a " + kind + " without checking the authenticated user."
