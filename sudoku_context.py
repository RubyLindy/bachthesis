latest_context = ""

def set_context(ctx):
    global latest_context
    latest_context = ctx

def get_context():
    return latest_context