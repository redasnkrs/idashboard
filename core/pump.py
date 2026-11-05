"""Boucle de lecture de la source et etat partage par le serveur.

Un seul thread lit la source a ``POLL_HZ`` ; le serveur HTTP se contente de
lire ``STATE``. Cela evite de toucher la memoire du jeu depuis plusieurs
threads et garde le flux SSE a 60 Hz.
"""
import json
import time

from adapters.base import DISCONNECTED_ETS2
from core.config import POLL_HZ

DASH_OFF = json.dumps({"c": False}).encode()

STATE = {
    "dash": DASH_OFF,
    "ets2": DISCONNECTED_ETS2,
}


def _set_disconnected():
    STATE["dash"] = DASH_OFF
    STATE["ets2"] = DISCONNECTED_ETS2


def poll_loop(source, debug=False, hz=POLL_HZ):
    period = 1.0 / hz
    nxt = time.perf_counter()
    last_log = 0.0
    while True:
        try:
            dash = source.read()
            if dash is None:
                _set_disconnected()
            else:
                STATE["dash"] = json.dumps(dash).encode()
                STATE["ets2"] = source.ets2()
                if debug and time.time() - last_log > 0.5:
                    last_log = time.time()
                    print(
                        "kmh={:.0f} rpm={:.0f}/{:.0f} gear={} fuel={:.1f}L "
                        "low={} high={} L={} R={} haz={} hb={:.2f} | "
                        "car='{}' track='{}' lap={} best={} tc={} abs={} "
                        "wt={} ot={}".format(
                            dash["v"], dash["r"], dash["rm"], dash["g"],
                            dash["fuel"], dash["low"], dash["high"],
                            dash["L"], dash["R"], dash["haz"], dash["hb"],
                            dash["car"], dash["track"], dash["lap"],
                            dash["best"], dash["tcl"], dash["absl"],
                            dash["wt"], dash["ot"]))
        except Exception as exc:  # le jeu se ferme, memoire invalide...
            _set_disconnected()
            if debug:
                print("erreur lecture:", exc)
        nxt += period
        delay = nxt - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        else:
            nxt = time.perf_counter()
