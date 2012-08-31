import functools


def with_summary(f):
    """Prints a nice summary, assuming the function accepts a
    'summary' kwarg and appends to it."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        summary = []
        f(*args, summary=summary, **kwargs)
        if summary:
            summary = ['\nSummary of actions:'] + summary
            print "\n - ".join(summary)

        else:
            print "No summary provided."

    return wrapper
