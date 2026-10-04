"""Recomendaciones de lectura sobre datasets previamente autorizados.

Puro: no archivos, red, mutaciones ni juicios contractuales. El llamador recorta
los tres documentos por identidad real y vista antes de llamar generar().
La vigencia metodológica procede de RO_EQUIPO/50_PRODUCTO/_AVISO_VIGENCIA.md
(1-sep-2026); los datos no acreditan reuniones válidas ni devolución alguna.
"""
from datetime import date, datetime
from math import isfinite
from paid_mediciones_331 import ventana as medir_paid331


def _numero(valor):
    if isinstance(valor, bool):
        return None
    try:
        n = float(valor)
        return n if isfinite(n) and n >= 0 else None
    except (TypeError, ValueError):
        return None


def _fecha(valor):
    try:
        if type(valor) is date:
            return valor
        if not isinstance(valor, str):
            return None
        return date.fromisoformat(valor) if len(valor) == 10 else datetime.fromisoformat(valor.replace('Z', '+00:00')).date()
    except (TypeError, ValueError):
        return None


def _conteo(valor):
    n = _numero(valor)
    return int(n) if n is not None and n == int(n) else None


def _fuente(doc, hoy):
    if not isinstance(doc, dict):
        return {"estado": "ausente", "fecha": None, "medido_hasta": None}
    generado = _fecha(doc.get("generado"))
    hasta = _fecha(doc.get("datos_hasta")) if "datos_hasta" in doc else generado
    # Fecha de generación no sustituye una fecha de medición explícita antigua.
    vigente = generado and hasta and 0 <= (hoy - generado).days <= 2 and 0 <= (hoy - hasta).days <= 2
    return {"estado": "actual" if vigente else "sin_vigencia", "fecha": doc.get("generado"),
            "medido_hasta": hasta.isoformat() if hasta else None,
            "fecha_base": "datos_hasta" if doc.get("datos_hasta") else "generacion_del_dataset",
            "cobertura": "no_acreditada"}


def _filas(doc, clave):
    resultado, duplicados = {}, set()
    for fila in (doc or {}).get(clave, []) or []:
        if not isinstance(fila, dict) or not fila.get("cliente_id"):
            continue
        cid = str(fila["cliente_id"])
        if cid in resultado:
            duplicados.add(cid)
        else:
            resultado[cid] = fila
    for cid in duplicados:
        resultado.pop(cid, None)  # No sumar subcuentas ni escoger una arbitrariamente.
    return resultado, duplicados


def _par(dic, numerador, denominador):
    n, d = _numero(dic.get(numerador)), _numero(dic.get(denominador))
    if n is None or d is None or d == 0 or n > d or n != int(n) or d != int(d):
        return None
    return int(n), int(d)


def _semanas_comparables(doc, hoy):
    ventanas = (doc or {}).get("ventanas") or {}
    periodos = []
    for key in ("7d_prev", "7d"):
        raw = ventanas.get(key)
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            return False
        a, b = (_fecha(x) for x in raw)
        if a is None or b is None or (b - a).days != 6 or b >= hoy:
            return False
        periodos.append((a, b))
    hasta = _fecha((doc or {}).get("datos_hasta"))
    return (periodos[1][0] - periodos[0][1]).days == 1 and hasta is not None and periodos[1][1] == hasta


