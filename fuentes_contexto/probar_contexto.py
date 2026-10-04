#!/usr/bin/env python3
"""fuentes_contexto/probar_contexto.py · Pruebas del contexto del cliente (4-oct-2026). Sin red.

Usa clientes INVENTADOS (ningún dato real): personas falsas en quien_esta_detras y un correo y un teléfono falsos
dentro de los textos. Comprueba:
  · la salida no lleva quien_esta_detras, ni account_ro, ni correos, ni teléfonos, ni los nombres de las personas;
  · se quedan las filas con cliente_id que existen en la lista de la app, y el resto va a sin_emparejar;
  · sin entrada: sale con error y no escribe nada;
  · una entrada vacía o rota nunca pisa una salida buena;
  · nombres: un solo mapa de todas las fichas, sin tildes ni mayúsculas, nombre de pila y apellido sueltos, palabras
    corrientes («Rosa», «sol»), el nombre del propio cliente y los sitios; el papel con barras no rompe nada;
  · teléfonos con formatos raros, sin comerse años, dinero, fechas ni porcentajes.

  python3 fuentes_contexto/probar_contexto.py      # sale con 1 si algo falla
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
GEN = AQUI / "generar_contexto.py"

# El correo y los teléfonos falsos se montan por trozos para que el escáner de secretos no los cuente como reales.
CORREO_FALSO = "pepe.inventado" + "@" + "ejemplo.test"
MOVIL_FALSO = " ".join(["612", "345", "678"])
MOVIL_FALSO_2 = "+34 " + " ".join(["612", "34", "56", "78"])

FICHAS = {
    "generado": "2026-10-04T10:00",
    "fuente": "prueba",
    "clientes": [
        {"cliente_id": "asesoria-ficticia", "carpeta": "x", "nombre": "Asesoría Ficticia", "bloque": "cartera",
         "en_una_frase": f"Despacho inventado. Escribir a {CORREO_FALSO} si hay dudas.",
         "quien_esta_detras": [{"nombre": "Pepe Inventado Pérez", "papel": "socio", "nota": f"móvil {MOVIL_FALSO}"}],
         "que_hacen": {"a_que_se_dedican": "Fiscal", "especialidad_o_nicho": None, "donde": "Ciudad Falsa",
                       "tamano": "5", "web": "https://ficticia.test"},
         "con_ro": {"servicios": "SEO", "cliente_desde": "2025-01-01", "account_ro": "Persona De Ro Falsa"},
         "objetivos": ["Más leads"], "lo_que_nos_han_dicho": [
             {"cita": f"Pepe Inventado Pérez dice que llaméis al {MOVIL_FALSO_2}", "fecha": "2026-09-01",
              "quien": "Pepe Inventado Pérez"}],
         "les_gusta": ["Rapidez"], "no_les_gusta": [], "como_trabajar_con_ellos": ["Por correo"],
         "situacion_actual": "Estable", "fuentes": ["ruta/interna.md:12"], "huecos": ["tamaño"], "estado": "activo"},
        {"cliente_id": "gestoria-de-prueba", "carpeta": "y", "nombre": "Gestoría de Prueba", "bloque": "nuevos",
         "en_una_frase": "Gestoría inventada.", "quien_esta_detras": [{"nombre": "Ana Falsa Gómez", "papel": "gerente",
                                                                       "nota": ""}],
         "que_hacen": {"a_que_se_dedican": "Laboral", "especialidad_o_nicho": None, "donde": None, "tamano": None,
                       "web": None},
         "con_ro": {"servicios": "Meta", "cliente_desde": None, "account_ro": None, "account_en_app": False},
         "objetivos": [], "lo_que_nos_han_dicho": [], "les_gusta": [], "no_les_gusta": ["Llamadas sin avisar"],
         "como_trabajar_con_ellos": [], "situacion_actual": "Arrancando", "fuentes": [], "huecos": [],
         "estado": "activo"},
        {"cliente_id": "no-esta-en-la-app", "nombre": "Despacho Fantasma", "en_una_frase": "No casa.",
         "quien_esta_detras": [], "que_hacen": {}, "con_ro": {}, "objetivos": [], "lo_que_nos_han_dicho": [],
         "les_gusta": [], "no_les_gusta": [], "como_trabajar_con_ellos": [], "situacion_actual": "",
         "fuentes": [], "huecos": [], "estado": "baja"},
    ],
}
LISTA_APP = [{"id": "asesoria-ficticia", "nombre": "Asesoría Ficticia"},
             {"id": "gestoria-prueba", "nombre": "Gestoría de Prueba"}]   # id distinto: casa por el nombre

FALLOS = []


def ok(cond, que):
    print(("  ✓ " if cond else "  ✗ ") + que)
    if not cond:
        FALLOS.append(que)


def correr(*args, env_extra=None):
    import os
    env = {k: v for k, v in os.environ.items() if k != "RO_CONTEXTO_CLIENTES"}
    env["RO_CRUDOS"] = env_extra or "/nonexistente_ro_crudos"   # que no encuentre la ruta por defecto
    return subprocess.run([sys.executable, str(GEN), *args], capture_output=True, text=True, env=env)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        entrada, lista, salida = tmp / "fichas.json", tmp / "clientes.json", tmp / "out" / "contexto.json"
        entrada.write_text(json.dumps(FICHAS, ensure_ascii=False))
        lista.write_text(json.dumps(LISTA_APP, ensure_ascii=False))
        base = ["--lista-clientes", str(lista)]

        print("1. Genera y limpia")
        r = correr("--entrada", str(entrada), "--salida", str(salida), *base)
        ok(r.returncode == 0 and salida.exists(), f"sale bien y escribe (código {r.returncode})")
        texto = salida.read_text() if salida.exists() else ""
        doc = json.loads(texto) if texto else {}
        ids = [c["cliente_id"] for c in doc.get("clientes", [])]
        ok(ids == ["asesoria-ficticia", "gestoria-prueba"], f"quedan los clientes de la app, por id o nombre: {ids}")
        ok(doc.get("sin_emparejar") == 1 and "no-esta-en-la-app" in r.stderr and "no-esta-en-la-app" not in texto,
           "el que no casa se cuenta y su id sale solo como aviso")
        ok(doc.get("fuente") == "fichas de cliente (privado)", "fuente correcta")
        ok("quien_esta_detras" not in texto, "sin quien_esta_detras")
        ok("account_ro" not in texto and "Persona De Ro Falsa" not in texto, "sin el nombre del account")
        ok("@" not in texto, "sin correos")
        ok("612" not in texto, "sin teléfonos")
        ok("Pepe" not in texto and "Ana Falsa" not in texto, "sin nombres de personas")
        ok("ruta/interna" not in texto, "sin fuentes internas")
        c0 = doc["clientes"][0] if ids else {}
        ok(c0.get("lo_que_nos_han_dicho", [{}])[0].get("papel") == "socio", "la cita lleva el papel, no el nombre")
        ok(c0.get("actualizado") == "2026-10-04", "lleva la fecha de actualización")
        ok(set(c0) == {"cliente_id", "en_una_frase", "que_hacen", "con_ro", "objetivos", "lo_que_nos_han_dicho",
                       "les_gusta", "no_les_gusta", "como_trabajar_con_ellos", "situacion_actual", "huecos",
                       "estado", "actualizado"}, "campos de la fila exactos")

        print("2. Sin entrada")
        sal2 = tmp / "out2" / "contexto.json"
        r = correr("--entrada", str(tmp / "no_existe.json"), "--salida", str(sal2), *base)
        ok(r.returncode != 0, f"sale con error (código {r.returncode})")
        ok(not sal2.exists(), "no escribe nada")
        r = correr("--salida", str(sal2), *base)
        ok(r.returncode != 0 and not sal2.exists(), "sin variable ni ruta por defecto: error y nada escrito")

        print("3. Nunca pisa una salida buena")
        buena = salida.read_text()
        vacia = tmp / "vacia.json"
        vacia.write_text(json.dumps({"generado": "2026-10-05", "fuente": "x", "clientes": []}))
        r = correr("--entrada", str(vacia), "--salida", str(salida), *base)
        ok(r.returncode != 0 and salida.read_text() == buena, "entrada vacía: error y la salida sigue igual")
        rota = tmp / "rota.json"
        rota.write_text("{esto no es json")
        r = correr("--entrada", str(rota), "--salida", str(salida), *base)
        ok(r.returncode != 0 and salida.read_text() == buena, "entrada rota: error y la salida sigue igual")
        uno = tmp / "uno.json"
        uno.write_text(json.dumps({**FICHAS, "clientes": FICHAS["clientes"][1:2]}, ensure_ascii=False))
        r = correr("--entrada", str(uno), "--salida", str(salida), *base)
        ok(r.returncode == 0, "bajar de 2 a 1 no es «menos de la mitad»: escribe")
        salida.write_text(buena)
        doc_buena = json.loads(buena)
        doc_buena["clientes"] = doc_buena["clientes"] * 3
        salida.write_text(json.dumps(doc_buena))
        r = correr("--entrada", str(uno), "--salida", str(salida), *base)
        ok(r.returncode != 0 and len(json.loads(salida.read_text())["clientes"]) == 6,
           "de 6 a 1 clientes: no escribe sin --forzar")

        print("4. --comprobar no escribe")
        sal4 = tmp / "out4" / "contexto.json"
        r = correr("--entrada", str(entrada), "--salida", str(sal4), "--comprobar", *base)
        ok(r.returncode == 0 and not sal4.exists(), "valida y no escribe")

    print("5. Nombres: mapa único, sin tildes, nombre de pila y apellido sueltos")
    import importlib
    sys.path.insert(0, str(AQUI))
    G = importlib.import_module("generar_contexto")
    doc = {"generado": "2026-10-04", "clientes": [
        {"cliente_id": "uno", "nombre": "Lunar Abogados", "que_hacen": {"donde": "Villaficticia"},
         "quien_esta_detras": [{"nombre": "Josué Ficticio Núñez", "papel": "socio"},
                               {"nombre": "Eva Sol", "papel": "gerente \\1 \\g<0>"},
                               {"nombre": "Rosa Imaginaria", "papel": "administración"},
                               {"nombre": "Lucas Lunar", "papel": "fundador"},
                               {"nombre": "Tomasín (Tomi) Villaficticia", "papel": "técnico"},
                               {"nombre": "Ximena Pruebas y Otilio Pruebas", "papel": "socios"}]},
        {"cliente_id": "dos", "nombre": "Otro Despacho",
         "quien_esta_detras": [{"nombre": "Berta Quimera", "papel": "socia de Josué Ficticio"}]}]}
    P = G.Personas(doc["clientes"])
    L1 = lambda t: G.limpiar(t, P, "uno", frozenset(G.norm("Lunar Abogados").split()))  # noqa: E731
    L2 = lambda t: G.limpiar(t, P, "dos")  # noqa: E731
    casos = [
        (L1("Habla con Josué Ficticio Núñez."), "Habla con socio."),
        (L1("Habla con JOSUE  ficticio-NUNEZ."), "Habla con socio."),            # tildes, mayúsculas, espacios
        (L2("Nos lo presentó Josue Ficticio Nunez."), "Nos lo presentó [persona]."),  # de otro cliente
        (L1("Lo lleva Josué; Núñez firma."), "Lo lleva socio; socio firma."),    # nombre y apellido sueltos
        (L2("Ficticio dijo que sí."), "[persona] dijo que sí."),
        (L1("Lo decide Eva."), "Lo decide gerente \\1 \\g<0>."),               # nombre corto; papel con barras
        (L1("Rosa lleva la agenda."), "Rosa lleva la agenda."),                  # palabra corriente a principio
        (L1("La agenda la lleva Rosa."), "La agenda la lleva administración."),  # a mitad de frase, sí
        (L1("Un ramo de rosa y sol."), "Un ramo de rosa y sol."),                # en minúscula, nunca
        (L1("Lunar Abogados crece."), "Lunar Abogados crece."),                  # el nombre del propio cliente
        (L2("Lucas y Lunar no están."), "[persona] y [persona] no están."),      # en otro cliente, sí
        (L1("Están en Villaficticia."), "Están en Villaficticia."),              # un sitio (donde)
        (L1("Llamad a Tomi o a Tomasín Villaficticia."), "Llamad a técnico o a técnico."),
        (L1("Ximena Pruebas y Otilio firman."), "socios y socios firman."),      # «A y B» en una entrada
    ]
    for got, esperado in casos:
        ok(got == esperado, f"{esperado!r}" + ("" if got == esperado else f" (sale {got!r})"))
    ok(P.papel("Josue ficticio NUNEZ", "uno") == "socio" and P.papel("Josué Ficticio Núñez", "dos") is None,
       "quien → papel solo en su cliente")
    ok(P.papel("Berta Quimera", "dos") == "socia de [persona]", "el papel también se limpia")

    print("6. Teléfonos: sí los raros; no años, dinero, fechas ni porcentajes")
    a, b, c = "600", "123", "456"
    tels = [f"{a}  {b} {c}", f"+34 ({a}) 12 34 56", f"{a}/{b}/{c}", f"{a}–{b}–{c}", f"tlf{a}{b}{c}",
            f"{a}{b}{c}ext", f"(+34) {a}{b}{c}", f"0034 {a} {b} {c}", f"91 {b} 45 67", f"{a}-12-34-56", MOVIL_FALSO_2]
    for t in tels:
        r = G.limpiar(f"Llamar al {t} mañana")
        ok(r is not None and not any(ch.isdigit() for ch in r), f"teléfono {t!r} → {r!r}")
    for t in ["En 2026 crecieron", "Factura 1.500 € al mes", "Desde el 18-sep-2026", "Reunión 18/09/2026",
              "Fecha 2026-09-18", "Sube un 45 %", "Sube un 12,5%", "Años 2024-2025-2026", "Somos 15 desde 2019",
              "Facturan 120.000 € y 3.500.000 € en total", "Del 18/09/2026 al 20/09/2026", "CP 28013"]:
        ok(G.limpiar(t) == t, f"se queda {t!r}" + ("" if G.limpiar(t) == t else f" (sale {G.limpiar(t)!r})"))
    ok(G.limpiar(f"Escribid a {CORREO_FALSO}.") == "Escribid a [dato quitado].", "correo quitado")

    print(f"\n{'TODO BIEN' if not FALLOS else f'{len(FALLOS)} FALLOS'}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
