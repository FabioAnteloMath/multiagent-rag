import sqlite3
import os
DB = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'db', 'multiagent_rag.db')
DB = os.path.abspath(DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('=== Classifier agent? ===')
rows = list(cur.execute(
    "SELECT name, specialty, provider, model_name FROM agents "
    "WHERE LOWER(name) LIKE ? OR LOWER(specialty) = ?",
    ('%classif%', 'classifier')
))
if rows:
    for r in rows:
        print('  Found classifier agent:', r)
else:
    print('  NONE -> classificador usa default: minimax / MiniMax-M2.7')

print()
print('=== All agents + their models ===')
print(f'  {"role":10} {"name":20} | {"specialty":12} | {"provider":10} / {"model"}')
print('  ' + '-' * 80)
for row in cur.execute(
    'SELECT name, specialty, provider, model_name, is_fallback '
    'FROM agents ORDER BY is_fallback DESC, name'
):
    role = 'FALLBACK' if row[4] else 'specialist'
    print(f'  [{role:10}] {row[0]:20} | {row[1]:12} | {row[2]:10} / {row[3]}')
