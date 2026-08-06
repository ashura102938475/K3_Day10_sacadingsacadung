from __future__ import annotations

from importlib import import_module


_EXPORTS = {
    "EvaluationBundle": (".metrics", "EvaluationBundle"),
    "JudgeVerdict": (".metrics", "JudgeVerdict"),
    "evaluate_pipeline": (".metrics", "evaluate_pipeline"),
    "build_test_set": (".testset", "build_test_set"),
}
__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _EXPORTS[name]
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value
