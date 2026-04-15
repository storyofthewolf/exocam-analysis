# plots/registry.py
#
# Registry for named plot types.
# Decorate a Plot subclass with @register_plot('name') to make it available
# by name in YAML configs and make_plot.py.
#

from plots.base import Plot

_registry: dict = {}


def register_plot(name: str):
    """Class decorator that registers a Plot subclass under a given name."""
    def decorator(cls):
        if not issubclass(cls, Plot):
            raise TypeError(f'register_plot: {cls} must subclass Plot')
        _registry[name] = cls
        return cls
    return decorator


def get_plot(name: str) -> Plot:
    """Return an instance of the named plot type."""
    if name not in _registry:
        available = ', '.join(sorted(_registry))
        raise ValueError(
            f"Unknown plot type '{name}'. Available: {available}")
    return _registry[name]()


def list_plots() -> list:
    """Return sorted list of all registered plot type names."""
    return sorted(_registry)
