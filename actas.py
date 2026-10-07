"""Acta y acuerdos de una reunión: una transacción local y una clave persistente por intento.

POST /api/ficha/acta valida las acciones con Manejador.validar_accion. Guarda el acta, todas las tareas,
su copia de sincronía SIMULADA, el rastro y el recibo idempotente juntos. No llama proveedores ni
_tras_accion (que podría despachar una escritura real). Un reintento devuelve el mismo recibo.
"""
import hashlib
import json
import os
import re
from datetime import date

TABLAS = (
    "CREATE TABLE IF NOT EXISTS actas_lotes (quien TEXT NOT NULL, cliente_id TEXT NOT NULL, huella TEXT NOT NULL, "
    "resultado TEXT NOT NULL, PRIMARY KEY (quien, cliente_id, huella))",
    "CREATE TABLE IF NOT EXISTS actas_claves (quien TEXT NOT NULL, clave TEXT NOT NULL, cliente_id TEXT NOT NULL, "
    "huella TEXT NOT NULL, PRIMARY KEY (quien, clave))",
)
CONTACTO = re.compile(r"[\w.+-]+@[\w-]+\.\w|(\+34|\b[6789]\d{2})[\s.-]?\d{3}[\s.-]?\d{3}\b")


class Rechazo(Exception):
    def __init__(self, codigo, texto):
        self.codigo, self.texto = codigo, texto
        super().__init__(texto)


def _texto(v, nombre, limite):
    if not isinstance(v, str) or len(v) > limite:
        raise Rechazo(400, f"«{nombre}» debe ser texto de hasta {limite} caracteres.")
    return v.strip()


