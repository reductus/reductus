from .refldata import Intent, infer_intent

INTENT_OPTIONS = 'infer|auto|'+'|'.join(Intent.intents)
def apply_intent(data, intent):
    stored_intent = getattr(data, 'intent', Intent.none)
    inferred_intent = infer_intent(data)
    if stored_intent == Intent.none:
        data.intent = inferred_intent
    elif intent == 'infer':
        data.intent = inferred_intent
    elif intent == 'auto':
        pass  # data.intent already is stored_intent
    else:
        data.intent = intent
    if inferred_intent not in (data.intent, Intent.none, Intent.time):
        data.warn("intent %r does not match inferred intent %r"
                  % (data.intent, inferred_intent))


