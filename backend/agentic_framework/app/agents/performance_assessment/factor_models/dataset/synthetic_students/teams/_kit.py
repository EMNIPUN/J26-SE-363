"""Small constructors so the hand-written team files stay readable. They only build plain dicts and tuples."""


def T(key, title, desc, ac, sp, sub, status, met, rating, code="", **kw):
    """One Scrum task. `met[i]` = 1 when the code satisfies criterion i; `rating` = 1-5 fulfilment judged from the code.
    Extra keywords: by="SYN-xxx" (finished by a teammate), carried="previous task id", story="epic name"."""
    return dict(key=key, title=title, desc=desc, ac=ac, sp=sp, sub=sub, status=status, met=met, rating=rating, code=code, **kw)


def Q(tier, rating, snippet, question, answer):
    """Code-ownership quiz item and the student's answer (tier: strong | good | partial | weak)."""
    return dict(tier=tier, rating=rating, snippet=snippet, question=question, answer=answer)


def S(tasks, commits, quiz, survival, owner, reviews=(), comments=(), prs=(), mfo=0):
    """One student in one sprint."""
    return dict(tasks=list(tasks), commits=list(commits), reviews=list(reviews), comments=list(comments), prs=list(prs),
                quiz=quiz, ko=dict(survival=survival, primary_owner=owner), merged_for_others=mfo)
