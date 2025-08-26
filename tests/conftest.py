import os
from hypothesis import settings

settings.register_profile("default", settings.get_profile("default"), print_blob=True)
settings.register_profile("dev", max_examples=100, deadline=200)
settings.register_profile("ci",  max_examples=250, deadline=None)
settings.register_profile("stress", max_examples=1000, deadline=None)

settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))

def pytest_collection_modifyitems(session, config, items):
    non_prop, prop = [], []
    for it in items:
        is_property = bool(it.get_closest_marker("property"))
        (prop if is_property else non_prop).append(it)
    items[:] = non_prop + prop
