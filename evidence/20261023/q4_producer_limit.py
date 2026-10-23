"""RR-11: does `stream-produce LIMITE=n` emit exactly n events?

Runs eng_dados' real `ProdutorDeEventos.executar` loop with all I/O replaced:
no database is read or written, no cursor file is touched, and nothing sleeps.
The draw is forced to return a transfer pair — the two events `_sortear` gives
when it picks a transfer —, and every other line of the loop is the real one.
Run with the eng_dados venv, from an empty directory:

    cd "$(mktemp -d)" && "$ENG_DADOS_DIR/.venv/bin/python" -I q4_producer_limit.py
"""

import datetime as dt
from pathlib import Path

from mvp_ed1.streaming import config, producer

assert not producer.ESTADO.exists(), "run from an empty directory: no cursor file may be read"

agora = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)


def par(self):
    evento = {"movement_type": "transfer_out", "occurred_at": agora, "recorded_at": agora}
    return [evento, dict(evento, movement_type="transfer_in")]


# An engine is created, never connected: an in-memory URL keeps the database out.
producer.database_url = lambda banco: "sqlite://"
producer.ProdutorDeEventos._carregar = lambda self: None
producer.ProdutorDeEventos._gravar = lambda self, eventos: None
producer.ProdutorDeEventos._salvar_estado = lambda self, relatorio: None
producer.ProdutorDeEventos._sortear = par
producer.time.sleep = lambda segundos: None

parametros = config.carregar(Path(config.ARQUIVO).resolve()).produtor
for limite in (1, 3, 2199, 2200):
    relatorio = producer.ProdutorDeEventos(parametros, semente=20260904, teto=limite).executar()
    print(f"limit={limite} emitted={relatorio.emitidos}")
