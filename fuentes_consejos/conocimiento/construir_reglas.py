#!/usr/bin/env python3
"""fuentes_consejos/conocimiento/construir_reglas.py · Cerebro de decisiones v2 (3-oct-2026).

reglas_minadas.json (120 reglas minadas del CEREBRO Cole Gordon + Hormozi, las skills de RO, el protocolo de lanzamiento v3
y las decisiones firmadas; cada una con su fichero y línea comprobados con grep) → reglas.json, que es lo que lee el cerebro.

Añade:
  · «url»: el fichero en GitHub (repo ro-equipo, rama main, en su línea) si el fichero está en el repo: el CEREBRO va tal
    cual y las skills (~/.claude/skills/X o ~/RO_SKILLS_EQUIPO/X) van a 30_SKILLS/X/. Lo que está fuera del repo
    (Downloads, memoria) se cita por su nombre, sin enlace.
  · Los ids que usa el motor (tipos.json y diagnostico.py) como ALIAS de una regla minada: misma fuente, mismo texto.

  python3 fuentes_consejos/conocimiento/construir_reglas.py
"""
import json
import os
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO_LOCAL = Path.home() / "RO_EQUIPO"
REPO_URL = "https://github.com/tomassala8/ro-equipo/blob/main/"

ALIAS = {   # id del motor → id minado
    "diag_no_gasta": "entrega_ahogada_pacing", "diag_formulario_roto": "landing_no_convierte", "diag_fatiga": "fatiga_dos_senales",
    "diag_segmentacion": "creativo_antes_que_segmentacion", "diag_medicion": "medicion_hasta_el_cierre",
    "diag_fuga": "contacto_prueba_diario", "diag_subcuenta_sin_uso": "sin_llamador_no_se_enciende",
    "diag_velocidad": "garantia_velocidad_despacho", "diag_whatsapp": "conexiones_caidas_dueno", "diag_seguimiento": "cadencia_24h",
    "diag_citas_sin_marcar": "asistencia_despachos_bandas", "diag_asistencia": "asistencia_prioridad",
    "diag_encaje_oferta": "cpl_sano_cero_cierres",
    "rel_correo_48h": "respuesta_24_48", "rel_silencio_30d": "reunion_mensual", "rel_bloqueo_callado": "problema_lo_contamos_nosotros",
    "rel_queja_llamada": "queja_p0", "rel_informe_mensual": "informe_dia_5", "rel_desk_agente": "respuesta_24_48",
    "rel_llamadas_perdidas": "respuesta_24_48", "arranque_dia_10": "encendido_dia_10", "arranque_lista": "accesos_un_correo",
    "crm_leads_sin_tocar": "cero_leads_sin_intento", "crm_subcuenta_90d": "conexiones_caidas_dueno",
    "seo_comprobar_google": "numero_jefa_seo", "seo_top10": "seo_alerta_top10", "gmb_resenas": "resenas_goteo",
    "web_caida": "monitor_landing_avisos", "web_spam": "monitor_landing_avisos", "web_certificado": "monitor_landing_avisos",
    "web_rendimiento": "velocidad_web_bandas", "redes_calendario": "redes_constancia", "redes_fallida": "redes_volumen_pactado",
    "rrhh_conversacion": "revision_personas_escalera", "rrhh_reconocimiento": "nota_y_1a1",
    "adm_cobro": "impago_corte", "adm_alta_facturacion": "cobro_sepa", "dir_decision_reloj": "una_restriccion",
    "dir_muro": "muro_direccion", "dir_sin_account": "carga_por_puesto", "prod_devuelto_primero": "rondas_revision",
    "prod_plazo_avisar": "problema_lo_contamos_nosotros", "prod_revision_48h": "rondas_revision",
    "ventas_contrato_3d": "reloj_propuesta", "ventas_propuesta_72h": "reloj_propuesta", "ventas_marcar_resultado": "cierre_ro_bandas",
    "setter_velocidad": "velocidad_calidad_lead", "setter_confirmar": "recordatorios_manuales", "setter_marcador": "juzgar_setter",
    "outreach_positiva_4h": "respuestas_con_dueno", "outreach_clasificar": "respuestas_con_dueno",
    "proyectos_visto": "rojo_revisado_por_coti", "conexion_clave": "conexiones_caidas_dueno", "datos_en_duda": "medicion_hasta_el_cierre",
    "jefa_rojos_trafficker": "carga_por_puesto", "jefa_crm_velocidad": "garantia_velocidad_despacho",
    "ops_cartera_riesgo": "salud_umbrales_accion",
}
PROPIAS = [   # reglas que el motor necesita y no estaban minadas (fuente comprobada con grep -n)
    {"id": "diag_sin_dato", "tema": "medicion", "puestos": ["trafficker", "account", "especialista_ghl", "jefa_publicidad", "jefa_crm"],
     "regla": "Si los datos no señalan una causa, el veredicto es «sin dato suficiente»: no se cambia nada a ciegas.",
     "umbral": "ventana mínima cumplida", "autor": "RO", "fichero": "30_SKILLS/diagnostico-embudo-despacho/recursos/ARBOL.md",
     "ancla": "02 · ÁRBOL MAESTRO DE DIAGNÓSTICO FULL-FUNNEL", "linea": 39, "confianza": "alta"},
]


