"""Speech-to-text then Gemma, with retries for the flaky free tier (measured 500/503s).
The workflow input is only the upload's id; content never goes to Temporal."""
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from flows.ai_activities import AIActivities, FailArgs

KNOWN_FAILURES = ["BadInput", "Gone", "Empty"]
AI_RETRY = RetryPolicy(initial_interval=timedelta(seconds=5), backoff_coefficient=2.0, maximum_attempts=5,
                       non_retryable_error_types=KNOWN_FAILURES)


@workflow.defn
class ProcessInputWorkflow:
    @workflow.run
    async def run(self, input_id: str) -> str:
        try:
            await workflow.execute_activity_method(AIActivities.transcribe, input_id,
                                                   start_to_close_timeout=timedelta(seconds=150),
                                                   retry_policy=AI_RETRY)
            await workflow.execute_activity_method(AIActivities.understand, input_id,
                                                   start_to_close_timeout=timedelta(seconds=300),
                                                   retry_policy=AI_RETRY)
            return "ready"
        except ActivityError as e:
            cause = e.cause
            reason = cause.type if isinstance(cause, ApplicationError) and cause.type in KNOWN_FAILURES else "Busy"
            await workflow.execute_activity_method(AIActivities.fail, FailArgs(input_id, reason),
                                                   start_to_close_timeout=timedelta(seconds=10))
            return "failed"
