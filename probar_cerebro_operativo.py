"""Fixtures unitarias, nunca se publican como datos de un cliente real."""
import copy
import json
import unittest
from unittest.mock import patch
from cerebro_operativo import generar


HOY = "2026-10-03"


def documentos():
    return (
        {"generado": HOY, "datos_hasta": "2026-10-02", "ventanas": {"7d": ["2026-09-26", "2026-10-02"]},
         "clientes": [{"cliente_id": "fixture", "meta_activa": True, "equipo": {"trafficker": "t", "account": "a", "crm": "c"},
                       "leads": {"7d": None}, "gasto": {"7d": None}, "anuncios": {"anuncios": []}}]},
        {"generado": HOY, "ventanas": {"leads": "Cohorte elegible últimos 30 días", "citas": "Eventos de los últimos 30 días"},
         "subcuentas": [{"cliente_id": "fixture", "errores_lectura": [], "velocidad": {}, "citas_30d": {}, "embudo": {}, "whatsapp": {}}]},
        {"generado": HOY, "clientes": []},
    )


def acreditar_paid331(a):
    # Fixture explícita: series tipadas, nunca metadatos asignados a datos reales.
    import datetime as dt
    k=a['clientes'][0];k['cuenta_meta']={'id':'123','moneda':'EUR'};k['serie']=[]
    for key in ['7d_prev','7d']:
        dates=a.get('ventanas',{}).get(key)
        if not isinstance(dates,list) or len(dates)!=2:continue
        first,last=map(dt.date.fromisoformat,dates)
        for i in range((last-first).days+1):
            d=str(first+dt.timedelta(days=i));lead=(k.get('leads') or {}).get(key);spend=(k.get('gasto') or {}).get(key)
            k['serie'].append({'d':d,'leads_meta':lead if i==0 else 0 if lead is not None else None,'gasto_meta':spend if i==0 else 0 if spend is not None else None,
              'medicion':{'version':'220.1','fuente':'meta_insights','nivel':'account','periodo_valido':True,'desde':d,'hasta':d,'fecha_lectura':HOY+' 01:00','cohorte':'resultados_meta_sin_union_crm_ni_cualificacion_ro','campos_observados':['leads','gasto'],'tipo_lead':'lead','cuenta_id':'123','moneda':'EUR'}})

def reglas(resultado):
    return {r["regla_id"] for r in resultado["recomendaciones"]}


