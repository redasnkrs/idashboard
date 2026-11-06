"""Point d'entree du pont.

    python main.py                  detection auto (AC Evo, AC 2014, AMS2)
    python main.py --game ac        force Assetto Corsa 2014
    python main.py --game ams2      force Automobilista 2
    python main.py --game acevo     force Assetto Corsa Evo
    python main.py --fake           fausse source (Mac, Linux, tests)
    python main.py --debug          affiche les valeurs lues toutes les 0,5 s
"""
import argparse
import sys
import threading

from core import media
from core.config import PORT, VERSION
from core.pump import poll_loop
from core.server import serve


def _make_source(fake, game):
    if fake or game == "fake":
        from adapters.fake import FakeSource
        return FakeSource()
    if sys.platform != "win32":
        sys.exit("Les vraies sources doivent tourner sous Windows (memoire "
                 "partagee). Utilise --fake pour tester sans jeu.")
    if game == "acevo":
        try:
            from adapters.acevo import AcevoSource
            return AcevoSource()
        except ImportError:
            sys.exit("Le paquet acevo-sdk est manquant : pip install acevo-sdk")
    if game == "ac":
        from adapters.ac import AcSource
        return AcSource()
    if game == "ams2":
        from adapters.ams2 import Ams2Source
        return Ams2Source()
    from adapters.ac import AcSource
    from adapters.ams2 import Ams2Source
    from adapters.auto import AutoSource
    sources = []
    try:
        from adapters.acevo import AcevoSource
        sources.append(AcevoSource())
    except Exception:
        pass
    sources.append(AcSource())
    sources.append(Ams2Source())
    return AutoSource(sources)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", action="version",
                    version="idash " + VERSION)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--fake", action="store_true",
                    help="fausse source, sans jeu (Mac/Linux)")
    ap.add_argument("--game", default="auto",
                    choices=("auto", "acevo", "ac", "ams2", "fake"),
                    help="source de telemetrie (defaut: detection auto)")
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args(argv)

    source = _make_source(args.fake, args.game)
    threading.Thread(target=poll_loop, args=(source, args.debug),
                     daemon=True).start()
    media.start()
    server = serve(args.port)
    port = server.server_address[1]
    print(f"idash {VERSION}")
    print(f"Accueil          : http://localhost:{port}/")
    print(f"Compteur defaut  : http://localhost:{port}/dashboard")
    print(f"Apercu sans jeu  : http://localhost:{port}/dashboard?demo")
    print(f"Plugin Macro Deck: http://localhost:{port}/api/ets2/telemetry")
    if not (args.fake or args.game == "fake"):
        print("Lance ton jeu (AC Evo, AC 2014 ou AMS2). Ctrl+C pour quitter.")
    else:
        print("Mode fausse source (aucun jeu requis). Ctrl+C pour quitter.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
