latest_context = ""
latest_hint = ""

def set_context(ctx):
    global latest_context
    latest_context = ctx

def get_context():
    return latest_context

def set_hint(hint):
    global latest_hint
    latest_hint = hint

def get_hint():
    return latest_hint