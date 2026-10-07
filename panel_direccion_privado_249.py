"""El panel de resultados personal se reserva a Tomás real y visto.

Sin IO ni decisiones sobre otras pantallas. El catálogo actual es la autoridad;
los snapshots de sesión no conservan un permiso revocado.
"""


def permitido(real, vista, personas):
    if not isinstance(real, dict) or not isinstance(vista, dict):
        return False
    if real.get('id') != 'tomas' or vista.get('id') != 'tomas':
        return False
    if not isinstance(personas, list):
        return False
    candidatos = [p for p in personas if isinstance(p, dict) and p.get('id') == 'tomas']
    if len(candidatos) != 1:
        return False
    canonica = candidatos[0]
    return (canonica.get('estado') == 'activo' and canonica.get('activo') is not False
            and isinstance(canonica.get('puestos'), list) and 'direccion' in canonica['puestos'])