class Motor(unittest.TestCase):
    def test_ausente_no_es_cero_y_sin_fuentes_no_inventa_cliente(self):
        a, c, o = documentos()
        self.assertEqual(reglas(generar(a, c, o, HOY)), set())
        a["clientes"][0]["gasto"]["7d"] = 0
        acreditar_paid331(a)
        self.assertEqual(reglas(generar(a, c, o, HOY)), {"paid_sin_gasto"})
        self.assertEqual(generar(hoy=HOY)["recomendaciones"], [])
        self.assertEqual(generar(hoy=HOY)["cobertura"]["fuentes"]["crm"]["estado"], "ausente")

    def test_denominadores_elegibles_no_porcentajes_precalculados(self):
        a, c, o = documentos()
        v = c["subcuentas"][0]["velocidad"]
        v.update(en_1h=2, juzgables=5, pct_1h=100, cuatro_en_72h=1, juzgables_72h=3)
        r = generar(a, c, o, HOY)
        self.assertEqual(reglas(r), {"crm_primera_hora", "crm_cuatro_intentos"})
        self.assertIn("2 de 5", next(x for x in r["recomendaciones"] if x["regla_id"] == "crm_primera_hora")["evidencias"][0]["texto"])
        v.update(en_1h=10, juzgables=5, cuatro_en_72h=0, juzgables_72h=0)
        self.assertEqual(reglas(generar(a, c, o, HOY)), set())
        v.update(en_1h=None, juzgables=5)
        self.assertEqual(reglas(generar(a, c, o, HOY)), set())

    def test_reciente_generacion_no_rejuvenece_medicion_antigua(self):
        a, c, o = documentos()
        a["clientes"][0].update(leads={"7d": 0}, gasto={"7d": 10})
        c["subcuentas"][0]["velocidad"] = {"en_1h": 0, "juzgables": 10}
        a["datos_hasta"] = "2026-09-10"
        c["generado"] = "2026-09-10"
        r = generar(a, c, o, HOY)
        self.assertEqual(reglas(r), set())
        self.assertEqual(r["cobertura"]["fuentes"]["captacion"]["estado"], "sin_vigencia")

    def test_fatiga_necesita_dos_senales_y_lectura_completa(self):
        a, c, o = documentos()
        a["anuncios_generado"] = HOY
        anuncios = a["clientes"][0]["anuncios"]
        anuncios["anuncios"] = [{"frecuencia_7d": 5, "caida_ctr_pct": None, "cansada": True}]
        self.assertNotIn("paid_fatiga_doble", reglas(generar(a, c, o, HOY)))
        anuncios["anuncios"][0]["caida_ctr_pct"] = 50
        self.assertIn("paid_fatiga_doble", reglas(generar(a, c, o, HOY)))
        anuncios["errores"] = ["fallo"]
        self.assertNotIn("paid_fatiga_doble", reglas(generar(a, c, o, HOY)))

    def test_duplicados_no_suma_ni_elige_fuente_arbitraria(self):
        a, c, o = documentos()
        a["clientes"][0].update(leads={"7d": 0}, gasto={"7d": 10})
        a["clientes"].append(copy.deepcopy(a["clientes"][0]))
        c["subcuentas"][0]["velocidad"] = {"en_1h": 0, "juzgables": 10}
        c["subcuentas"].append(copy.deepcopy(c["subcuentas"][0]))
        r = generar(a, c, o, HOY)
        self.assertEqual(reglas(r), set())
        self.assertEqual(sum(x["codigo"] == "identidad_duplicada" for x in r["cobertura"]["clientes"][0]["limites"]), 2)

    def test_citas_sin_estado_no_ausencias_no_conversion_ni_garantia(self):
        a, c, o = documentos()
        s = c["subcuentas"][0]
        s.update(leads_30d=100, citas_30d={"agendadas": 10, "sin_estado": 8, "celebradas": 0},
                 embudo={"funnel": {"cerrado": 1}})
        r = generar(a, c, o, HOY)
        self.assertEqual(reglas(r), {"crm_citas_sin_estado"})
        self.assertEqual(r["cobertura"]["clientes"][0]["cadena"]["cierre"], "sin_dato")
        self.assertIn("conversion_no_unida", {x["codigo"] for x in r["cobertura"]["clientes"][0]["limites"]})
        self.assertEqual(r["cobertura"]["clientes"][0]["cadena"]["recibidos"], "conteo_crm_no_cualificacion")
        self.assertEqual(r["cobertura"]["clientes"][0]["cadena"]["cualificados"], "no_instrumentado")
        self.assertEqual(r["cobertura"]["metrica_resultado_ro"]["estado"], "no_instrumentado")

    def test_error_parcial_bloquea_crm_y_no_filtra_datos_personales(self):
        a, c, o = documentos()
        s = c["subcuentas"][0]
        s.update(errores_lectura=["ERROR-CON-SECRETO"], nombre="CONTACTO-PRIVADO", velocidad={"en_1h": 0, "juzgables": 10})
        r = generar(a, c, o, HOY)
        self.assertEqual(reglas(r), set())
        self.assertNotIn("ERROR-CON-SECRETO", json.dumps(r))
        self.assertNotIn("CONTACTO-PRIVADO", json.dumps(r))

    def test_objetivo_general_y_viejo_no_es_objetivo_cliente(self):
        a, c, o = documentos()
        k = a["clientes"][0]
        k.update(objetivo={"cargado": False, "cpl_usado": 35}, cpl_resumen={"ref": 100, "fiable": True})
        self.assertNotIn("paid_cpl_objetivo", reglas(generar(a, c, o, HOY)))
        o["clientes"] = [{"cliente_id": "fixture", "objetivo": {"cpl_objetivo": 40}}]
        self.assertNotIn("paid_cpl_objetivo", reglas(generar(a, c, o, HOY)))
        o["generado"] = "2026-08-10"
        self.assertNotIn("paid_cpl_objetivo", reglas(generar(a, c, o, HOY)))

    def test_puro_replay_determinista_sin_io_et_output_contrat(self):
        a, c, o = documentos()
        k = a["clientes"][0]
        k.update(leads={"7d": 0}, gasto={"7d": 10})
        originales = copy.deepcopy((a, c, o))
        with patch("builtins.open", side_effect=AssertionError("IO interdit")):
            r = generar(a, c, o, HOY)
            self.assertEqual(r, generar(a, c, o, HOY))
        self.assertEqual(originales, (a, c, o))
        item = r["recomendaciones"][0]
        self.assertEqual(item["responsable_id"], "t")
        self.assertTrue({"cliente_id", "area", "titulo", "motivo", "accion", "prioridad", "responsable_id", "evidencias", "certeza", "criterio_entrega", "modulo_destino"} <= set(item))
        self.assertTrue({"fuente", "fecha", "periodo", "cobertura", "texto"} <= set(item["evidencias"][0]))

    def test_account_sigue_despacho_llama(self):
        a, c, o = documentos()
        c["subcuentas"][0]["velocidad"] = {"en_1h": 0, "juzgables": 3}
        item = generar(a, c, o, HOY)["recomendaciones"][0]
        self.assertEqual(item["responsable_id"], "a")
        self.assertEqual(item["ejecutor_operativo"], "despacho")
        self.assertEqual(item["responsabilidad"], "Seguimiento y verificación con el despacho")

    def test_subfuente_antigua_no_se_rejuvenece_con_generador(self):
        a, c, o = documentos()
        a["clientes"][0].update(leads={"7d": 0}, gasto={"7d": 10})
        a["captacion_generado"] = "2026-08-01"
        self.assertNotIn("paid_sin_leads", reglas(generar(a, c, o, HOY)))
        a["captacion_generado"] = HOY
        a["anuncios_generado"] = "2026-08-01"
        a["clientes"][0]["anuncios"]["anuncios"] = [{"frecuencia_7d": 5, "caida_ctr_pct": 50}]
        self.assertNotIn("paid_fatiga_doble", reglas(generar(a, c, o, HOY)))

    def test_fuente_ghl_antigua_o_ausente_no_se_oculta_con_generacion(self):
        a, c, o = documentos()
        c["subcuentas"][0]["velocidad"] = {"en_1h": 0, "juzgables": 3}
        c["fuentes"] = {"ghl": {"hora": "2026-08-01", "estado": "bien"}}
        r = generar(a, c, o, HOY)
        self.assertNotIn("crm_primera_hora", reglas(r))
        self.assertEqual(r["cobertura"]["fuentes"]["crm"]["fecha_base"], "lectura_ghl")
        c["fuentes"]["ghl"]["hora"] = None
        self.assertNotIn("crm_primera_hora", reglas(generar(a, c, o, HOY)))
        c["fuentes"]["ghl"].update(hora=HOY, estado="dato_viejo")
        self.assertNotIn("crm_primera_hora", reglas(generar(a, c, o, HOY)))

    def test_citas_tarea_resultado_comercial_enlazado_no_inferido(self):
        a, c, o = documentos()
        c["subcuentas"][0]["citas_30d"] = {"sin_estado": 4, "sin_estado_max_h": 60, "futuras": 2}
        r = generar(a, c, o, HOY)
        cards = [x for x in r["recomendaciones"] if x["regla_id"] == "crm_citas_sin_estado"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["prioridad"], 1)
        self.assertIn("por ID", cards[0]["accion"])
        self.assertIn("resultado comercial", cards[0]["criterio_entrega"])
        self.assertIn("futuras no se cierran", cards[0]["criterio_entrega"])
        self.assertEqual(r["cobertura"]["clientes"][0]["cadena"]["cierre"], "sin_dato")

    def test_cualificacion_es_revision_acotada_no_diagnostico_calidad(self):
        a, c, o = documentos()
        s = c["subcuentas"][0]
        s.update(tipo="cliente", leads_30d=3, meta_activa=True)
        r = generar(a, c, o, HOY)
        card = next(x for x in r["recomendaciones"] if x["regla_id"] == "crm_criterio_cualificacion")
        self.assertEqual(card["prioridad"], 3)
        self.assertIn("No implica calidad mala", card["motivo"])
        self.assertIn("Account y trafficker", card["accion"])
        s["leads_30d"] = 2
        self.assertNotIn("crm_criterio_cualificacion", reglas(generar(a, c, o, HOY)))
        s.update(leads_30d=3, meta_activa=False)
        a["clientes"][0]["meta_activa"] = False
        self.assertNotIn("crm_criterio_cualificacion", reglas(generar(a, c, o, HOY)))
        s.update(meta_activa=True, errores_lectura=["error"])
        self.assertNotIn("crm_criterio_cualificacion", reglas(generar(a, c, o, HOY)))

    def test_correo_fallido_no_inventa_rebote_y_faltantes_no_cero(self):
        a, c, o = documentos()
        s = c["subcuentas"][0]
        s["correo"] = {"fallidos": 1, "enviados": None, "pct_fallo": 100}
        self.assertNotIn("crm_correo_fallido", reglas(generar(a, c, o, HOY)))
        s["correo"]["enviados"] = 5
        card = next(x for x in generar(a, c, o, HOY)["recomendaciones"] if x["regla_id"] == "crm_correo_fallido")
        self.assertIn("no acredita tasa de rebote", card["motivo"])
        self.assertIn("1 de 5", card["evidencias"][0]["texto"])
        s["correo"]["fallidos"] = 0
        self.assertNotIn("crm_correo_fallido", reglas(generar(a, c, o, HOY)))

    def test_subcuenta_prueba_no_tratada_como_cliente(self):
        a, c, o = documentos()
        s = c["subcuentas"][0]
        s.update(tipo="prueba", meta_activa=True, leads_30d=30, velocidad={"en_1h": 0, "juzgables": 10}, citas_30d={"sin_estado": 3})
        r = generar(a, c, o, HOY)
        self.assertFalse(any(x["area"] == "crm" for x in r["recomendaciones"]))
        self.assertIn("subcuenta_no_cliente", {x["codigo"] for x in r["cobertura"]["clientes"][0]["limites"]})

    def test_paid_tendencia_recalcula_periodos_iguales_no_delta_proveedor(self):
        a, c, o = documentos()
        a["ventanas"]["7d_prev"] = ["2026-09-19", "2026-09-25"]
        k = a["clientes"][0]
        k.update(leads={"7d": 5, "7d_prev": 10}, gasto={"7d": 200, "7d_prev": 200}, cpl_resumen={"delta_pct": -90})
        card = next(x for x in (acreditar_paid331(a) or generar(a, c, o, HOY))["recomendaciones"] if x["regla_id"] == "paid_cpl_tendencia")
        self.assertIn("100.0%", card["evidencias"][0]["texto"])
        self.assertIn("no un juicio", card["motivo"])
        self.assertNotIn("200", card["evidencias"][0]["texto"])
        self.assertEqual(card["evidencias"][0]["periodo"]["anterior"], a["ventanas"]["7d_prev"])

    def test_paid_tendencia_no_ventanas_desiguales_solapadas_o_sin_muestra(self):
        a, c, o = documentos()
        k = a["clientes"][0]
        k.update(leads={"7d": 5, "7d_prev": 10}, gasto={"7d": 200, "7d_prev": 200})
        for periodo in (None, ["2026-09-20", "2026-09-25"], ["2026-09-22", "2026-09-28"], ["2026-09-11", "2026-09-17"]):
            a["ventanas"]["7d_prev"] = periodo
            self.assertNotIn("paid_cpl_tendencia", reglas(generar(a, c, o, HOY)))
        a["ventanas"]["7d_prev"] = ["2026-09-19", "2026-09-25"]
        k["leads"]["7d"] = 3
        self.assertNotIn("paid_cpl_tendencia", reglas(generar(a, c, o, HOY)))

    def test_paid_tendencia_importes_recortados_no_infiere_costes(self):
        a, c, o = documentos()
        a["ventanas"]["7d_prev"] = ["2026-09-19", "2026-09-25"]
        k = a["clientes"][0]
        k.update(leads={"7d": 5, "7d_prev": 10}, gasto=None, cpl_resumen={"delta_pct": 100, "fiable": True})
        r = (acreditar_paid331(a) or generar(a, c, o, HOY))
        self.assertNotIn("paid_cpl_tendencia", reglas(r))
        self.assertIn("coste_paid_no_comparable", {x["codigo"] for x in r["cobertura"]["clientes"][0]["limites"]})
        k["gasto"] = {"7d": 200, "7d_prev": 0}
        self.assertNotIn("paid_cpl_tendencia", reglas((acreditar_paid331(a) or generar(a, c, o, HOY))))
        k["gasto"]["7d_prev"] = 5e-324
        self.assertNotIn("paid_cpl_tendencia", reglas((acreditar_paid331(a) or generar(a, c, o, HOY))))

    def test_presupuesto_foto_antigua_y_mes_temprano_no_pace(self):
        a, c, o = documentos()
        a["clientes"][0]["presupuesto_ads"] = {"aprobado": 99999, "origen": "Torre septiembre sin confirmar octubre", "proyeccion": 999999}
        r = generar(a, c, o, HOY)
        limites = r["cobertura"]["clientes"][0]["limites"]
        codigos = {x["codigo"] for x in limites}
        self.assertIn("presupuesto_mes_no_confirmado", codigos)
        self.assertIn("ritmo_mes_temprano", codigos)
        self.assertTrue(next(x for x in limites if x["codigo"] == "presupuesto_mes_no_confirmado")["accion"])
        self.assertNotIn("99999", json.dumps(r))
        self.assertFalse(any("ritmo" in x["regla_id"] for x in r["recomendaciones"]))

    def test_semanas_cerradas_terminan_en_ultimo_dato_no_hoy_ni_historicas(self):
        a, c, o = documentos()
        k = a['clientes'][0]
        k.update(leads={'7d': 5, '7d_prev': 10}, gasto={'7d': 200, '7d_prev': 200})
        for anterior, actual in [(['2026-09-20','2026-09-26'],['2026-09-27','2026-10-03']),
                                  (['2026-08-18','2026-08-24'],['2026-08-25','2026-08-31'])]:
            a['ventanas']={'7d_prev':anterior,'7d':actual}
            self.assertNotIn('paid_cpl_tendencia', reglas((acreditar_paid331(a) or generar(a,c,o,HOY))))
        a['ventanas']={'7d_prev':['2026-09-19','2026-09-25'],'7d':['2026-09-26','2026-10-02']}
        self.assertIn('paid_cpl_tendencia',reglas((acreditar_paid331(a) or generar(a,c,o,HOY))))
        a.pop('datos_hasta')
        self.assertNotIn('paid_cpl_tendencia',reglas((acreditar_paid331(a) or generar(a,c,o,HOY))))

    def test_objetivo_paid_cargado_no_rescata_fuente_vieja_o_duplicada(self):
        a,c,o=documentos()
        k=a['clientes'][0]
        k.update(objetivo={'cargado':True,'cpl_objetivo':40},cpl_resumen={'ref':100,'fiable':True})
        self.assertNotIn('paid_cpl_objetivo',reglas(generar(a,c,None,HOY)))
        o['clientes']=[{'cliente_id':'fixture','objetivo':{'cpl_objetivo':40}}]
        self.assertNotIn('paid_cpl_objetivo',reglas(generar(a,c,o,HOY)))
        o['generado']='2026-08-01'
        self.assertNotIn('paid_cpl_objetivo',reglas(generar(a,c,o,HOY)))
        o['generado']=HOY;o['clientes'].append(copy.deepcopy(o['clientes'][0]))
        self.assertNotIn('paid_cpl_objetivo',reglas(generar(a,c,o,HOY)))
        o['clientes']=o['clientes'][:1]
        for dato in [{'periodo':'2026-09'},{'vigente_desde':'2026-10-10'},{'vigente_hasta':'2026-09-30'},{'vigente_hasta':'mal'}]:
            o['clientes'][0]['objetivo']={'cpl_objetivo':40,**dato}
            self.assertNotIn('paid_cpl_objetivo',reglas(generar(a,c,o,HOY)))

    def test_conteos_fraccionarios_no_se_truncan_gasto_decimal_si_permitido(self):
        a,c,o=documentos();a['ventanas']['7d_prev']=['2026-09-19','2026-09-25']
        k=a['clientes'][0];k.update(leads={'7d':4.5,'7d_prev':10},gasto={'7d':200.25,'7d_prev':100.75})
        c['subcuentas'][0].update(tipo='cliente',meta_activa=True,leads_30d=3.5,citas_30d={'sin_estado':1.5})
        rs=reglas((acreditar_paid331(a) or generar(a,c,o,HOY)))
        self.assertFalse({'paid_cpl_tendencia','crm_criterio_cualificacion','crm_citas_sin_estado'} & rs)
        k['leads']['7d']=4
        self.assertIn('paid_cpl_tendencia',reglas((acreditar_paid331(a) or generar(a,c,o,HOY))))

    def test_errores_cuenta_paid_suspenden_ceros_y_comparaciones_no_se_exponen(self):
        a,c,o=documentos();k=a['clientes'][0]
        k.update(leads={'7d':0},gasto={'7d':10},cuenta_meta={'errores':['SECRETO-PRIVADO']})
        r=generar(a,c,o,HOY)
        self.assertNotIn('paid_sin_leads',reglas(r))
        self.assertNotIn('SECRETO-PRIVADO',json.dumps(r))
        self.assertIn('lectura_paid_parcial',{x['codigo'] for x in r['cobertura']['clientes'][0]['limites']})
        self.assertEqual(r['cobertura']['clientes'][0]['cadena']['paid'],'sin_dato')

    def test_cero_citas_sin_cobertura_no_instrumenta_cadena(self):
        a,c,o=documentos();s=c['subcuentas'][0];s['citas_30d']={'sin_estado':0,'agendadas':0}
        r=generar(a,c,o,HOY)
        self.assertEqual(r['cobertura']['clientes'][0]['cadena']['citas'],'sin_dato')
        self.assertIn('citas_cero_sin_cobertura',{x['codigo'] for x in r['cobertura']['clientes'][0]['limites']})
        s['citas_30d']={'sin_estado':0,'agendadas':1}
        self.assertEqual(generar(a,c,o,HOY)['cobertura']['clientes'][0]['cadena']['citas'],'eventos_del_periodo')

    def test_fechas_invalidas_no_adquieren_actualidad_por_prefijo_o_fallback(self):
        a,c,o=documentos();a['clientes'][0].update(leads={'7d':0},gasto={'7d':10})
        for bad in ['2026-10-03texto','2026-10-03 99:99','2026-10-04']:
            a['captacion_generado']=bad
            self.assertNotIn('paid_sin_leads',reglas(generar(a,c,o,HOY)))
        a['captacion_generado']=HOY;a['datos_hasta']='incorrecta'
        self.assertNotIn('paid_sin_leads',reglas(generar(a,c,o,HOY)))
        c['subcuentas'][0]['velocidad']={'en_1h':0,'juzgables':4,'cuatro_en_72h':0,'juzgables_72h':4}
        c['fuentes']={'ghl':{'hora':'2026-10-03invalida','estado':'bien'}}
        self.assertFalse({'crm_primera_hora','crm_cuatro_intentos'} & reglas(generar(a,c,o,HOY)))

    def test_cobertura_y_primera_hora_no_afirma_llamadas_ni_garantia_70(self):
        a,c,o=documentos();c['subcuentas'][0]['velocidad']={'en_1h':1,'juzgables':4,'cuatro_en_72h':1,'juzgables_72h':4}
        r=generar(a,c,o,HOY)
        for card in r['recomendaciones']:
            self.assertEqual(card['evidencias'][0]['cobertura'],'registros_observados_no_exhaustivos')
            self.assertIn('cobertura no acreditada',card['evidencias'][0]['texto'])
            self.assertNotIn('70',card['motivo'])
        primera=next(x for x in r['recomendaciones'] if x['regla_id']=='crm_primera_hora')
        self.assertIn('mensajes',primera['accion'])
        self.assertEqual(primera['ejecutor_operativo'],'despacho')


if __name__ == "__main__":
    unittest.main()
