"""Teste do pipeline de import com a planilha real."""
import sys, io
sys.path.insert(0, ".")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.infra_import import parse_spreadsheet, execute_import
from app.infra_db import init_db

init_db()

path = "Network Mapping - Safe Notos.xlsx"
with open(path, "rb") as f:
    file_bytes = f.read()

print("=== PARSE ===")
parsed = parse_spreadsheet(file_bytes)

print(f"Sheets : {parsed['sheets_found']}")
print(f"Avisos : {parsed['warnings']}")
print(f"Racks  : {len(parsed['racks'])}")
print(f"Equips : {len(parsed['equipment'])}")
print(f"Conns  : {len(parsed['connections'])}")

print("\nConexoes por sheet:")
for sheet, count in parsed['row_counts'].items():
    print(f"  {sheet}: {count}")

from collections import Counter
types = Counter(e["type"] for e in parsed["equipment"].values())
print(f"\nTipos: {dict(types)}")

print("\nPrimeiras 3 conexoes:")
for c in parsed["connections"][:3]:
    print(f"  {c['pp_name']}:{c['pp_port']} -> {c['sw_name']}:{c['sw_port']} | {c['status']} | {c['deck']}")

print("\n=== IMPORT ===")
report = execute_import(parsed, skip_existing=True)

print(f"Racks criados  : {report['racks_created']}  (skip: {report['racks_skipped']})")
print(f"Equip criados  : {report['equip_created']}  (skip: {report['equip_skipped']})")
print(f"Portas criadas : {report['ports_created']}")
print(f"Conns criadas  : {report['conns_created']}  (skip: {report['conns_skipped']})")
print(f"Erros          : {len(report['errors'])}")

if report["errors"]:
    print("\nPrimeiros erros:")
    for e in report["errors"][:10]:
        print(f"  {e}")

print("\nOK - pipeline concluido")
