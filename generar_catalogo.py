#!/usr/bin/env python3
"""
generar_catalogo.py · el catálogo de indicadores de la app (E0, regla R5 y R6 del plan v2).

Lee (solo lectura) las tablas «Indicadores» de 10_FICHAS/G1, G2 y G3 y la tabla U de umbrales firmados
del plan v2 (que copia 11_DECISIONES_PARA_TOMAS.md) y escribe ./indicadores.json:

  - 229 indicadores de puesto (228 de las fichas + 1 de la regla «cliente primero», R13) y, aparte,
    los 23 marcados «Fase 2» en las fichas.
  - Cada uno: id, puesto, ficha, nombre, fórmula, umbral verde/ámbar/rojo y su origen, estado de medición
    (hoy · medias · no) con el porqué, fuente, frecuencia, adelantado/retrasado, superprompt y módulo que lo pinta.
  - Si una decisión firmada (tabla U) fija el umbral, MANDA la decisión: `umbral` = el firmado,
    `umbral_ficha` = lo que decía la ficha, `decision` = D-xx.

Uso: python3 generar_catalogo.py
"""
import json
import re
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
FICHAS = RAIZ / "10_FICHAS"
PLAN = RAIZ / "12_PLAN_DE_CONSTRUCCION_v2.md"

# Cabecera de la ficha → puesto de la app
PUESTO_DE_FICHA = [
    ("Dirección · Tomás", "direccion"), ("Finanzas y administración", "administracion"),
    ("Finanzas de dirección", "finanzas_direccion"), ("Dirección de operaciones", "operaciones"),
    ("Proyectos y oferta", "proyectos"), ("RRHH", "rrhh"), ("Account manager", "account"),
    ("Trafficker de Meta", "trafficker"), ("Jefa de publicidad", "jefa_publicidad"),
    ("Especialista en GoHighLevel", "especialista_ghl"), ("Jefa de CRM", "jefa_crm"),
    ("Técnico de altas", "tecnico_altas"), ("Jefa de SEO", "jefa_seo"), ("SEO técnico", "seo"),
    ("SEO local", "ficha_google"), ("Web ·", "web"), ("Redes sociales", "redes"),
    ("Producción creativa", "produccion"), ("Setters", "setters"), ("Closer", "ventas_ro"), ("Outreach", "outreach"),
]
# Puesto → superprompt que construye su pantalla y módulo donde se pinta (plan v2)
MODULO_DE_PUESTO = {
    "direccion": ("E10", "mi-dia"), "finanzas_direccion": ("E10", "finanzas"), "administracion": ("E10", "finanzas"),
    "operaciones": ("E2", "mi-dia"), "proyectos": ("E2", "mi-dia"), "rrhh": ("E7", "personas"),
    "account": ("E3", "mi-dia"), "trafficker": ("E5", "captacion"), "jefa_publicidad": ("E5", "captacion"),
    "especialista_ghl": ("E5", "salud-crm"), "jefa_crm": ("E5", "salud-crm"), "tecnico_altas": ("E4", "clientes-nuevos"),
    "jefa_seo": ("E8", "seo-web"), "seo": ("E8", "seo-web"), "ficha_google": ("E8", "seo-web"), "web": ("E8", "seo-web"),
    "redes": ("E8", "redes"), "produccion": ("E7", "produccion"), "setters": ("E6", "ventas-ro"),
    "ventas_ro": ("E6", "ventas-ro"), "outreach": ("E6", "prospeccion"),
}
# Umbral firmado (tabla U del plan v2) que manda, por palabras del nombre del indicador.
# (palabras que deben estar todas, puestos a los que se limita o None, fila de la tabla U)
REGLAS_U = [
    (("frío",), None, "Respuesta del correo en frío"),
    (("tasa de respuesta del correo",), None, "Respuesta del correo en frío"),
    (("informe", "mensual"), None, "Informe mensual"),
    (("informes", "mensuales"), None, "Informe mensual"),
    (("respuesta", "cliente"), None, "Respuesta al cliente"),
    (("encendid", "plazo"), None, "Encendido de un alta"),
    (("horas por cuenta nueva",), None, "Horas por cuenta nueva (solo aviso)"),
    (("no planificad",), None, "Trabajo no planificado"),
    (("coste por cita",), ("trafficker", "jefa_publicidad", "account", "direccion", "operaciones"), "Coste por cita del cliente", "nota"),
    (("fatiga",), None, "Fatiga de un anuncio"),
    (("asistencia marcada",), ("setters",), None),
    (("asistencia",), ("setters", "ventas_ro"), "Asistencia a citas de RO"),
    (("asistencia",), ("especialista_ghl", "jefa_crm", "account", "trafficker", "jefa_publicidad", "direccion", "operaciones"), "Asistencia a citas de despachos"),
    (("cierre sobre",), None, "Cierre sobre celebradas (RO)"),
    (("coste por cliente captado",), None, "Coste por cliente captado por RO"),
    (("intentos",), ("setters", "ventas_ro"), "Intentos por lead (RO)"),
    (("cuentas en rojo",), ("jefa_publicidad",), "Cuentas en rojo por trafficker (Valeria)"),
    (("velocidad",), ("seo", "web", "jefa_seo", "ficha_google"), "Velocidad de la web"),
    (("rondas",), None, "Rondas de revisión por pieza"),
    (("retención neta de ingresos",), None, "Retención neta (trimestral)"),
    (("impago",), None, "Impago"),
]


