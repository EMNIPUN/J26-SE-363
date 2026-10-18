"""Shared vocabulary of the Requirement Fulfillment experiments: the verdict scale and the fixed rating rule.

Every experiment returns one verdict per acceptance criterion. Everything after that is plain code and identical for all
experiments: the language model never does the arithmetic (plan.md, section 4).
"""

VERDICTS = ("met", "partly", "not_met", "cannot_tell")
VERDICT_VALUE = {"met": 1.0, "partly": 0.5, "not_met": 0.0, "cannot_tell": 0.0}

# size buckets of the cleaned diff of a task, in tokens (plan.md, Experiment 1)
BUCKETS = ("<=4k", "4-8k", "8-16k", "16-32k", ">32k")
BUCKET_EDGES = (4000, 8000, 16000, 32000)

CHARS_PER_TOKEN = 3.3  # code averages roughly 3.3 characters per token; replaced by measured counts where a model reports them


def est_tokens(text):
    return int(len(text) / CHARS_PER_TOKEN) + 1


def bucket_of(tokens):
    for name, edge in zip(BUCKETS, BUCKET_EDGES):
        if tokens <= edge:
            return name
    return BUCKETS[-1]


def task_fulfilment(verdicts):
    """RF_j in [0, 1]: the mean value of the criterion verdicts (RF_j = (R_j - 1) / 4 with R_j = 1 + 4 * mean)."""
    if not verdicts:
        return 0.0
    return sum(VERDICT_VALUE[v] for v in verdicts) / len(verdicts)


def band(fulfilment):
    """Rubric band 1-5 of a fulfilment value."""
    return min(5, max(1, int(round(1 + 4 * fulfilment))))


def sprint_score(task_values):
    """RF of a sprint = mean over the student's tasks, as in the proposal."""
    return sum(task_values) / len(task_values) if task_values else 0.0
