"""Regresión142 con autorización sintética: nunca activa el depósito real."""
import subprocess
import unittest
from unittest.mock import patch
import ia_real_559 as R
import probar_ia_gasto_142 as anterior

original = subprocess.Popen

def proceso_fixture(args, *resto, **kwargs):
    args = list(args)
    if len(args) < 4 or args[1] != '-c' or 'import ia_gasto as G' not in args[2] or 'fixture' not in args[2]:
        raise AssertionError('Sólo subprocesos sintéticos de la suite142')
    args[2] = args[2].replace('import ia_gasto as G', 'import ia_gasto as G\nG.IA_REAL.autorizada=lambda:True', 1)
    return original(args, *resto, **kwargs)

if __name__ == '__main__':
    with patch.object(R, 'autorizada', return_value=True), patch.object(subprocess, 'Popen', proceso_fixture):
        resultado = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(anterior))
        raise SystemExit(0 if resultado.wasSuccessful() else 1)
