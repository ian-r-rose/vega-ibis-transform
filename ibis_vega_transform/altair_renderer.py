import typing

import altair
import opentracing

from .tracing import tracer
from .globals import get_fallback

__all__: typing.List[str] = []

# New Vega Lite renderer mimetype which can process ibis expressions in names
MIMETYPE = "application/vnd.vega.ibis.v5+json"


def altair_renderer(spec):
    """
    An altair renderer that serves our custom mimetype with ibis support.
    """
    if get_fallback():
        return altair.vegalite.v3.display.default_renderer(spec)

    active_span = tracer.active_span
    injected_span = {}
    tracer.inject(active_span, opentracing.Format.TEXT_MAP, injected_span)
    active_span.finish()
    return {MIMETYPE: {"spec": spec, "span": injected_span}}


altair.renderers.register("ibis", altair_renderer)
altair.renderers.enable("ibis")