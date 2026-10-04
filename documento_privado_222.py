"""222: cache de UN documento de fuente, sin actores/roles/permisos/índices owners.

El consumidor trata el documento como sólo lectura. No se crea copia profunda
por petición: los índices de autorización se reconstruyen con datos actuales.
"""
import json
import threading
from pathlib import Path


class DocumentoPrivado:
    def __init__(self):
        self._lock = threading.RLock()
        self._firma = None
        self._documento = {}

    @staticmethod
    def firma(path):
        try:
            st = path.stat()
            return (str(path.absolute()), st.st_dev, st.st_ino, st.st_mtime_ns,
                    st.st_ctime_ns, st.st_size)
        except OSError:
            return None

    @staticmethod
    def cargar(path):
        try:
            d = json.loads(path.read_text())
            return d if isinstance(d, dict) else None
        except (OSError, ValueError, TypeError, RecursionError, UnicodeError):
            return None

    def leer(self, path):
        path = Path(path)
        with self._lock:
            for _ in range(2):
                antes = self.firma(path)
                if antes is None:
                    # No conservar documento anterior si desaparece la fuente.
                    self._firma, self._documento = None, {}
                    return self._documento
                if self._firma == antes:
                    return self._documento
                d = self.cargar(path)
                despues = self.firma(path)
                if antes == despues:
                    if d is None:
                        # Errores transitorios tampoco quedan cacheados para siempre.
                        self._firma, self._documento = None, {}
                        return self._documento
                    self._firma, self._documento = despues, d
                    return d
            # Carrera persistente: no publicar ni servir el snapshot obsoleto.
            self._firma, self._documento = None, {}
            return self._documento
