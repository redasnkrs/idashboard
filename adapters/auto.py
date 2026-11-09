"""Source automatique : AC Evo, AC 2014, AMS2 puis SimHub (ETS2/ATS)."""
from adapters.base import DISCONNECTED_ETS2, Source


class AutoSource(Source):
    def __init__(self, sources):
        self.sources = [s for s in sources if s is not None]
        self.active = None
        self._ets2 = DISCONNECTED_ETS2

    def read(self):
        if self.active is not None:
            try:
                dash = self.active.read()
                if dash is not None:
                    return dash
            except Exception:
                pass
            self.active = None
        for source in self.sources:
            try:
                dash = source.read()
            except Exception:
                dash = None
            if dash is not None:
                self.active = source
                self._ets2 = source.ets2()
                return dash
        self._ets2 = DISCONNECTED_ETS2
        return None

    def ets2(self):
        if self.active is not None:
            try:
                return self.active.ets2()
            except Exception:
                pass
        return self._ets2
