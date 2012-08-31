import functools


def with_summary(f):
    """Prints a nice summary, assuming a function returns a list of
    summary strings."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        summary = []
        f(*args, summary=summary, **kwargs)
        if summary:
            summary = ['Summary of actions:'] + summary
            print "\n - ".join(summary)

        else:
            print "No summary provided."

    return wrapper
