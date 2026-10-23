"""Mede o produto analítico em Parquet: analytics (tabelas) e consumption (views).

Sessão somente leitura; credenciais lidas do .env do eng_dados sem imprimir.
Uso: python exportar.py <raiz do eng_dados> <pasta de saída>
"""
import os
import pathlib
import sys
import time

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq

raiz, saida = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
env = dict(l.split("=", 1) for l in (raiz / ".env").read_text().splitlines()
           if "=" in l and not l.lstrip().startswith("#"))
con = psycopg.connect(host="localhost", port=env["WAREHOUSE_DB_PORT"], dbname=env["WAREHOUSE_DB_NAME"],
                      user=env["WAREHOUSE_DB_USER"], password=env["WAREHOUSE_DB_PASSWORD"],
                      options="-c default_transaction_read_only=on", application_name="sonda_parquet")
cur = con.cursor()
cur.execute("""select table_schema, table_name from information_schema.tables
               where (table_schema = 'analytics' and table_type = 'BASE TABLE')
                  or (table_schema = 'consumption' and table_type = 'VIEW')
               order by 1, 2""")
alvos = cur.fetchall()
totais = {}
inicio = time.time()
for schema, tabela in alvos:
    cur.execute(f'select * from "{schema}"."{tabela}"')
    nomes = [d.name for d in cur.description]
    linhas = cur.fetchall()
    colunas = list(zip(*linhas)) if linhas else [[] for _ in nomes]
    arrays = []
    for col in colunas:
        try:
            arrays.append(pa.array(list(col)))
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            arrays.append(pa.array([None if v is None else str(v) for v in col]))
    t = pa.Table.from_arrays(arrays, names=nomes)
    destino = saida / schema / f"{tabela}.parquet"
    destino.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(t, destino, compression="zstd")
    tam = destino.stat().st_size
    totais.setdefault(schema, [0, 0, 0])
    totais[schema][0] += 1; totais[schema][1] += len(linhas); totais[schema][2] += tam
    print(f"{schema}.{tabela}: {len(linhas)} linhas, {tam/1024:.0f} KiB")
print(f"\ntempo total: {time.time() - inicio:.1f}s")
for schema, (n, l, b) in totais.items():
    print(f"TOTAL {schema}: {n} objetos, {l} linhas, {b/1024/1024:.2f} MiB em Parquet (zstd)")
print(f"TOTAL GERAL: {sum(v[2] for v in totais.values())/1024/1024:.2f} MiB")
con.close()