def generar(captacion=None, crm=None, objetivos=None, hoy=None, metodo=None):
    """JSON {version,fecha,recomendaciones,cobertura}; hoy ISO/date para replay.

    None significa fuente no accesible/disponible. Nunca se buscan datos fuera
    de los argumentos. No se utilizan nombres, contactos, enlaces ni textos
    libres de las filas como contenido de recomendaciones.
    """
    fecha = _fecha(hoy) if hoy is not None else date.today()
    if fecha is None:
        raise ValueError("hoy debe ser una fecha ISO válida")
    paid_fecha = ({**captacion, "generado": captacion["captacion_generado"]}
                  if isinstance(captacion, dict) and captacion.get("captacion_generado") else captacion)
    crm_fecha = crm
    ghl = ((crm or {}).get("fuentes") or {}).get("ghl")
    if isinstance(ghl, dict):
        crm_fecha = {"generado": ghl.get("hora")}
        if "datos_hasta" in (crm or {}):
            crm_fecha["datos_hasta"] = crm["datos_hasta"]
    fuentes = {"captacion": _fuente(paid_fecha, fecha), "crm": _fuente(crm_fecha, fecha),
               "objetivos": _fuente(objetivos, fecha)}
    if isinstance(ghl, dict):
        fuentes["crm"]["fecha_base"] = "datos_hasta" if "datos_hasta" in (crm or {}) else "lectura_ghl"
        fuentes["crm"]["fecha_generacion_dataset"] = (crm or {}).get("generado")
        if ghl.get("estado") not in (None, "bien"):
            fuentes["crm"]["estado"] = "sin_vigencia"
    paid, dp = _filas(captacion, "clientes")
    cuentas, dc = _filas(crm, "subcuentas")
    goals, dg = _filas(objetivos, "clientes")
    ids = sorted(set(paid) | set(cuentas) | dp | dc)
    recomendaciones, clientes, emitidas = [], [], set()

    for cid in ids:
        k, s = paid.get(cid), cuentas.get(cid)
        equipo = (k or {}).get("equipo") or {}
        owners = {"trafficker": equipo.get("trafficker"),
                  "crm": (s or {}).get("especialista_id") or equipo.get("crm"),
                  "account": (s or {}).get("account_id") or equipo.get("account")}
        gaps = []
        cadena = {"paid": "sin_dato", "crm": "sin_dato", "recibidos": "sin_dato",
                  "cualificados": "no_instrumentado", "citas": "sin_dato", "cierre": "sin_dato"}

        def recomendar(regla, area, titulo, motivo, accion, role, datos, prioridad=2,
                       certeza="señal", entrega="Registrar la comprobación y su resultado.", fuente=None, periodo=None,
                       fecha_evidencia=None):
            llave = (cid, regla)
            if llave in emitidas:
                return
            emitidas.add(llave)
            f = fuente or ("captacion" if area == "paid" else "crm")
            recomendaciones.append({"cliente_id": cid, "regla_id": regla, "area": area,
                "titulo": titulo, "motivo": motivo, "accion": accion, "prioridad": prioridad,
                "responsable_id": owners.get(role), "responsable_role": role,
                "evidencias": [{"fuente": f, "fecha": fecha_evidencia if fecha_evidencia is not None else fuentes[f]["fecha"],
                    "periodo": periodo, "cobertura": "registros_observados_no_exhaustivos",
                    "vigencia": fuentes[f]["estado"], "texto": datos}],
                "certeza": certeza, "criterio_entrega": entrega,
                "responsabilidad": "Seguimiento y verificación con el despacho" if regla in ("crm_primera_hora", "crm_cuatro_intentos") else "Comprobación operativa",
                "ejecutor_operativo": "despacho" if regla in ("crm_primera_hora", "crm_cuatro_intentos") else role,
                "modulo_destino": "captacion" if area == "paid" else "salud-crm"})

        for f, fila, repetidos in (("captacion", k, dp), ("crm", s, dc)):
            if cid in repetidos:
                gaps.append({"fuente": f, "codigo": "identidad_duplicada", "texto": "Varias filas para el cliente: no se agregan ni se diagnostican."})
            elif fila is None:
                gaps.append({"fuente": f, "codigo": "sin_fila", "texto": "Sin datos accesibles de esta fuente para el cliente."})
            elif fuentes[f]["estado"] != "actual":
                gaps.append({"fuente": f, "codigo": "sin_vigencia", "texto": "Sin fecha reciente comprobable: no representa el estado actual."})

        paid_error = bool(k and ((k.get("cuenta_meta") or {}).get("error") or (k.get("cuenta_meta") or {}).get("errores") or k.get("error") or k.get("errores_lectura")))
        if paid_error:
            gaps.append({"fuente": "captacion", "codigo": "lectura_paid_parcial", "texto": "Hay errores de lectura de la cuenta: sus ceros y comparaciones no sostienen diagnósticos Paid."})
        if k and not paid_error and fuentes["captacion"]["estado"] == "actual":
            periodo7 = (captacion.get("ventanas") or {}).get("7d")
            medicion331 = medir_paid331(k, periodo7, fecha.isoformat())
            leads, gasto = medicion331["leads"], medicion331["gasto"]
            if leads is None:
                raw331 = _numero((k.get("leads") or {}).get("7d"))
                spend331 = _numero((k.get("gasto") or {}).get("7d"))
                if (raw331 is not None and raw331 > 0) or (spend331 is not None and spend331 > 0):
                    recomendar("paid_validar_medicion", "paid", "Comprobar la definición y el periodo de resultados Meta",
                        "Hay referencias en la copia, pero no una medición de eventos lead validada por cuenta, fecha y ventana. No se interpreta como leads, compras ni CPL.",
                        "Trafficker: contrastar el evento configurado y las filas diarias de la cuenta; registrar definición, periodo, moneda y cobertura antes de decidir cambios. En tienda online, confirmar el evento comercial por separado.",
                        "trafficker", "Resultados Meta de referencia; evento y comparabilidad por confirmar.", certeza="medicion_pendiente", periodo=periodo7,
                        entrega="Evento, cuenta y ventana documentados; gasto autorizado y moneda compatibles o explícitamente no disponibles. Sin modificación de campaña.")
            cadena["paid"] = "eventos_meta_observados" if leads is not None or gasto is not None else "sin_dato"
            if leads is None:
                gaps.append({"fuente": "captacion", "codigo": "leads_ausentes", "texto": "Los leads no son un cero medido."})
            if k.get("meta_activa") is True and gasto == 0:
                recomendar("paid_sin_gasto", "paid", "Comprobar campaña activa sin gasto registrado",
                    "La copia registra gasto cero y campaña activa. Sin cobertura completa, ese cero no acredita ausencia de gasto real ni explica la causa.",
                    "Contrastar cobertura y gasto del periodo, entrega, facturación y estado de los anuncios antes de cambiar el presupuesto.",
                    "trafficker", "Gasto en la copia de 7 días: 0; exhaustividad no acreditada.", periodo=periodo7)
            elif leads == 0 and gasto is not None and gasto > 0:
                recomendar("paid_sin_leads", "paid", "Probar captación y medición",
                    "La copia registra gasto y cero leads. La cobertura no está acreditada: no demuestra cero leads reales ni un formulario roto.",
                    "Probar el formulario y la llegada al CRM; contrastar el evento de lead y registrar dónde falla.",
                    "trafficker", "Eventos lead Meta observados en 7 días: 0; hay gasto observado. No acredita contactos únicos ni cualificados.", prioridad=1, periodo=periodo7)
            if k.get("meta_activa") is True:
                previo331 = medir_paid331(k, (captacion.get("ventanas") or {}).get("7d_prev"), fecha.isoformat())
                previo_leads, previo_gasto = previo331["leads"], previo331["gasto"]
                periodos_iguales = _semanas_comparables(captacion, fecha) and medicion331["tipo_evento"] == previo331["tipo_evento"]
                # 4 leads/semana y 25% son umbrales de revisión propuestos por RO,
                # no significación estadística ni objetivo comercial del cliente.
                muestra = leads is not None and previo_leads is not None and leads >= 4 and previo_leads >= 4
                costes = gasto is not None and previo_gasto is not None and gasto > 0 and previo_gasto > 0
                if periodos_iguales and muestra and costes:
                    ahora_cpl, antes_cpl = gasto / leads, previo_gasto / previo_leads
                    variacion = (ahora_cpl / antes_cpl - 1) * 100 if antes_cpl > 0 and isfinite(ahora_cpl) and isfinite(antes_cpl) else None
                    if variacion is not None and isfinite(variacion) and variacion >= 25:
                        recomendar("paid_cpl_tendencia", "paid", "Revisar aumento de coste por lead entre semanas equivalentes",
                            "El coste por evento lead Meta observado aumenta frente a la semana anterior. Es una señal de revisión con muestra operativa, no un juicio de rentabilidad, calidad o objetivo incumplido.",
                            "Trafficker y account: contrastar cambios de campañas, entrega y formulario entre ambas semanas; revisar los leads con el criterio del cliente antes de cambiar presupuesto o atribuir una causa.",
                            "trafficker", f"Dos semanas consecutivas de 7 días, con {int(previo_leads)} y {int(leads)} leads; coste por evento lead Meta observado sube un {variacion:.1f}%.",
                            periodo={"actual": periodo7, "anterior": (captacion.get("ventanas") or {}).get("7d_prev")},
                            entrega="Variación contrastada por campaña y periodo, cambios verificados y siguiente comprobación documentada; sin cambio automático de inversión.")
                elif not periodos_iguales or not muestra:
                    gaps.append({"fuente": "captacion", "codigo": "comparacion_paid_insuficiente", "texto": "Faltan dos semanas consecutivas de 7 días o muestra operativa de 4 leads en cada una; no se calcula tendencia comparable.",
                                 "accion": "Verificar fechas y captación de ambas semanas con el trafficker; esperar muestra antes de interpretar variación."})
                elif not costes:
                    gaps.append({"fuente": "captacion", "codigo": "coste_paid_no_comparable", "texto": "Sin gasto positivo medido y accesible en ambas semanas; no se calcula tendencia de coste.",
                                 "accion": "Contrastar el gasto de ambos periodos con el responsable autorizado, sin tomar datos ausentes como cero."})
                presupuesto = k.get("presupuesto_ads") or {}
                # Las fotos de septiembre no se convierten en aprobación de octubre.
                if not presupuesto or presupuesto.get("confirmado") is not True or presupuesto.get("periodo") != fecha.strftime("%Y-%m"):
                    gaps.append({"fuente": "captacion", "codigo": "presupuesto_mes_no_confirmado", "texto": "No consta presupuesto autorizado para el mes actual en esta fuente; no se proyecta gasto ni desviación.",
                                 "accion": "Account: confirmar periodo y autorización del presupuesto vigente antes de evaluar el ritmo; no cambiar importes."})
                if fecha.day <= 4:
                    gaps.append({"fuente": "captacion", "codigo": "ritmo_mes_temprano", "texto": "Primeros 4 días del mes: la muestra parcial no sostiene una proyección mensual estable.",
                                 "accion": "Revisar semanas equivalentes; posponer la proyección mensual hasta tener presupuesto vigente y días suficientes."})
            anuncios = k.get("anuncios") or {}
            # La generación de Captación no rejuvenece la copia independiente de anuncios.
            fecha_ads = _fecha(captacion.get("anuncios_generado"))
            ads_vigentes = fecha_ads and 0 <= (fecha - fecha_ads).days <= 2
            if anuncios.get("errores") or not ads_vigentes:
                gaps.append({"fuente": "captacion", "codigo": "anuncios_sin_cobertura", "texto": "Datos de anuncios parciales o sin vigencia comprobable; no se diagnostica fatiga."})
            for a in ([] if anuncios.get("errores") or not ads_vigentes else anuncios.get("anuncios", [])) or []:
                freq, caida = _numero(a.get("frecuencia_7d")), _numero(a.get("caida_ctr_pct"))
                if freq is not None and caida is not None and freq > 3 and caida >= 40:
                    recomendar("paid_fatiga_doble", "paid", "Contrastar dos señales de creatividad de la copia",
                        "La copia combina frecuencia superior a 3 y caída de CTR de al menos 40%, umbrales de revisión RO. No acredita ventanas, zona y muestra comparables por anuncio ni confirma desgaste; la frecuencia puede proceder de una ventana distinta a la de clics.",
                        "Trafficker: identificar el anuncio y contrastar ambas ventanas, zona, impresiones y clics. Solo tras verificar las señales, proponer una variante para revisión; no retirar anuncios ni modificar inversión automáticamente.",
                        "trafficker", f"Valores de la copia: frecuencia {freq:g}; caída de CTR {caida:g}%. Comparabilidad pendiente; no diagnóstico de fatiga.",
                        certeza="referencia_pendiente_confirmacion", periodo=None,
                        fecha_evidencia=captacion["anuncios_generado"],
                        entrega="Anuncio identificado por ID; fechas, zona y alcance de ambas ventanas, impresiones/clics y origen de frecuencia contrastados. Registrar si son comparables o qué falta, resultado de la revisión y siguiente comprobación con fecha y responsable. La copia sola no confirma fatiga; propuesta de variante revisable sin publicación ni cambio automático de inversión.")
                    gaps.append({"fuente": "captacion", "codigo": "anuncios_comparacion_no_acreditada",
                                 "texto": "La copia contiene dos señales por contrastar; no acredita que frecuencia y variación de CTR compartan ventanas y zona comparables por anuncio.",
                                 "accion": "Contrastar el anuncio por ID, periodos, zona, alcance y muestra antes de atribuir desgaste o cambiar campañas."})
                    break
            # Techo general/cpl_usado NO es un objetivo acordado para este cliente.
            objetivo = ((goals.get(cid) or {}).get("objetivo") or {}) if fuentes["objetivos"]["estado"] == "actual" and cid not in dg else {}
            # El flag cargado del snapshot Paid no confirma vigencia/autoridad
            # del objetivo y no rescata una fuente antigua, ausente o duplicada.
            if objetivo.get("periodo") and objetivo["periodo"] != fecha.strftime("%Y-%m"):
                objetivo = {}
            for campo, futura in (("vigente_desde", True), ("vigente_hasta", False)):
                if campo in objetivo:
                    d = _fecha(objetivo[campo])
                    if d is None or (d > fecha if futura else d < fecha):
                        objetivo = {}
                        break
            if objetivo.get("confirmado") is False or str(objetivo.get("estado") or "").lower() in ("propuesta", "pendiente", "borrador", "no_confirmado", "rechazado"):
                objetivo = {}
            objetivo_confirmado = objetivo.get("confirmado") is True
            target = _numero(objetivo.get("cpl_objetivo")) if objetivo else None
            cr = k.get("cpl_resumen") or {}
            ref = gasto / leads if gasto is not None and leads is not None and leads >= 4 else None
            if target is not None and target > 0 and ref is not None and objetivo_confirmado and objetivo.get("periodo") == fecha.strftime("%Y-%m") and isinstance(periodo7, (list, tuple)) and all(str(d).startswith(objetivo["periodo"] + "-") for d in periodo7) and ref > target * 1.5:
                recomendar("paid_cpl_objetivo", "paid",
                    "Revisar coste por lead respecto al objetivo acordado" if objetivo_confirmado else "Contrastar coste por lead con la referencia propia registrada",
                    "La muestra marcada fiable supera 1,5 veces el objetivo propio confirmado; no se propone cambiar importes." if objetivo_confirmado else "La muestra supera la referencia propia registrada, cuyo acuerdo vigente no está confirmado en esta fuente.",
                    "Revisar mensaje, captación y calidad de los leads con el account antes de modificar la campaña." if objetivo_confirmado else "Account y trafficker: confirmar la referencia y su vigencia con el cliente antes de evaluar objetivos o modificar la campaña.",
                    "trafficker", "Relación coste por lead/referencia propia superior a 1,5.", periodo=periodo7,
                    certeza="señal" if objetivo_confirmado else "referencia_pendiente_confirmacion")
            elif target is None:
                gaps.append({"fuente": "objetivos", "codigo": "objetivo_no_confirmado", "texto": "No se sustituye el objetivo del cliente por un techo general."})

        if s and fuentes["crm"]["estado"] == "actual":
            if s.get("tipo") not in (None, "cliente"):
                gaps.append({"fuente": "crm", "codigo": "subcuenta_no_cliente", "texto": "Subcuenta interna, de prueba o sin cliente confirmado: no se diagnostica como un cliente comercial."})
            elif s.get("errores_lectura"):
                gaps.append({"fuente": "crm", "codigo": "lectura_parcial", "texto": "Hay errores de lectura; se suspenden diagnósticos CRM para evitar falsos ceros."})
            else:
                cadena["crm"] = "medido"
                if _conteo(s.get("leads_30d")) is not None:
                    cadena["recibidos"] = "conteo_crm_no_cualificacion"
                periodo30 = (crm.get("ventanas") or {}).get("leads")
                v = s.get("velocidad") or {}
                for regla, n, d, titulo, accion in (
                    ("crm_primera_hora", "en_1h", "juzgables", "Contrastar primer contacto y llamada en la primera hora", "Contrastar con el despacho la llamada y su hora para cada lead elegible; los intentos observados también pueden ser mensajes. Registrar lo realizado."),
                    ("crm_cuatro_intentos", "cuatro_en_72h", "juzgables_72h", "Comprobar cuatro intentos en 72 horas", "Contrastar con el despacho los leads con 72 horas cumplidas que no registran cuatro intentos; acordar seguimiento y registrar el resultado.")):
                    par = _par(v, n, d)
                    if par and par[0] < par[1]:
                        recomendar(regla, "crm", titulo,
                            "La lectura parcial registra menos intentos que la referencia operativa. No acredita una cohorte exhaustiva ni llamadas: puede haber mensajes o llamadas externas sin registrar. No es un dictamen de incumplimiento contractual.",
                            accion, "account", f"Casos observados que pasan la referencia: {par[0]} de {par[1]} leads en el registro; cobertura no acreditada.", periodo=periodo30,
                            entrega=("Casos revisados por ID de lead y subcuenta autorizada: creación y primer intento con fecha, zona, canal y evidencia, o datos explícitamente pendientes. Confirmar llamada solo con evidencia específica; un mensaje no la sustituye. Contraste con el despacho y siguiente acción con responsable y fecha; no extrapolar la muestra."
                                     if regla == "crm_primera_hora" else
                                     "Casos con 72 horas acreditadas: intentos observados únicos con fecha, zona y canal en la ventana creación a 72 horas, o ventana/fechas explícitamente pendientes. Separar registros CRM de declaración del despacho, sin completar faltantes ni duplicados y sin afirmar cuatro llamadas. Seguimiento con responsable y fecha."))
                    elif par is None:
                        gaps.append({"fuente": "crm", "codigo": regla + "_sin_cohorte", "texto": "Sin numerador y denominador elegibles consistentes; no se calcula porcentaje."})
                citas = s.get("citas_30d") or {}
                sin_estado = _conteo(citas.get("sin_estado"))
                # Un cero legado no acredita cobertura de calendarios ni eventos.
                if _conteo(citas.get("agendadas")) not in (None, 0) or (sin_estado is not None and sin_estado > 0):
                    cadena["citas"] = "eventos_del_periodo"
                elif sin_estado == 0:
                    gaps.append({"fuente": "crm", "codigo": "citas_cero_sin_cobertura", "texto": "El cero del snapshot no acredita inventario completo de citas ni resultados registrados."})
                if sin_estado is not None and sin_estado > 0:
                    recomendar("crm_citas_sin_estado", "crm", "Completar el resultado de las citas",
                        "Hay citas sin resultado registrado. No se cuentan como ausencias, ventas ni reuniones válidas.",
                        "Pedir al despacho asistencia y resultado comercial de las citas pasadas; enlazar cada cita con su lead y oportunidad por ID y registrar siguiente acción, presupuesto o cierre confirmado sin inferir ventas.",
                        "account", f"Citas sin estado en el periodo de 30 días: {int(sin_estado)}.",
                        prioridad=1 if (_numero(citas.get("sin_estado_max_h")) or 0) > 48 else 2,
                        entrega="Citas pasadas enlazadas por ID a lead/oportunidad, asistencia y resultado comercial confirmados o explícitamente pendientes; siguiente acción con responsable. Citas futuras no se cierran.", periodo=(crm.get("ventanas") or {}).get("citas"))
                wa = s.get("whatsapp") or {}
                fallo = _par(wa, "fallidos", "enviados")
                if fallo and fallo[0] > 0:
                    recomendar("crm_whatsapp_fallidos", "crm", "Revisar mensajes de WhatsApp fallidos",
                        "La fuente registra fallos de envío; no permite asegurar la causa ni el estado del número.",
                        "Comprobar los errores y las secuencias WhatsApp que opera RO antes de reintentar.",
                        "crm", f"Mensajes fallidos registrados: {fallo[0]} de {fallo[1]} envíos.", periodo=periodo30,
                        entrega="Mensajes revisados por ID y subcuenta: estado, error, fecha y secuencia verificados o pendientes. Separar causa comprobada de hipótesis y registrar corrección propuesta. Un reintento solo queda comprobado con nuevo mensaje identificable y su estado posterior; sin reenvío automático ni entrega inferida.")
                email = _par(s.get("correo") or {}, "fallidos", "enviados")
                if email and email[0] > 0:
                    recomendar("crm_correo_fallido", "crm", "Revisar emails fallidos registrados",
                        "Hay correos marcados fallidos en conversaciones. Este conteo no acredita tasa de rebote, apertura ni entrega final.",
                        "Comprobar el estado y error de esos mensajes y la secuencia email de RO; corregir la causa verificada antes de reintentar.",
                        "crm", f"Emails fallidos registrados: {email[0]} de {email[1]} envíos observados.", periodo=periodo30,
                        entrega="Errores de mensajes revisados y causa/acción registradas, sin reenvío automático ni métricas de apertura inferidas.")
                embudo = s.get("embudo") or {}
                paradas = _par(embudo, "estancados_72h", "cohorte_30d")
                if paradas and paradas[0] > 0:
                    recomendar("crm_etapas_paradas", "crm", "Contrastar oportunidades marcadas como paradas",
                        "La fuente señala oportunidades con antigüedad de al menos 72 horas. Su fecha puede ser cambio de etapa, estado o modificación general; sin verificar su origen no acredita ausencia de cambio de etapa ni falta de llamadas.",
                        "Account: contrastar con el despacho cada oportunidad señalada, el origen de su fecha y el estado comercial real; acordar siguiente acción y responsable sin inferir ventas.",
                        "account", f"Oportunidades señaladas en la copia: {paradas[0]} de {paradas[1]} de la cohorte; tipo de fecha pendiente de contrastar.", periodo=periodo30,
                        certeza="referencia_pendiente_confirmacion",
                        entrega="Oportunidades revisadas por ID y subcuenta: etapa/estado actual y tipo y fecha de transición contrastados con evidencia, o antigüedad desconocida. Comprobar duplicados y cambios concurrentes; registrar si la señal se confirma, se descarta o sigue pendiente y siguiente acción con responsable y fecha. Una nota local no prueba una transición; updatedAt no acredita 72 horas de etapa ni un cierre implica venta confirmada.")
                leads30 = _conteo(s.get("leads_30d"))
                paid_activo = s.get("meta_activa") is True or (k and fuentes["captacion"]["estado"] == "actual" and k.get("meta_activa") is True)
                # Umbral de revisión operativo propuesto para evitar tarjetas sin actividad;
                # no es muestra estadística, benchmark de calidad ni condición contractual.
                if s.get("tipo") == "cliente" and paid_activo and leads30 is not None and leads30 >= 3:
                    recomendar("crm_criterio_cualificacion", "crm", "Acordar cómo medir leads cualificados de este cliente",
                        "Hay leads recibidos con Paid activo, pero estas fuentes no contienen criterio versionado ni resultado de cualificación por lead. No implica calidad mala.",
                        "Account y trafficker: acordar con el despacho el criterio de oportunidad cualificada y su versión; revisar una muestra autorizada de leads y registrar por ID cualificación, motivo y siguiente acción, diferenciando recibido, contactable y cualificado.",
                        "account", f"Leads recibidos en el periodo CRM de 30 días: {int(leads30)}; Paid activo. Cualificación no instrumentada en esta fuente.",
                        prioridad=3, periodo=periodo30,
                        entrega="Criterio por cliente aprobado y versionado; muestra revisada por ID con resultado/motivo y responsable. No se altera presupuesto ni se dictamina garantía.")
                gaps.append({"fuente": "crm", "codigo": "conversaciones_cobertura_limitada", "texto": "El lector actual limita conversaciones y mensajes y no certifica su exhaustividad; intentos y mensajes son registros observados, no todas las llamadas del despacho."})

        gaps.extend([
            {"fuente": "crm", "codigo": "cualificacion_no_instrumentada", "texto": "Los leads recibidos no acreditan leads cualificados. Falta criterio verificable y registro de cualificación para evaluar el resultado de RO."},
            {"fuente": "crm", "codigo": "conversion_no_unida", "texto": "Leads, citas y cierres no están unidos por cohorte; no se calcula conversión entre ellos."},
            {"fuente": "crm", "codigo": "huecos_48h_no_medidos", "texto": "No hay evidencia de dos huecos ofrecidos en 48 horas."},
            {"fuente": "crm", "codigo": "garantia_no_evaluable", "texto": "No se verifica validez de reuniones ni condiciones del contrato; no se juzga garantía o devolución."},
        ])
        clientes.append({"cliente_id": cid, "cadena": cadena, "limites": gaps})
    if isinstance(metodo, dict):
        from consejo_metodo_308 import recomendaciones_metodo308
        recomendaciones.extend(recomendaciones_metodo308(metodo, metodo.get('_ids_308') or [], metodo.get('_personas_308') or [], metodo.get('_asignaciones_308') or [], fecha.isoformat()))
    recomendaciones.sort(key=lambda r: (r["prioridad"], r["cliente_id"], r["regla_id"]))
    return {"version": 1, "fecha": fecha.isoformat(), "recomendaciones": recomendaciones,
            "cobertura": {"fuentes": fuentes, "clientes": clientes,
                "metrica_resultado_ro": {"metrica": "leads_cualificados", "estado": "no_instrumentado",
                    "criterio": "No confundir leads recibidos con oportunidades cualificadas; ventas es resultado final separado."},
                "alcance": "Solo filas previamente autorizadas; Meta y registros CRM. Cualificación, cierre y garantía no evaluables."}}
