"""DTO real300 en SQLite temporal; sin servidor ni datos de trabajo."""
import json
from datetime import datetime,timezone
from unittest.mock import patch
from probar_operaciones_prioridades_300 import Prioridades,M
class Reloj(datetime):
 @classmethod
 def now(cls,tz=None):return datetime(2026,10,3,12,0,tzinfo=timezone.utc)
def fixture(truncado=False):
 t=Prioridades();t.setUp()
 try:
  with patch.object(M,'datetime',Reloj):
   t.save(t.b())
   t.save(t.b(revision=1,estado='resuelto',nota='Comprobación declarada, sin verificación externa'))
   if truncado:
    for revision in range(2,22):t.save(t.b(revision=revision,estado='empujado',nota='Declaración fixture'))
  return t.read()
 finally:t.doCleanups()
if __name__=='__main__':
 import sys
 print(json.dumps(fixture('--truncado' in sys.argv),ensure_ascii=False))
