import os
from hypothesis import settings

settings.register_profile("default", settings.get_profile("default"), print_blob=True)
settings.register_profile("dev", max_examples=100, deadline=200)
settings.register_profile("ci",  max_examples=250, deadline=None)
settings.register_profile("stress", max_examples=1000, deadline=None)

settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))

def pytest_collection_modifyitems(session, config, items):
    unit, prop, ui = [], [], []
    for it in items:
        if it.get_closest_marker("ui"):
            ui.append(it)
        elif it.get_closest_marker("property"):
            prop.append(it)
        else:
            unit.append(it)
    items[:] = unit + prop + ui