# Correcciones del estado de medición posteriores a las fichas (fecha y porqué). Mandan sobre la ficha.
CORRECCIONES_MEDICION = {
    "jefa_crm.carga_por_especialista": ("medias", "Ya existe la tabla de asignaciones (E0, 2-oct), pero la silla CRM sale de horas imputadas (confianza media o baja) hasta que Mili cierre las dudas D1-D2.", "E0 ronda 4 (2-oct)"),
}


# Ronda 12 (R13) · regla de Tomás (2-oct, memoria «Métricas: cliente primero, ideal vs hoy»): «cada puesto mide primero los
# resultados de sus clientes». El número que manda del account deja de ser la salud de su cartera y pasa a ser los
# RESULTADOS de los clientes de su cartera (leads, citas y ventas frente a objetivo), cada parte con «¿se mide hoy?».
# La salud queda como SEGUNDO indicador (mismo id, para no romper a quien ya lo lee; cambia el nombre y la marca).
REGLA_CLIENTE_PRIMERO = "Regla de Tomás (2-oct): cada puesto mide primero los resultados de sus clientes"
INDICADORES_NUEVOS = {
    "account": [{
        "id": "account.resultados_de_su_cartera_frente_a_objetivo",
        "nombre": "Resultados de los clientes de su cartera frente a objetivo (el que manda)",
        "prioritario": True,
        "formula": "Clientes de su cartera con leads, citas y ventas del mes en su objetivo del alta ÷ clientes de su cartera con campaña encendida",
        "umbral": "≥ 70 % / 50-70 % / < 50 % (propuesta sin firmar: la misma vara que la trafficker)",
        "umbral_origen": f"Propuesta sin firmar del coordinador (R13) · {REGLA_CLIENTE_PRIMERO}",
        "adelantado": "Retrasado (resultado del cliente)", "frecuencia": "Diaria (leads) · semanal (citas) · mensual (ventas)",
        "fuente": "Captación (Meta + GoHighLevel) por cliente de su cartera (asignaciones); objetivo del alta (D-03)",
        "medible": "medias",
        "medible_porque": "Leads sí; citas y ventas solo en las subcuentas con GoHighLevel; el objetivo del alta no está cargado en ningún cliente (D-03), mientras se usa el techo general.",
        "partes": [
            {"que": "Leads", "medible": "hoy", "porque": "Meta y GoHighLevel por cliente, cada día (Captación)."},
            {"que": "Citas", "medible": "medias", "porque": "Solo en las subcuentas con GoHighLevel conectado; la asistencia sin marcar en muchas."},
            {"que": "Ventas", "medible": "medias", "porque": "Solo las que el despacho marca como cerradas en su embudo de GoHighLevel (90 días)."},
            {"que": "Objetivo del alta", "medible": "no", "porque": "0 clientes con objetivo cargado (D-03, se carga el día 0). Mientras: techo general de coste por lead y por cita."},
        ],
        "el_que_manda": True, "decision": None, "umbral_ficha": None,
    }],
}
SEGUNDO_INDICADOR = {
    "account.de_su_cartera_con_salud_60_el_que_manda": {
        "nombre": "% de su cartera con salud ≥ 60 (segundo indicador)",
        "segundo_de": "account.resultados_de_su_cartera_frente_a_objetivo",
        "antes": "Hasta el 2-oct era el que manda (ficha G2). Pasa a segundo por la regla «cliente primero».",
    },
}


