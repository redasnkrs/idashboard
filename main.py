"""Point d'entree du pont.

    python main.py            vraie source (Windows + Assetto Corsa Evo)
    python main.py --fake     fausse source (Mac, Linux, tests)
    python main.py --debug    affiche les valeurs lues toutes les 0,5 s
"""
import argparse
import sys
import threading

from core.config import PORT
from core.pump import poll_loop
from core.server import serve


def _make_source(fake):
    if fake:
        from adapters.fake import FakeSource
        return FakeSource()
    if sys.platform != "win32":
        sys.exit("La vraie source doit tourner sur Windows (memoire partagee "
                 "AC Evo). Utilise --fake pour tester sans le jeu.")
    try:
        from adapters.acevo import AcevoSource
        return AcevoSource()
    except ImportError:
        sys.exit("Le paquet acevo-sdk est manquant : pip install acevo-sdk")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--fake", action="store_true",
                    help="fausse source, sans jeu (Mac/Linux)")
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args(argv)

    source = _make_source(args.fake)
    threading.Thread(target=poll_loop, args=(source, args.debug),
                     daemon=True).start()
    server = serve(args.port)
    port = server.server_address[1]
    print(f"Accueil          : http://localhost:{port}/")
    print(f"Compteur defaut  : http://localhost:{port}/dashboard")
    print(f"Apercu sans jeu  : http://localhost:{port}/dashboard?demo")
    print(f"Plugin Macro Deck: http://localhost:{port}/api/ets2/telemetry")
    if not args.fake:
        print("Lance AC Evo (en session). Ctrl+C pour quitter.")
    else:
        print("Mode fausse source (aucun jeu requis). Ctrl+C pour quitter.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
