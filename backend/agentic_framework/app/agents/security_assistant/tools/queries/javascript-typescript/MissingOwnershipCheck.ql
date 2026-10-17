/**
 * @name Route handler uses a client-supplied id without checking the authenticated user
 * @description An Express route handler passes request input to a database call, but neither the
 *              route nor the handler refers to the authenticated user.
 * @kind problem
 * @problem.severity warning
 * @security-severity 7.5
 * @precision low
 * @id security-assistant/js/missing-ownership-check
 * @tags security
 *       external/cwe/cwe-639
 *       external/cwe/cwe-862
 *       external/security-assistant/V1
 */

import javascript

/** The route has extra middleware (e.g. `authenticate`) or the handler reads the logged-in user. */
predicate refersToAuthenticatedUser(Express::RouteSetup rs, Function handler) {
  rs.getNumArgument() > 2
  or
  exists(PropAccess pa |
    pa.getEnclosingFunction*() = handler and
    pa.getPropertyName() in ["user", "session", "auth", "userId", "currentUser"]
  )
}

/** A call that reads or changes a record. */
predicate isRecordAccess(DataFlow::CallNode call) {
  call.getCalleeName() in
    [
      "query", "execute", "findById", "findOne", "findByPk", "findUnique", "findFirst", "find",
      "findOneAndUpdate", "findByIdAndUpdate", "findByIdAndDelete", "findOneAndDelete", "deleteOne",
      "updateOne", "destroy", "update", "get", "all", "run"
    ] and
  // `get`/`all`/`run`/`find` are only record access when called on something that looks like a db/model
  (
    call.getCalleeName() in ["query", "execute", "findById", "findOne", "findByPk", "findUnique", "findFirst",
        "findOneAndUpdate", "findByIdAndUpdate", "findByIdAndDelete", "findOneAndDelete", "deleteOne",
        "updateOne", "destroy"]
    or
    call.getReceiver().asExpr().(Identifier).getName().regexpMatch("(?i).*(db|model|repo|collection|knex|pool|client).*")
  )
}

class RequestToRecordAccess extends TaintTracking::Configuration {
  RequestToRecordAccess() { this = "SecurityAssistantRequestToRecordAccess" }

  override predicate isSource(DataFlow::Node n) {
    n.(Http::RequestInputAccess).getKind() in ["parameter", "body", "url"]
  }

  override predicate isSink(DataFlow::Node n) {
    exists(DataFlow::CallNode call | isRecordAccess(call) and n = call.getAnArgument())
  }
}

from
  RequestToRecordAccess cfg, Express::RouteSetup rs, Function handler, DataFlow::Node input,
  DataFlow::Node arg, DataFlow::CallNode sink
where
  handler = rs.getARouteHandler().getAFunctionValue().getFunction() and
  cfg.hasFlow(input, arg) and
  arg = sink.getAnArgument() and
  sink.getEnclosingFunction() = handler and
  input.getContainer() = handler and
  not refersToAuthenticatedUser(rs, handler)
select sink, "Route handler uses request input in a database call without checking the authenticated user."