def validar(h, S, real, persona, b):
    if real["id"] != persona["id"]:
        raise Rechazo(403, "Estás en «ver como»: es solo lectura. No se escribe nada.")
    if S.E.nucleo_bloqueado:
        raise Rechazo(503, "La puerta de secretos ha bloqueado los datos.")
    if not isinstance(b, dict):
        raise Rechazo(400, "Falta el acta.")
    clave = _texto(b.get("clave"), "clave de guardado", 100)
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,100}", clave):
        raise Rechazo(400, "La clave de guardado no es válida.")
    cid = _texto(b.get("cliente_id"), "cliente", 100)
    cliente = next((c for c in S.E.crudo["clientes"] if c["id"] == cid), None)
    if not cliente:
        raise Rechazo(403, "No puedes actuar sobre ese cliente.")
    fecha = b.get("fecha")
    try:
        if date.fromisoformat(fecha).isoformat() != fecha:
            raise ValueError()
    except (ValueError, TypeError):
        raise Rechazo(400, "La fecha del acta no es válida.")
    if fecha > S.hoy():
        raise Rechazo(400, "El acta no puede ser de una reunión futura.")
    notas = _texto(b.get("notas", ""), "notas", 3000)
    acuerdos = b.get("acuerdos")
    if not isinstance(acuerdos, list) or len(acuerdos) > 30:
        raise Rechazo(400, "El acta admite hasta 30 acuerdos.")
    acciones, normalizados = [], []
    acta = {"herramienta": "app", "tipo": "acta", "modulo": "ficha", "cliente_id": cid,
            "objeto": f"reunion:{cid}:{fecha}", "texto": notas[:600] or f"Acta de {cliente['nombre']} (solo acuerdos)",
            "vista_previa": {"fecha": fecha, "notas": notas, "acuerdos": normalizados}}
    # La misma validación que /api/acciones: pantalla, puesto, cliente, enlaces y herramientas permitidas.
    _cid, error = h.validar_accion(real, persona, acta)
    if error:
        raise Rechazo(error[0], error[1]["error"])
    acciones.append(acta)
    for acuerdo in acuerdos:
        if not isinstance(acuerdo, dict):
            raise Rechazo(400, "Cada acuerdo necesita texto, persona y fecha opcional.")
        texto = _texto(acuerdo.get("texto"), "acuerdo", 200)
        quien = _texto(acuerdo.get("quien"), "persona asignada", 100)
        candidato = S.E.persona(quien)
        if not texto or not candidato or candidato.get("estado", "activo") != "activo":
            raise Rechazo(400, "El acuerdo necesita texto y una persona activa.")
        if quien != real["id"] and not S.lleva_cliente(candidato, cid, S.P.contexto(candidato, S.E.crudo)):
            raise Rechazo(403, "El acuerdo solo se asigna a quien lleva ese cliente.")
        vence = acuerdo.get("vence") or None
        if vence:
            try:
                if date.fromisoformat(vence).isoformat() != vence:
                    raise ValueError()
            except (ValueError, TypeError):
                raise Rechazo(400, "La fecha de un acuerdo no es válida.")
        normalizados.append({"texto": texto, "quien": quien, "vence": vence})
        tarea = {"herramienta": "clickup", "tipo": "tarea", "modulo": "ficha", "cliente_id": cid,
                 "objeto": f"{cliente['nombre']} · {texto}"[:180],
                 "texto": f"Acuerdo de la reunión del {fecha} con {cliente['nombre']}: {texto}",
                 "vista_previa": {"tarea": f"{cliente['nombre']} · {texto}"[:180], "asignado": quien,
                                  "vence": vence, "origen": "acta de reunión", "solo_simulacion": True}}
        _cid, error = h.validar_accion(real, persona, tarea)
        if error:
            raise Rechazo(error[0], error[1]["error"])
        acciones.append(tarea)
    if not notas and not normalizados:
        raise Rechazo(400, "Escribe las notas o al menos un acuerdo.")
    if CONTACTO.search(notas + " " + " ".join(x["texto"] for x in normalizados)):
        raise Rechazo(400, "Sin correos ni teléfonos en el acta: van en Contactos.")
    huella = hashlib.sha256(json.dumps({"cliente_id": cid, "fecha": fecha, "notas": notas, "acuerdos": normalizados},
                                      sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return clave, cid, huella, acciones


def _rastro(con, S, quien, acta, n):
    datos = json.dumps({"acta_id": acta, "acuerdos": n, "modo": "simulado"}, ensure_ascii=False)
    previa = (con.execute("SELECT huella FROM registro_huellas ORDER BY id DESC LIMIT 1").fetchone() or [None])[0]
    cur = con.execute("INSERT INTO registro (quien, como, coleccion, accion, clave, datos, motivo, anula_a, origen, huella_previa) "
                      "VALUES (?,NULL,'ficha','acta_lote',?,?,NULL,NULL,'app',?)", (quien, str(acta), datos, previa))
    rid = cur.lastrowid
    creada = con.execute("SELECT creada FROM registro WHERE id=?", (rid,)).fetchone()[0]
    huella = S._huella(previa, [rid, creada, quien, None, "ficha", "acta_lote", str(acta), datos, None, None, "app"])
    con.execute("INSERT INTO registro_huellas (id, huella) VALUES (?,?)", (rid, huella))


def guardar(S, sinc, real, clave, cid, huella, acciones, *, tras_insertar=None):
    """El punto de fallo opcional solo se usa en pruebas, nunca procede del navegador."""
    with S._CANDADO_RASTRO, S.conectar() as con:
        if os.environ.get("DATABASE_URL"):
            con.execute("SELECT pg_advisory_xact_lock(hashtext(?))", ("ro-actas-lotes",))
        else:
            con.execute("BEGIN IMMEDIATE")
        previa = con.execute("SELECT cliente_id, huella FROM actas_claves WHERE quien=? AND clave=?", (real["id"], clave)).fetchone()
        if previa and (previa["cliente_id"] != cid or previa["huella"] != huella):
            raise Rechazo(409, "Esta clave ya guardó otra versión del acta. Revisa el contenido antes de reintentar.")
        lote = con.execute("SELECT resultado FROM actas_lotes WHERE quien=? AND cliente_id=? AND huella=?", (real["id"], cid, huella)).fetchone()
        if lote:
            if not previa:
                con.execute("INSERT INTO actas_claves (quien, clave, cliente_id, huella) VALUES (?,?,?,?)", (real["id"], clave, cid, huella))
            return {**json.loads(lote["resultado"]), "repetida": True}
        ids = []
        for i, a in enumerate(acciones):
            vp = dict(a["vista_previa"])
            if i:
                vp["acta"] = ids[0]
            cur = con.execute("INSERT INTO acciones (quien, herramienta, tipo, objeto, cliente_id, modulo, texto, vista_previa, estado, detalle) "
                              "VALUES (?,?,?,?,?,?,?,?,'simulada',?)", (real["id"], a["herramienta"], a["tipo"], a["objeto"], cid, "ficha", a["texto"],
                              json.dumps(vp, ensure_ascii=False), "Acta transaccional: solo simulación. No se llama ninguna API externa."))
            aid = cur.lastrowid
            ids.append(aid)
            if i:
                fila = con.execute("SELECT * FROM acciones WHERE id=?", (aid,)).fetchone()
                canal, objeto, cambio, base, ignorado = sinc.traducir(fila)
                cambio.update(asignado=vp["asignado"], vence=vp["vence"], acta=ids[0])
                sinc.crear_cambio(con, clave=sinc.clave_accion(aid), quien=real["id"], canal=canal, tipo=a["tipo"], objeto=objeto,
                                   cambio=cambio, base=base, cliente_id=cid, modulo="ficha", accion_id=aid,
                                   ignorado=ignorado, modo="simulado")
            if tras_insertar:
                tras_insertar(i, aid)
        _rastro(con, S, real["id"], ids[0], len(ids) - 1)
        resultado = {"ok": True, "id": ids[0], "tareas": ids[1:], "estado": "simulada", "simulado": True}
        con.execute("INSERT INTO actas_lotes (quien, cliente_id, huella, resultado) VALUES (?,?,?,?)",
                    (real["id"], cid, huella, json.dumps(resultado)))
        con.execute("INSERT INTO actas_claves (quien, clave, cliente_id, huella) VALUES (?,?,?,?)", (real["id"], clave, cid, huella))
        return resultado


def enganchar(Manejador, S):
    import sincronia as sinc
    with S.conectar() as con:
        for sql in TABLAS:
            con.execute(sql)
    post_orig = Manejador.api_post

    def api_post(h, ruta, real, persona, b):
        if ruta != "/api/ficha/acta":
            return post_orig(h, ruta, real, persona, b)
        try:
            clave, cid, huella, acciones = validar(h, S, real, persona, b)
            resultado = guardar(S, sinc, real, clave, cid, huella, acciones)
        except Rechazo as e:
            return h.responder(e.codigo, {"error": e.texto})
        return h.responder(200, resultado)

    Manejador.api_post = api_post
