# Reservas de Amanai — Maqueta 3D

Maqueta digital interactiva del urbanismo de Reservas de Amanai (La Luisa), construida a partir de la geometría vectorial del plano de urbanismo V.27.

**Ver en línea:** https://mentorjotacoo-crypto.github.io/amanai-maqueta-3d/

- `index.html` — página autocontenida (Three.js + datos embebidos).
- `extract*.py`, `build_lots_real.py`, `build_json.py` — pipeline de extracción (PyMuPDF + shapely) desde el PDF del plano.
- Para regenerar con un plano nuevo: correr extract3→9, build_lots_real, build_json y reensamblar.
