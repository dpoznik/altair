"""Updates the attribute __all__ in altair/__init__.py based on the updated Altair schema."""

from __future__ import annotations

import typing as t
import typing_extensions as te
from inspect import getattr_static, ismodule
from pathlib import Path
from typing import TYPE_CHECKING

from tools.codemod import ruff

_TYPING_CONSTRUCTS = {
    te.TypeAlias,
    t.TypeVar,
    t.cast,
    t.overload,
    te.runtime_checkable,
    list,
    dict,
    tuple,
    t.Any,
    t.Literal,
    t.Union,
    t.Iterable,
    t.Protocol,
    te.Protocol,
    t.Sequence,
    t.IO,
    annotations,
    te.Required,
    te.TypedDict,
    t.TypedDict,
    te.Self,
    te.deprecated,
    te.TypeAliasType,
}


def update__all__variable() -> None:
    """
    Updates the __all__ variable to all relevant attributes of top-level Altair.

    This is for example useful to hide deprecated attributes from code completion in
    Jupyter.
    """
    # Read existing file content
    import altair as alt

    encoding = "utf-8"
    init_path = Path(alt.__file__)
    with init_path.open(encoding=encoding) as f:
        lines = f.readlines()
    lines = [line.strip("\n") for line in lines]

    # Find first and last line of the definition of __all__
    first_definition_line = None
    last_definition_line = None
    for idx, line in enumerate(lines):
        if line.startswith("__all__ ="):
            first_definition_line = idx
        elif first_definition_line is not None and line.startswith("]"):
            last_definition_line = idx
            break
    assert first_definition_line is not None
    assert last_definition_line is not None

    # Put file back together, replacing old definition of __all__ with new one, keeping
    # the rest of the file as is
    new_lines = [
        *lines[:first_definition_line],
        f"__all__ = {relevant_attributes(alt.__dict__)}",
        *lines[last_definition_line + 1 :],
    ]
    # Write new version of altair/__init__.py
    # Format file content with ruff
    ruff.write_lint_format(init_path, new_lines)


def relevant_attributes(namespace: dict[str, t.Any], /) -> list[str]:
    """
    Figure out which attributes in `__all__` are relevant.

    Returns an alphabetically sorted list, to insert into `__all__`.

    Parameters
    ----------
    namespace
        A module dict, like `altair.__dict__`
    """
    from altair.vegalite.v5.schema import _typing

    # NOTE: Exclude any `TypeAlias` that were reused in a runtime definition.
    # Required for imports from `_typing`, outside of a `TYPE_CHECKING` block.
    _TYPING_CONSTRUCTS.update(
        (
            v
            for k, v in _typing.__dict__.items()
            if (not k.startswith("__")) and _is_hashable(v)
        )
    )
    it = (
        name
        for name, attr in namespace.items()
        if (not name.startswith("_")) and _is_relevant(attr, name)
    )
    return sorted(it)


def _is_hashable(obj: t.Any) -> bool:
    """Guard to prevent an `in` check occuring on mutable objects."""
    try:
        return bool(hash(obj))
    except TypeError:
        return False


def _is_relevant(attr: t.Any, name: str, /) -> bool:
    """Predicate logic for filtering attributes."""
    if (
        getattr_static(attr, "_deprecated", False)
        or attr is TYPE_CHECKING
        or (_is_hashable(attr) and attr in _TYPING_CONSTRUCTS)
        or name in {"pd", "jsonschema"}
        or getattr_static(attr, "__deprecated__", False)
    ):
        return False
    elif ismodule(attr):
        # Only include modules which are part of Altair. This excludes built-in
        # modules (they do not have a __file__ attribute), standard library,
        # and third-party packages.
        return getattr_static(attr, "__file__", "").startswith(str(Path.cwd()))
    else:
        return True


if __name__ == "__main__":
    update__all__variable()
