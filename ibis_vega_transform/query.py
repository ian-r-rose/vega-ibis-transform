"""
Functionality for server-side ibis transforms of vega charts.
"""
import json
import re
import typing

import altair
import altair.vegalite.v3.display
import ibis
import IPython
from IPython import get_ipython

from .core import apply
from .globals import _expr_map

__all__ = ["display_queries"]


# For debugging
_executed_expressions: typing.List[str] = []

d = None


def display_queries():
    global d
    d = IPython.display.display(IPython.display.Code(""), display_id=True)
    _update_display()


def _update_display():
    if d:
        d.update(IPython.display.Code("\n\n".join(reversed(_executed_expressions))))


def query_target_func(comm, msg):
    """
    Target function for actually evaluating the `queryibis` transform.
    """
    # These are the paramaters passed to the vega transform
    parameters: dict = msg["content"]["data"]

    name: str = parameters.pop("name")
    transforms: typing.Optional[str] = parameters.pop("transform", None)

    if name not in _expr_map:
        raise ValueError(f"{name} is not an expression known to us!")
    expr = _expr_map[name]
    if transforms:
        # Replace all string instances of data references with value in schema
        for k, v in parameters.items():
            # All data items are added to parameters as `:<data name>`.
            # They also should  be in the `data` paramater, but you have to call
            # this with a tuple which I am not sure where to get from
            # https://github.com/vega/vega/blob/65fe7cb2485be90e16298d9dff87bf56045afb8d/packages/vega-transforms/src/Filter.js#L48
            if not k.startswith(":"):
                continue
            k = k[1:]
            res = json.dumps(v)
            for t in transforms:
                if t["type"] == "filter" or t["type"] == "formula":
                    t["expr"] = _patch_vegaexpr(t["expr"], k, res)
        try:
            expr = apply(expr, transforms)
        except Exception as e:
            raise ValueError(
                f"Failed to convert {transforms} with error message message '{e}'"
            )
    try:
        _executed_expressions.append(str(expr.compile()))
        print(_executed_expressions)
    except ibis.common.UnsupportedOperationError:
        raise NotImplementedError(
            f"Could not compile \n{expr}\n\ncreated from transforms:\n{transforms}"
        )
    _update_display()

    data = expr.execute()
    comm.send(altair.to_values(data)["values"])


def _patch_vegaexpr(expr: str, name: str, value: str) -> str:
    quote = "(['\"])"
    expr = re.sub(f"data\({quote}{name}{quote}\)", value, expr)
    expr = re.sub(
        f"vlSelectionTest\({quote}{name}{quote}", f"vlSelectionTest({value}", expr
    )
    return expr


get_ipython().kernel.comm_manager.register_target("queryibis", query_target_func)
