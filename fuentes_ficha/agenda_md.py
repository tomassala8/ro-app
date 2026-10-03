"""agenda_md.py · lectura ESTRICTA del documento de móviles y correos del 2-oct (M4). Solo librería estándar.

leer_agenda() → {"clientes": {<título del documento>: {account, dominios, moviles[], correos[], notas[], fijos[]}},
                 "totales": {...}, "indice": {<título>: {moviles, correos}}}
Cada línea del documento se lee una vez y se cuenta: si algo no se entiende, va a «no_leido» (para el cuadre).
"""
import re
import unicodedata
from pathlib import Path

MD = Path.home() / "Downloads/MOVILES_Y_CORREOS_CLIENTES_RO_2026-10-02.md"

GENERICOS = {"info", "hello", "hola", "clientes", "cliente", "admin", "administracion", "administración", "contabilidad", "oficina",
             "general", "bookings", "recepcion", "laboral", "fiscal", "despacho", "contacto", "comercial", "facturacion", "gestion",
             "asesoria", "asesor", "consultas", "secretaria", "secretaría", "rrhh", "nominas", "marketing", "web", "mail", "correo",
             "atencion", "atencionalcliente", "soporte", "administrativo", "zaragoza", "madrid", "barcelona", "valencia", "malaga",
             "sevilla", "palma", "granada", "office", "team", "equipo", "direccion", "empresa", "empresas", "juridico", "legal",
             "abogados", "economistas", "gestoria", "tramites", "notificaciones", "avisos", "pedidos", "ventas", "sales", "accounts"}


def norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9@.+ ]", " ", t).strip()


def es_generico(c):
    local = c["correo"].split("@")[0].lower()
    base = re.sub(r"[\d._-]+", "", local)
    if base in GENERICOS or local in GENERICOS:
        return True
    return any(re.search(r"(?i)\b(email general|general|buz[oó]n)\b", n) for n in c["nombres"])


def leer_agenda():
    lineas = MD.read_text(encoding="utf-8").splitlines()
    out, indice, no_leido = {}, {}, []
    cur, modo, en_indice = None, None, False
    for n, ln in enumerate(lineas, 1):
        s = ln.rstrip()
        if s == "## Índice":
            en_indice = True; continue
        if s.startswith("## "):
            en_indice = False
            cur = s[3:].strip(); modo = None
            out[cur] = {"account": "", "dominios": [], "moviles": [], "correos": [], "notas": [], "fijos": [], "linea": n}
            continue
        if en_indice:
            m = re.match(r"^\| (.+?) \| (.+?) \| (.+?) \| (\d+) \|$", s)
            if m and m.group(1) != "Cliente":
                mv = re.search(r"\((\d+)\)", m.group(3))
                indice[m.group(1)] = {"account": m.group(2), "moviles": int(mv.group(1)) if mv else 0, "correos": int(m.group(4))}
            continue
        if not cur or not s:
            continue
        c = out[cur]
        if s.startswith("Account:"):
            c["account"] = s.split("Account:")[1].split("·")[0].strip()
            if "Dominios:" in s:
                c["dominios"] = [d.strip() for d in s.split("Dominios:")[1].split(",") if d.strip()]
        elif s.startswith("**Móviles**"):
            modo = "m"
        elif s.startswith("**Correos**"):
            modo = "c"
        elif modo == "m" and s.startswith("- "):
            if "+" in s and re.search(r"\+\d", s):
                partes = [x.strip() for x in s[2:].split(" · ")]
                i = next(i for i, x in enumerate(partes) if re.match(r"^\+\d", x))
                c["moviles"].append({"nombre": partes[0] if i > 0 else "", "detalle": " · ".join(partes[1:i]) if i > 1 else "",
                                     "tel": partes[i], "fuente": " · ".join(partes[i + 1:]).strip("_ ")})
            else:
                c["notas"].append(s[2:].strip())
                for f in re.findall(r"fijo ([\d ]{9,13})", s):
                    c["fijos"].append(f.strip())
        elif modo == "c" and s.startswith("| ") and "@" in s.split("|")[1]:
            col = [x.strip() for x in s.strip("|").split("|")]
            nombres = [x.strip().strip("'\"") for x in col[1].split(",")] if col[1] != "—" else []
            truncado = bool(nombres) and len(col[1]) >= 59
            if truncado:
                nombres = nombres[:-1]          # el documento corta la columna a 60 caracteres: el último trozo no es fiable
            c["correos"].append({"correo": col[0].lower(), "nombres": [x for x in nombres if x], "nombres_truncado": truncado,
                                 "donde": [x.strip() for x in col[2].split(",")], "veces": int(col[3]) if col[3].isdigit() else 0,
                                 "copia": int(col[4]) if len(col) > 4 and col[4].isdigit() else 0})
        elif modo == "c" and (s.startswith("| Correo") or s.startswith("|---")):
            pass
        elif modo == "c" and s.startswith("- "):
            c["notas"].append(s[2:].strip())
        else:
            no_leido.append((n, s[:80]))
    tot = {"clientes": len(out), "moviles": sum(len(x["moviles"]) for x in out.values()), "correos": sum(len(x["correos"]) for x in out.values())}
    return {"clientes": out, "indice": indice, "totales": tot, "no_leido": no_leido}


if __name__ == "__main__":
    a = leer_agenda()
    print(a["totales"], "índice:", len(a["indice"]), sum(x["moviles"] for x in a["indice"].values()), sum(x["correos"] for x in a["indice"].values()))
    for t, x in a["clientes"].items():
        i = a["indice"].get(t)
        if not i or i["moviles"] != len(x["moviles"]) or i["correos"] != len(x["correos"]):
            print("DESCUADRE", t, i, len(x["moviles"]), len(x["correos"]))
    print("no leído:", a["no_leido"][:10])
