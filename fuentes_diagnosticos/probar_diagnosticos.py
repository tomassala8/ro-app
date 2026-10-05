#!/usr/bin/env python3
"""fuentes_diagnosticos/probar_diagnosticos.py · pruebas con DATOS INVENTADOS (4-oct-2026). Sin red, sin IA, sin tocar data/.

  1. Dato de contacto: teléfonos y correos buenos, mal escritos, extranjeros, falsos.
  2. Tres despachos inventados: leads malos, despacho que no atiende y embudo sano → su veredicto.
  3. SEO: un despacho con el tráfico en el blog y otro con tráfico de servicio; búsquedas informativas y de marca.
  4. Coste por lead calificable: barato pero malo.
  5. El generador completo escribe en una carpeta temporal y la salida no lleva correos ni teléfonos.
  6. Cada diagnóstico apunta a una ficha que existe en el cerebro `calidad`.
  python3 fuentes_diagnosticos/probar_diagnosticos.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(AQUI))
import diagnosticos as D  # noqa: E402

AHORA = 1_791_100_800_000          # 4-oct-2026 ~08:00 de Madrid, en ms
H, DIA = 3600_000, 86_400_000
fallos = []


def ok(cond, que):
    if not cond:
        fallos.append(que)


def lead(i, tel="+34 612 345 6{:02d}", correo="cliente{}@despachoejemplo.es", nombre="Persona {}", horas=48, humano_min=30,
         intentos=2, cita=False, respondio=True, wa_env=1, wa_fallo=0):
    return {"contacto": f"c{i}", "creado": AHORA - horas * H, "medio": "facebook", "es_lead": True, "cita": cita,
            "privado": {"nombre": nombre.format(i) if nombre else None, "telefono": tel.format(i) if tel else None,
                        "correo": correo.format(i).replace("#", "@") if correo else None},
            "humano_min": humano_min, "intentos": intentos, "intentos_72h": intentos, "respondio": respondio,
            "wa_env": wa_env, "wa_fallo": wa_fallo}


# 1 · dato de contacto ---------------------------------------------------------------------------
# los números y correos se escriben con «~» (espacio), «_» (nada) y «#» (arroba) para que escaner_secretos.py no los tome por reales
tel = lambda t: t.replace("~", " ").replace("_", "") if t else t
for t, esperado in [(tel(a), b) for a, b in [("+34~612~345~678", "ok"), ("612_345_678", "ok"), ("0034~912~345~678", "ok"), ("612 345", "invalido"),
                    ("512_345_678", "invalido"), ("600_000_000", "repetido"), ("+52 55 1234 5678", "extranjero"),
                    ("+57 300 123 4567", "extranjero"), ("", "falta"), (None, "falta"), ("123456789", "invalido")]]:
    ok(D.calidad_telefono(t) == esperado, f"teléfono {t!r} → {D.calidad_telefono(t)} (esperado {esperado})")
for c, esperado in [(a.replace("#", "@"), b) for a, b in [("ana.lopez#despacho.es", "ok"), ("ana#gmail.com", "gratuito"), ("info#despacho.es", "rol"),
                    ("asdf#gmail.com", "basura"), ("x#yopmail.com", "desechable"), ("ana#gmial.com", "invalido"),
                    ("ana#gmail", "invalido"), ("", "falta"), ("test#hotmail.com", "basura")]]:
    ok(D.calidad_correo(c) == esperado, f"correo {c!r} → {D.calidad_correo(c)} (esperado {esperado})")
ok(D.calidad_lead({"nombre": "asdf", "telefono": "", "correo": "asdf#gmail.com".replace("#", "@")})["nivel"] == "no_calificable", "lead basura")
ok(D.calidad_lead({"nombre": "Ana", "telefono": "", "correo": "ana#gmail.com".replace("#", "@")})["nivel"] == "dudoso", "lead sin teléfono")
ok(D.calidad_lead({"nombre": "Ana", "telefono": tel("612_345_678"), "correo": ""})["nivel"] == "ok", "lead con teléfono")

# 2 · tres despachos inventados --------------------------------------------------------------------
malos = [lead(i) for i in range(12)] + [lead(20, tel="+52 55 1234 56{:02d}"), lead(21, tel="600000000"), lead(22, tel=None),
                                        lead(23, tel="612 34", correo="asdf#gmail.com", nombre="asdf"), lead(24, tel=None, correo="x{}#yopmail.com"),
                                        lead(25, tel="+57 300 123 45{:02d}"), lead(26, tel=None, correo="test#hotmail.com"),
                                        lead(27, tel="5{:02d}")]
no_atiende = [lead(i, humano_min=None, intentos=0, respondio=False) for i in range(12)] + [lead(i, humano_min=2000) for i in range(12, 20)]
sano = [lead(i, cita=(i % 5 < 2), horas=96) for i in range(20)]
for nombre, leads in (("malos", malos), ("no_atiende", no_atiende), ("sano", sano)):
    r = D.diagnosticar_cliente({"leads": leads, "oportunidades": [], "citas": []}, AHORA)
    globals()["r_" + nombre] = r
ok(r_malos["diagnosticos"][0]["estado"] == "rojo", f"calidad de «malos»: {r_malos['diagnosticos'][0]['estado']} ({r_malos['diagnosticos'][0]['lectura']})")
ok(r_malos["veredicto_embudo"]["veredicto"] == "leads_malos", f"veredicto «malos»: {r_malos['veredicto_embudo']}")
ok(r_no_atiende["diagnosticos"][1]["estado"] == "rojo", "atención de «no_atiende» debería ser rojo")
ok(r_no_atiende["veredicto_embudo"]["veredicto"] == "despacho_no_atiende", f"veredicto «no_atiende»: {r_no_atiende['veredicto_embudo']}")
ok(r_sano["veredicto_embudo"]["veredicto"] == "embudo_sano", f"veredicto «sano»: {r_sano['veredicto_embudo']}")
ok(r_sano["diagnosticos"][0]["estado"] == "verde", "calidad de «sano» debería ser verde")
poco = D.diagnosticar_cliente({"leads": sano[:4]}, AHORA)
ok(poco["diagnosticos"][0]["estado"] == "sin_dato" and poco["veredicto_embudo"]["veredicto"] == "sin_dato", "con 4 leads: sin dato")
# gestión fuera del CRM: nadie registra intentos, pero hay citas
fuera = [lead(i, humano_min=None, intentos=0, respondio=False, cita=(i < 6)) for i in range(20)]
rf = D.diag_atencion(fuera, AHORA)
ok(rf["evidencia"]["posible_gestion_fuera_del_crm"] and "fuera del CRM" in rf["lectura"], "gestión fuera del CRM no detectada")
# oportunidades que no se mueven y asistencia baja
opps = [{"creada": AHORA - 10 * DIA, "ultimo_cambio": AHORA - 10 * DIA, "etapa": "Nuevo lead"} for _ in range(8)] + \
       [{"creada": AHORA - 10 * DIA, "ultimo_cambio": AHORA - 5 * DIA, "etapa": "Cita"} for _ in range(2)]
citas = [{"inicio": AHORA - (i + 1) * DIA, "estado": "noshow" if i < 6 else "showed"} for i in range(10)]
av = D.diag_avance([lead(i, cita=(i < 6), horas=96) for i in range(20)], opps, citas, AHORA)
ok(av["evidencia"]["pct_nunca_movidas"] == 80.0 and av["evidencia"]["etapa_donde_se_quedan"] == "Nuevo lead", f"avance: {av['evidencia']}")
ok(av["estado"] == "ambar" and "solo viene" in av["lectura"], f"avance con plantones: {av['estado']} · {av['lectura']}")

# 3 · SEO --------------------------------------------------------------------------------------------
blog = {"mes": {"clics": 1000}, "paginas": [["https://despacho.es/blog/modelo-303-plazos/", 520, 9000, 6.1, 400],
                                           ["https://despacho.es/2026/05/que-es-el-iva/", 230, 5000, 8.0, 200],
                                           ["https://despacho.es/", 90, 900, 2.0, 80], ["https://despacho.es/asesoria-fiscal-zaragoza/", 60, 700, 9.0, 50]],
        "busquedas": [["modelo 303 plazo", 300, 4000, 5.0, 6], ["que es el iva", 200, 3000, 7.0, 7], ["despacho ejemplo", 80, 200, 1.0, 1],
                      ["asesoria fiscal zaragoza", 40, 600, 9.0, 10]]}
servicio = {"mes": {"clics": 400}, "paginas": [["https://despacho.es/", 150, 2000, 2.0, 140], ["https://despacho.es/gestoria-laboral-huesca/", 180, 1500, 4.0, 120],
                                              ["https://despacho.es/blog/novedades/", 40, 900, 12.0, 30]],
            "busquedas": [["gestoria huesca", 150, 1200, 3.0, 4], ["asesoria laboral huesca", 120, 900, 4.0, 5], ["como hacer una nomina", 20, 800, 14.0, 15]]}
sb, ss = D.diag_seo_blog(blog), D.diag_seo_blog(servicio)
ok(sb["estado"] == "rojo" and sb["evidencia"]["pct_blog"] == 83.3, f"SEO blog: {sb['estado']} {sb['evidencia']}")
ok(ss["estado"] == "verde", f"SEO servicio: {ss['estado']}")
# Tomás, 4-oct: con bastantes clics transaccionales el blog no hunde el diagnóstico (rojo → ámbar)
grande = {"mes": {"clics": 3000}, "paginas": [["https://despacho.es/blog/a/", 2000, 1, 1, 1], ["https://despacho.es/asesoria-fiscal/", 800, 1, 1, 1]]}
sg = D.diag_seo_blog(grande)
ok(sg["estado"] == "ambar" and sg["evidencia"]["salvado_por_transaccional"], f"blog con 800 clics de servicio: {sg['estado']} {sg['evidencia']}")
marca = D.marca_de("Despacho Ejemplo Asesores", "despachoejemplo.es")
ib, is_ = D.diag_seo_intencion(blog, marca), D.diag_seo_intencion(servicio, marca)
ok(ib["estado"] == "rojo", f"intención blog: {ib['estado']} {ib['evidencia']} marca={marca}")
ok(is_["estado"] == "verde", f"intención servicio: {is_['estado']} {is_['evidencia']}")
solo_marca = {"busquedas": [["despacho ejemplo", 300, 900, 1.0, 1], ["despacho ejemplo telefono", 60, 100, 1.0, 1], ["gestoria huesca", 20, 500, 8.0, 9]]}
ok(D.diag_seo_intencion(solo_marca, marca)["estado"] == "ambar", "solo marca debería ser ámbar")
for u, t in [("https://x.es/", "portada"), ("https://x.es/blog/a/", "blog"), ("https://x.es/asesoria-laboral/", "servicio"),
             ("https://x.es/contacto/", "contacto_legal"), ("https://x.es/en/blogs/tax/", "blog")]:
    ok(D.tipo_pagina(u) == t, f"tipo_pagina {u} → {D.tipo_pagina(u)}")

# 4 · coste por lead calificable ----------------------------------------------------------------------
cpl = D.diag_cpl_enganoso(12.0, 15.0, r_malos["diagnosticos"][0])
ok(cpl["estado"] == "rojo" and cpl["evidencia"]["coste_por_lead_calificable"] > 19.5, f"CPL engañoso: {cpl}")
ok(all(k.startswith(("cpl", "coste", "pct")) for k in cpl["evidencia"]), "dinero fuera de claves cpl*/coste*")

# 5 · generador completo con ficheros inventados ----------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp)
    (t / "ghl.json").write_text(json.dumps({"vivo": {"s1": {"leads": malos, "oportunidades": [], "citas": []},
                                                     "s2": {"leads": no_atiende, "oportunidades": [], "citas": []},
                                                     "s3": {"leads": sano, "oportunidades": opps, "citas": citas}}}))
    (t / "crm.json").write_text(json.dumps({"subcuentas": [{"sub_id": "s1", "cliente_id": "cli-malos", "nombre": "Malos", "tipo": "cliente"},
                                                           {"sub_id": "s2", "cliente_id": "cli-no-atiende", "nombre": "No atiende", "tipo": "cliente"},
                                                           {"sub_id": "s3", "cliente_id": "cli-sano", "nombre": "Sano", "tipo": "cliente"}]}))
    (t / "cap.json").write_text(json.dumps({"clientes": [{"cliente_id": "cli-malos", "cpl": {"30d": 12.0}, "objetivo": {"cpl_usado": 15}}]}))
    (t / "gsc.json").write_text(json.dumps({"clientes": {"cli-sano": {**blog, "site": "sc-domain:despachoejemplo.es"}}}))
    env = {**os.environ, "RO_DIAG_GHL": str(t / "ghl.json"), "RO_DIAG_CRM": str(t / "crm.json"), "RO_DIAG_CAPTACION": str(t / "cap.json"),
           "RO_DIAG_GSC": str(t / "gsc.json"), "RO_DIAG_AHORA": "2026-10-04 08:00"}
    p = subprocess.run([sys.executable, str(AQUI / "generar_diagnosticos.py"), "--salida", str(t / "out.json")], env=env, capture_output=True, text=True)
    ok(p.returncode == 0, f"generador: {p.stderr[-400:]}")
    if p.returncode == 0:
        texto = (t / "out.json").read_text()
        doc = json.loads(texto)
        ver = {c["cliente_id"]: c["veredicto_embudo"]["veredicto"] for c in doc["clientes"]}
        ok(ver.get("cli-malos") == "leads_malos" and ver.get("cli-no-atiende") == "despacho_no_atiende", f"veredictos del generador: {ver}")
        ok(any(d["id"] == "pub_leads_baratos_malos" and d["estado"] == "rojo" for c in doc["clientes"] for d in c["diagnosticos"]), "CPL engañoso en el generador")
        ok(any(d["id"] == "seo_trafico_blog" for c in doc["clientes"] for d in c["diagnosticos"]), "SEO en el generador")
        ok(not re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", texto), "la salida lleva un correo")
        ok(not re.search(r"(?<!\d)(?:\+34\s?)?[6789]\d{2}\s?\d{3}\s?\d{3}(?!\d)", texto), "la salida lleva un teléfono")
        ok(all(d.get("cliente_id") for c in doc["clientes"] for d in c["diagnosticos"]), "diagnóstico sin cliente_id (servir.py no podría recortar)")

# 6 · cada diagnóstico tiene su ficha en el cerebro calidad -------------------------------------------------
cer = APP / "fuentes_consejos" / "cerebros" / "calidad.json"
if cer.exists():
    c = json.loads(cer.read_text())
    ids = {s["id"] for s in c["situaciones"]}
    fichas = {r["ficha"] for r in r_malos["diagnosticos"] + [sb, ib, cpl]}
    ok(fichas <= ids, f"fichas que faltan en calidad.json: {sorted(fichas - ids)}")
    disp = {x for s in c["situaciones"] for x in s.get("disparadores", {}).get("diagnosticos", [])}
    ok(set(D.CATALOGO) <= disp, f"diagnósticos sin disparador en el cerebro: {sorted(set(D.CATALOGO) - disp)}")
else:
    fallos.append("falta fuentes_consejos/cerebros/calidad.json")

print("\n".join("✗ " + f for f in fallos) or "✓ diagnósticos: todo en orden")
sys.exit(1 if fallos else 0)