def slug(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


def limpio(t):
    return re.sub(r"\*\*|`", "", t or "").strip()


def tabla_u():
    texto = PLAN.read_text()
    bloque = texto.split("### U · Umbrales firmados", 1)[1].split("\n---", 1)[0]
    filas = {}
    for linea in bloque.splitlines():
        if not linea.startswith("| ") or linea.startswith("| Qué") or set(linea) <= set("|-: "):
            continue
        que, umbral, decision = [x.strip() for x in linea.strip().strip("|").split("|")]
        filas[que] = {"umbral": umbral, "decision": decision}
    return filas


def estado_medicion(texto):
    t = limpio(texto)
    if t.startswith("Sí"):
        return "hoy", (t[2:].strip(" :()") or None)
    if t.startswith("Parcial") or t.startswith("A medias"):
        return "medias", (t.split(":", 1)[1].strip() if ":" in t else t[7:].strip(" ()") or None)
    return "no", (t.split(":", 1)[1].strip() if ":" in t else re.sub(r"^No( todavía)?", "", t).strip(" ()") or None)


def main():
    U = tabla_u()
    indicadores, vistos = [], set()
    for f in sorted(FICHAS.glob("G[123]_*.md")):
        puesto, ficha, modo = None, None, 0
        for linea in f.read_text().splitlines():
            if linea.startswith("### "):
                ficha = linea[4:].strip()
                puesto = next((pid for clave, pid in PUESTO_DE_FICHA if clave in ficha), None)
                modo = 0
                continue
            if linea.startswith("**Indicadores"):
                modo = 1
                continue
            if modo == 1 and linea.startswith("|"):
                modo = 2
                continue
            if modo != 2:
                continue
            if not linea.startswith("|"):
                modo = 0
                continue
            if re.match(r"^\|[\s:\-|]+\|$", linea.strip()):
                continue
            c = [x.strip() for x in linea.strip().strip("|").split("|")]
            nombre_crudo = limpio(c[0])
            fase2 = bool(re.match(r"^(⭐\s*)?Fase 2\s*·", nombre_crudo))
            nombre = re.sub(r"^(⭐\s*)?Fase 2\s*·\s*", "", nombre_crudo).replace("⭐", "").strip()
            estrella = "⭐" in c[0]
            estado, porque = estado_medicion(c[6])
            base = f"{puesto}.{slug(nombre)[:48]}"
            iid, n = base, 2
            while iid in vistos:
                iid, n = f"{base}_{n}", n + 1
            vistos.add(iid)
            sp, modulo = MODULO_DE_PUESTO.get(puesto, (None, None))
            ind = {
                "id": iid, "puesto": puesto, "ficha": f"{f.name[:2]} · {ficha.split(' · ')[0]}",
                "nombre": nombre, "prioritario": estrella, "formula": limpio(c[1]),
                "umbral": limpio(c[2]), "umbral_origen": limpio(c[7]), "decision": None, "umbral_ficha": None,
                "adelantado": limpio(c[3]), "frecuencia": limpio(c[4]), "fuente": limpio(c[5]),
                "medible": estado, "medible_porque": porque, "medible_texto": limpio(c[6]),
                "fase2": fase2, "superprompt": sp, "modulo": modulo,
            }
            # Umbral firmado: manda sobre la ficha
            n_low = nombre.lower()
            for palabras, puestos, fila, *tipo_regla in REGLAS_U:
                if all(p in n_low for p in palabras) and (puestos is None or puesto in puestos):
                    firmado = U.get(fila) if fila else None
                    if firmado and tipo_regla == ["nota"]:
                        # La decisión fija la regla por cliente; el indicador agrega clientes: el umbral de la ficha sigue.
                        ind["decision"] = firmado["decision"]
                        ind["regla_firmada"] = f"{fila}: {firmado['umbral']} ({firmado['decision']})"
                    elif firmado:
                        ind["umbral_ficha"] = ind["umbral"]
                        ind["umbral"] = firmado["umbral"]
                        ind["decision"] = firmado["decision"]
                        ind["umbral_origen"] = f"{firmado['decision']} (firmada el 2-oct; manda sobre la ficha) · ficha: {ind['umbral_origen']}"
                        ind["umbral_firmado_fila"] = fila
                    break
            if iid in CORRECCIONES_MEDICION:
                med, porque, cuando = CORRECCIONES_MEDICION[iid]
                ind.update({"medible": med, "medible_porque": porque, "medible_texto": f"{'A medias' if med == 'medias' else med}: {porque}",
                            "medible_corregido": f"{cuando} · la ficha decía: {ind['medible_texto']}"})
            # Ronda 5 (I-03): orígenes sin emojis ni códigos a la vista; el código queda en «decision» (y en «¿Qué es?»).
            for campo in ("umbral_origen", "umbral", "medible_texto", "medible_porque", "formula", "fuente"):
                if isinstance(ind.get(campo), str):
                    ind[campo] = re.sub(r"\s{2,}", " ", ind[campo].replace("RO ⭐", "Regla de RO").replace("⭐", "Regla de RO").replace("⚠️ Propuesta", "Propuesta sin firmar")
                                        .replace("Propuesta ⚠️", "Propuesta sin firmar").replace("⚠️", "propuesta sin firmar")).strip()
            ind["el_que_manda"] = "(el que manda)" in nombre
            if iid in SEGUNDO_INDICADOR:
                ind.update(SEGUNDO_INDICADOR[iid])
                ind["el_que_manda"] = False
                ind["regla"] = REGLA_CLIENTE_PRIMERO
            for nuevo in INDICADORES_NUEVOS.get(puesto, []):
                if nuevo["id"] not in vistos:             # el nuevo, delante de los de su puesto
                    vistos.add(nuevo["id"])
                    sp_n, mod_n = MODULO_DE_PUESTO.get(puesto, (None, None))
                    texto = "A medias: " + nuevo["medible_porque"]
                    indicadores.append({**nuevo, "puesto": puesto, "ficha": f"{f.name[:2]} · {ficha.split(' · ')[0]} · añadido R13",
                                        "medible_texto": texto, "fase2": False, "superprompt": sp_n, "modulo": mod_n,
                                        "regla": REGLA_CLIENTE_PRIMERO})
            indicadores.append(ind)

    puesto_ok = [i for i in indicadores if not i["fase2"]]
    resumen = {
        "total_fichas": len(indicadores),
        "de_puesto": len(puesto_ok),
        "fase2_aparte": len(indicadores) - len(puesto_ok),
        "por_estado": {e: sum(1 for i in puesto_ok if i["medible"] == e) for e in ("hoy", "medias", "no")},
        "con_umbral_firmado": sum(1 for i in indicadores if i["decision"]),
        "el_que_manda": {i["puesto"]: i["id"] for i in indicadores if i.get("el_que_manda")},
        "sin_puesto": [i["id"] for i in indicadores if not i["puesto"]],
    }
    salida = {
        "_meta": {
            "generado_por": "generar_catalogo.py",
            "fuentes": ["10_FICHAS/G1_…md", "10_FICHAS/G2_…md", "10_FICHAS/G3_…md", "12_PLAN_DE_CONSTRUCCION_v2.md tabla U (= 11_DECISIONES)"],
            "estados": {"hoy": "Se mide hoy", "medias": "A medias (y por qué)", "no": "Todavía no: no se pinta como número; va a «Fase 2» al pie"},
            "regla": "Nadie se inventa un umbral: los módulos leen este catálogo (ctx.indicador(id)).",
            "resumen": resumen,
        },
        "umbrales_firmados": U,
        "indicadores": indicadores,
    }
    (AQUI / "indicadores.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    print(json.dumps(resumen, ensure_ascii=False))


if __name__ == "__main__":
    main()