def ruta_repo(f):
    """Ruta relativa dentro del repo ro-equipo, o None si el fichero no está en él."""
    f = str(f or "")
    if not f:
        return None
    if not f.startswith("/"):
        return f if (REPO_LOCAL / f).exists() else None
    m = re.search(r"/(?:\.claude/skills|RO_SKILLS_EQUIPO)/([^/]+)/(.+)$", f)
    if m:
        rel = f"30_SKILLS/{m.group(1)}/{m.group(2)}"
        return rel if (REPO_LOCAL / rel).exists() else None
    if f.endswith("LANZAMIENTO_CAMPANAS_CLIENTES_2026-09-28/01_PROTOCOLO_LANZAMIENTO_v3.md"):
        rel = "15_NUEVOS_CLIENTES/_lanzamiento/01_PROTOCOLO_LANZAMIENTO_v3.md"      # copia idéntica en el repo (diff -q, 3-oct)
        return rel if (REPO_LOCAL / rel).exists() else None
    if f.startswith(str(REPO_LOCAL) + "/"):
        return f[len(str(REPO_LOCAL)) + 1:]
    return None


def con_url(r):
    rel = ruta_repo(r.get("fichero"))
    out = dict(r)
    out["fichero"] = rel or Path(str(r.get("fichero") or "")).name     # nunca una ruta del Mac en lo que viaja
    out["url"] = (REPO_URL + rel + (f"?plain=1#L{int(r['linea'])}" if r.get("linea") else "")) if rel else None
    return out


def main():
    minadas = json.loads((AQUI / "reglas_minadas.json").read_text())["reglas"]
    por_id = {r["id"]: con_url(r) for r in minadas}
    for r in PROPIAS:
        por_id[r["id"]] = con_url(r)
    faltan = [a for a, m in ALIAS.items() if m not in por_id]
    if faltan:
        raise SystemExit(f"Alias sin regla minada: {faltan}")
    for a, m in ALIAS.items():
        por_id[a] = dict(por_id[m], id=a, alias_de=m)
    out = {"_meta": "Generado por construir_reglas.py desde reglas_minadas.json (3-oct-2026). Cada regla: texto llano (parafraseado, "
                    "nunca copiado), umbral, autor (Cole Gordon, Hormozi o RO), fichero y línea comprobados, y «url» a GitHub si "
                    "está en el repo ro-equipo. Los ids con «alias_de» son los que usa el motor.",
           "reglas": sorted(por_id.values(), key=lambda r: r["id"])}
    (AQUI / "reglas.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    n_url = sum(1 for r in out["reglas"] if r.get("url"))
    print(f"reglas.json: {len(out['reglas'])} reglas ({len(minadas)} minadas + {len(PROPIAS)} propias + {len(ALIAS)} alias), {n_url} con enlace a GitHub")


if __name__ == "__main__":
    main()
