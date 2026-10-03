// Limits shared by the chat input and the (mock) backend validation.
export const MAX_MESSAGE_LENGTH = 1000

// window.postMessage contract with the embedded external learning platform:
// { type: ACTIVITY_COMPLETED_MESSAGE, activityId } is sent when the student
// finishes an activity. It only signals completion; results are always
// fetched from the backend.
export const ACTIVITY_COMPLETED_MESSAGE = 'selvia:activity-completed'
