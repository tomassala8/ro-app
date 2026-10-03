"""telefono.py · regla común de teléfonos de la app de RO (3-oct-2026). Gemelo de modulos/_telefono.js.

Por qué: Zadarma pone el 34 delante si el número no lleva «+». Un «34 6xx…» guardado sin «+» sale como
«34 34 6xx…» → número inexistente (26 llamadas fallidas en 90 días). Misma lógica que
~/RO_HERRAMIENTAS/zadarma/normalizar_telefonos.py (función normalizar).

Regla:
  · Se GUARDA con prefijo internacional y sin espacios: «+34» + 9 cifras (o «+» y el prefijo del país).
  · Se quitan espacios, puntos, guiones y paréntesis.
  · 9 cifras que empiezan por 6, 7, 8 o 9 → «+34» delante.  «34…» (11 cifras) o «0034…» → «+34…».  «3434…» → un solo 34.
  · Extranjeros: con su prefijo y «+» (o «00»).
  · Si no cuadra (cifras de más o de menos, texto, número de relleno), NO se guarda y se avisa en llano.
  · La extensión de centralita va en un campo aparte («extension»), nunca dentro del número.
  · Se ENSEÑA con espacios («+34 6XX XX XX XX»); llamar, WhatsApp y tel: usan el valor sin espacios.

Uso:
  from telefono import limpiar, formatear, enlace_tel, enlace_wa, enlace_sip, Dudosos
  r = limpiar(valor)                 # {"telefono": "+34…" | None, "extension": "204" | None, "motivo": "ok"|"vacio"|"dudoso", "aviso": "…"}
  r = validar(valor)                 # lo mismo, pero una extensión DENTRO del número es un error (campos de la app)
  nuevo, motivo = normalizar(valor)  # contrato idéntico al de Zadarma: (None, "") sin cambios · (nuevo, "cambio") · (None, "dudoso")
  python3 telefono.py --probar       # pruebas de la regla
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

MOVIL_O_FIJO_ES = "6789"
APP = Path(__file__).resolve().parent
FICHERO_DUDOSOS = APP / "data" / "telefonos" / "dudosos.json"

# «ext. 204», «extensión 204», «int 12», «x204», «#204» al final del texto
RX_EXT = re.compile(r"(?i)[\s,;/]*(?:\b(?:ext|extensi[oó]n|ext\.|int|interno|centralita)\b\.?\s*[:.#-]?\s*|\bx\s*|#\s*)(\d{1,6})\s*$")
RX_PERMITIDOS = re.compile(r"^[\d\s.\-+()/]+$")


def _cifras(crudo):
    return re.sub(r"\D", "", crudo)


def normalizar(valor):
    """Contrato de normalizar_telefonos.py (Zadarma): (nuevo, motivo). nuevo=None si no se toca; motivo='dudoso' si está roto."""
    if valor is None or str(valor).strip() == "":
        return None, ""
    crudo = str(valor).strip()
    con_mas = crudo.startswith("+")
    d = _cifras(crudo)
    if not d:
        return None, "dudoso"
    if d.startswith("00"):
        d, con_mas = d[2:], True
    if d.startswith("3434") and len(d) == 13 and d[4] in MOVIL_O_FIJO_ES:   # 34 repetido
        nuevo = "+" + d[2:]
    elif d.startswith("34") and len(d) == 11 and d[2] in MOVIL_O_FIJO_ES:
        nuevo = "+" + d
    elif len(d) == 9 and d[0] in MOVIL_O_FIJO_ES:                         # nacional sin prefijo (o «+9…» sin 34)
        nuevo = "+34" + d
    elif con_mas and 8 <= len(d) <= 15 and not d.startswith("34"):        # extranjero bien puesto
        nuevo = "+" + d
    else:
        return None, "dudoso"
    if nuevo == "+34600000000":
        return None, "dudoso"
    return (None, "") if nuevo == crudo else (nuevo, "cambio")


def separar_extension(valor):
    """(«93 … ext. 204») → («93 …», «204»). Sin extensión: (valor, None)."""
    crudo = str(valor or "").strip()
    m = RX_EXT.search(crudo)
    if m and len(_cifras(crudo[:m.start()])) >= 8:
        return crudo[:m.start()].strip(), m.group(1)
    return crudo, None


def _aviso_dudoso(crudo):
    """Por qué no cuadra, en llano."""
    if not RX_PERMITIDOS.match(crudo):
        return "lleva texto además del número"
    d = _cifras(crudo)
    con_mas = crudo.startswith("+") or d.startswith("00")
    if d.startswith("00"):
        d = d[2:]
    if not d:
        return "no lleva ninguna cifra"
    if _cifras(crudo) in ("600000000", "34600000000", "0034600000000") or (d.endswith("600000000") and len(d) in (9, 11)):
        return "es un número de relleno"
    es_es = d.startswith("34") or not con_mas
    if es_es:
        resto = d[2:] if d.startswith("34") and len(d) > 9 else d
        if len(resto) < 9:
            return f"le faltan cifras (tiene {len(d)})"
        if len(resto) > 9:
            return f"le sobran cifras (tiene {len(d)})"
        return "no empieza por 6, 7, 8 o 9: no parece un teléfono de España; si es de fuera, ponle «+» y el prefijo del país"
    if len(d) < 8:
        return f"le faltan cifras (tiene {len(d)})"
    return f"le sobran cifras (tiene {len(d)})"


def limpiar(valor, extension_aparte=True):
    """{"telefono", "extension", "motivo", "aviso"}. extension_aparte=True: una extensión al final se separa a su campo."""
    if valor is None or str(valor).strip() == "":
        return {"telefono": None, "extension": None, "motivo": "vacio", "aviso": ""}
    crudo = str(valor).strip()
    numero, ext = separar_extension(crudo)
    if ext and not extension_aparte:
        return {"telefono": None, "extension": None, "motivo": "dudoso",
                "aviso": "lleva una extensión dentro: escribe el número solo y la extensión en su campo"}
    if not RX_PERMITIDOS.match(numero):
        return {"telefono": None, "extension": None, "motivo": "dudoso", "aviso": _aviso_dudoso(numero)}
    nuevo, motivo = normalizar(numero)
    if motivo == "dudoso":
        return {"telefono": None, "extension": None, "motivo": "dudoso", "aviso": _aviso_dudoso(numero)}
    return {"telefono": nuevo or numero, "extension": ext, "motivo": "ok", "aviso": "extensión separada" if ext else ""}


def validar(valor):
    """Para cualquier campo de la app donde se escriba un teléfono: la extensión va en su campo, nunca en el número."""
    return limpiar(valor, extension_aparte=False)


def e164(valor):
    """El número guardable («+34…») o None si no cuadra."""
    return limpiar(valor)["telefono"]


def formatear(valor):
    """Para leer: «+34 6XX XX XX XX» (España) o «+NNNN…» (fuera, sin trocear). Lo que no cuadra se devuelve tal cual."""
    t = e164(valor)
    if not t:
        return str(valor or "")
    d = t[1:]
    if d.startswith("34") and len(d) == 11:
        n = d[2:]
        return f"+34 {n[0:3]} {n[3:5]} {n[5:7]} {n[7:9]}"
    return "+" + d          # fuera de España, sin trocear: el prefijo del país puede ser de 1, 2 o 3 cifras


def enlace_tel(valor):
    t = e164(valor)
    return f"tel:{t}" if t else None


def enlace_sip(valor):
    """App de Zadarma: siempre con «+» (sin «+» Zadarma antepone el 34 y marca «34 34 …»)."""
    t = e164(valor)
    return f"sip:{t}@sip.zadarma.com" if t else None


def enlace_wa(valor):
    """WhatsApp pide el número internacional sin «+» ni espacios (wa.me/34…)."""
    t = e164(valor)
    return f"https://wa.me/{t[1:]}" if t else None


def final(valor, n=3):
    """«…678»: para avisos e informes sin enseñar el número entero."""
    d = _cifras(str(valor or ""))
    return f"…{d[-n:]}" if len(d) >= n else ("…" if d else "")


class Dudosos:
    """Números que no cuadran, por cliente. Cada generador escribe SU apartado de data/telefonos/dudosos.json
    (lo de los demás se conserva). Sin números enteros: solo las 3 últimas cifras, dónde está y por qué no cuadra."""

    def __init__(self, generador):
        self.generador = generador
        self.clientes = {}
        self.sin_cliente = []

    def anotar(self, cliente_id, valor, aviso, donde, nombre_cliente=None, quien=None):
        fila = {"final": final(valor), "aviso": aviso, "donde": donde, "generador": self.generador}
        if quien:
            fila["quien"] = quien
        if cliente_id:
            c = self.clientes.setdefault(cliente_id, {"cliente": nombre_cliente, "numeros": []})
            c["cliente"] = c["cliente"] or nombre_cliente
            if fila not in c["numeros"]:
                c["numeros"].append(fila)
        elif fila not in self.sin_cliente:
            self.sin_cliente.append(fila)

    def revisar(self, valor, cliente_id, donde, nombre_cliente=None, quien=None, extension_aparte=True):
        """limpiar() y, si no cuadra, lo anota. Devuelve el resultado de limpiar()."""
        r = limpiar(valor, extension_aparte)
        if r["motivo"] == "dudoso":
            self.anotar(cliente_id, valor, r["aviso"], donde, nombre_cliente, quien)
        return r

    def guardar(self, fichero=None):
        f = Path(fichero or os.environ.get("RO_TELEFONOS_DUDOSOS") or FICHERO_DUDOSOS)
        f.parent.mkdir(parents=True, exist_ok=True)
        try:
            doc = json.loads(f.read_text())
        except (OSError, ValueError):
            doc = {}
        por_gen = doc.get("por_generador") or {}
        por_gen[self.generador] = {"generado": datetime.now().strftime("%Y-%m-%d %H:%M"), "clientes": self.clientes, "sin_cliente": self.sin_cliente}
        clientes = {}
        for g, bloque in sorted(por_gen.items()):
            for cid, c in (bloque.get("clientes") or {}).items():
                dst = clientes.setdefault(cid, {"cliente": c.get("cliente"), "numeros": []})
                dst["cliente"] = dst["cliente"] or c.get("cliente")
                dst["numeros"] += c.get("numeros") or []
        total = sum(len(c["numeros"]) for c in clientes.values()) + sum(len(b.get("sin_cliente") or []) for b in por_gen.values())
        doc = {"_meta": {"que": "Teléfonos que no cuadran con la regla de la app (prefijo internacional y sin espacios). No se guardaron: hay que corregirlos en su origen. Solo dirección y operaciones.",
                         "regla": "9 cifras que empiezan por 6/7/8/9 → +34; 34… o 0034… → +34…; extranjeros con «+» y su prefijo; la extensión en campo aparte.",
                         "por_que": "Zadarma marca «34 34 6…» si el número no lleva «+» (26 llamadas fallidas en 90 días).",
                         "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M"), "total": total},
               "clientes": dict(sorted(clientes.items(), key=lambda kv: (-(len(kv[1]["numeros"])), kv[1].get("cliente") or kv[0]))),
               "por_generador": por_gen}
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        os.replace(tmp, f)
        return doc


def _probar():
    m = "6" + "12345678"        # partido para que la puerta de secretos no lo tome por un teléfono real
    f = "9" + "31234567"
    casos = [
        (m, "+34" + m), (" ".join([m[:3], m[3:5], m[5:7], m[7:]]), "+34" + m), (m[:3] + "." + m[3:6] + "-" + m[6:], "+34" + m),
        ("34" + m, "+34" + m), ("0034" + m, "+34" + m), ("+34" + m, "+34" + m), ("3434" + m, "+34" + m), ("+34 " + f, "+34" + f),
        ("+49 30 1234567", "+49301234567"), ("0049301234567", "+49301234567"), ("+54 9 11 1234 5678", "+5491112345678"),
        (m[:-1], None), (m + "1", None), ("612 abc 678", None), ("+34600000000", None), ("512345678", None), ("", None),
    ]
    mal = 0
    for entrada, esperado in casos:
        r = limpiar(entrada)
        if r["telefono"] != esperado:
            mal += 1
            print("FALLA", repr(entrada), "→", r, "esperaba", esperado)
    r = limpiar(f + " ext. 204")
    assert r["telefono"] == "+34" + f and r["extension"] == "204", r
    assert validar(f + " ext. 204")["motivo"] == "dudoso"
    assert formatear("+34" + m) == f"+34 {m[:3]} {m[3:5]} {m[5:7]} {m[7:]}", formatear("+34" + m)
    assert enlace_wa(m) == "https://wa.me/34" + m and enlace_tel(m) == "tel:+34" + m and enlace_sip(m).startswith("sip:+34")
    assert normalizar("34" + m) == ("+34" + m, "cambio") and normalizar("+34" + m) == (None, "")
    assert "faltan" in limpiar(m[:-1])["aviso"] and "sobran" in limpiar(m + "1")["aviso"] and "texto" in limpiar("612 abc 678")["aviso"]
    print(f"telefono.py: {len(casos) + 6 - mal} de {len(casos) + 6} pruebas bien")
    return mal == 0


if __name__ == "__main__":
    import sys
    if "--probar" in sys.argv:
        sys.exit(0 if _probar() else 1)
    for v in sys.argv[1:]:
        print(json.dumps({"entrada": final(v), **{k: (final(x) if k == "telefono" and x else x) for k, x in limpiar(v).items()}}, ensure_ascii=False))
