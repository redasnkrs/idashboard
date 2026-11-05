"""Compatibilite : ancien nom du point d'entree.

Utilise ``main.py``. Ce fichier existe pour que ``python acevo_bridge.py`` et
les scripts Windows deja en place continuent de fonctionner.
"""
from main import main

if __name__ == "__main__":
    main()
