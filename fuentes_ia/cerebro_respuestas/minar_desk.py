#!/usr/bin/env python3
"""fuentes_ia/cerebro_respuestas/minar_desk.py · cerebro de respuestas · 3-oct-2026.

Mina las respuestas REALES del equipo de RO en Zoho Desk (SOLO LECTURA, ~/RO_HERRAMIENTAS/zoho/zh.py) para sacar
patrones por tipo de correo: longitud, saludo, reconocimiento, qué se hace y cuándo, cierre.

  python3 fuentes_ia/cerebro_respuestas/minar_desk.py [--tickets 450] [--dias 365]

Salida PRIVADA: data/ia/_privado/minado_desk.json (pares «correo del cliente → respuesta del equipo», texto limpio de
correos, teléfonos y credenciales). No se sirve nunca. De aquí sale, ya anonimizado, patrones.json (analizar.py).
Nada se escribe en Desk.
"""
import html
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent.parent
sys.path.insert(0, str(APP))
import config  # noqa: E402
import escaner_secretos as ESC  # noqa: E402

sys.path.insert(0, str(config.HERRAMIENTAS / "zoho"))
DESK = "https://desk.zoho.eu/api/v1"
SALIDA = APP / "data/ia/_privado/minado_desk.json"
DEPS = {"157377000000741729": "Marketing Clientes.", "157377000013886031": "Marketing Clientes"}
RUIDO_ASUNTO = re.compile(r"(?i)candidatura|bofu|reuni[oó]n agendada|nuevo lead|formulario|newsletter|webinar|invitaci[oó]n|"
                          r"out of office|fuera de la oficina|respuesta autom|notificaci[oó]n|alerta|delivery status|undeliver")
RE_CREDENCIAL = re.compile(r"(?i)\b(usuari[oa]s?|user(?:name)?|login|contrase(?:ñ|n)a|password|passw(?:or)?d|pass|clave|pwd|pin)(\s*[:=]\s*)(\S+)")
CORTE_CITA = re.compile(r"\n?(?:El .{5,160}? escribió:|On .{5,160}? wrote:|De: |From: |-----Original|________________|"
                        r"---- El |NOTA LEGAL|AVISO LEGAL|PROTECCIÓN DE DATOS|Este correo electrónico puede contener|"
                        r"Este mensaje y sus archivos|CONFIDENCIALIDAD)", re.S)


def limpiar(t):
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", t or "")
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = RE_CREDENCIAL.sub(r"\1\2[quitado]", t)
    for nombre, pat in ESC.PATRONES:
        t = pat.sub("[" + nombre + " quitado]", t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t).strip()
    t = CORTE_CITA.split(t)[0].strip()
    return t[:4000]


def main():
    n_max = int(sys.argv[sys.argv.index("--tickets") + 1]) if "--tickets" in sys.argv else 450
    dias = int(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else 365
    import zh
    tk, _ = zh.acceso()
    oid = "20094453246"

    def g(ruta):
        req = urllib.request.Request(DESK + ruta, headers={"Authorization": "Zoho-oauthtoken " + tk, "orgId": oid})
        for _ in range(3):
            try:
                b = urllib.request.urlopen(req, timeout=60).read()
                return json.loads(b) if b else {"data": []}
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503):
                    import time; time.sleep(3)
                    continue
                return {"_error": e.code}
            except Exception:
                import time; time.sleep(2)
        return {"_error": "red"}

    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    cand = []
    for dep in DEPS:
        frm = 1
        while frm < 4000:
            r = g(f"/tickets?departmentId={dep}&from={frm}&limit=100&sortBy=-createdTime&include=assignee")
            lote = r.get("data", [])
            for t in lote:
                ct = datetime.fromisoformat(t["createdTime"].replace("Z", "+00:00"))
                if ct < desde:
                    continue
                if int(t.get("threadCount") or 0) < 2 or RUIDO_ASUNTO.search(t.get("subject") or ""):
                    continue
                cand.append(t)
            if len(lote) < 100 or (lote and datetime.fromisoformat(lote[-1]["createdTime"].replace("Z", "+00:00")) < desde):
                break
            frm += 100
    print("candidatos", len(cand))
    cand.sort(key=lambda t: -int(t.get("threadCount") or 0))
    cand = cand[:n_max]

    def uno(t):
        th = g(f"/tickets/{t['id']}/threads?limit=30")
        hilos = sorted(th.get("data", []), key=lambda m: m.get("createdTime") or "")[-10:]
        msgs = []
        for m in hilos:
            if m.get("visibility") != "public" and m.get("direction") != "in":
                continue
            x = g(f"/tickets/{t['id']}/threads/{m['id']}?include=plainText")
            texto = limpiar(x.get("plainText") or x.get("content") or m.get("summary") or "")
            a = m.get("author") or {}
            msgs.append({"fecha": (m.get("createdTime") or "")[:16].replace("T", " "), "direccion": "entrante" if m.get("direction") == "in" else "saliente",
                         "de": a.get("name") or "", "tipo_autor": a.get("type"), "texto": texto})
        asg = t.get("assignee") or {}
        return {"numero": t["ticketNumber"], "asunto": t.get("subject"), "estado": t.get("status"), "creado": t["createdTime"][:10],
                "cuenta_id": t.get("accountId"), "asignado": " ".join(x for x in (asg.get("firstName"), asg.get("lastName")) if x),
                "mensajes": msgs}

    with ThreadPoolExecutor(6) as ex:
        tickets = [r for r in ex.map(uno, cand) if r["mensajes"]]
    SALIDA.write_text(json.dumps({"generado": datetime.now().strftime("%Y-%m-%d %H:%M"), "fuente": "Zoho Desk (zh.py, solo lectura)",
                                  "dias": dias, "tickets": tickets}, ensure_ascii=False, indent=1))
    print("→", SALIDA, len(tickets), "tickets")


if __name__ == "__main__":
    main()
