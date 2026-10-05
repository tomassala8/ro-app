import unittest
from fuentes_crm.snapshot_v3 import adaptar_snapshot_v3

class SnapshotV3(unittest.TestCase):
    def run_snapshot(self, rows=None, **kwargs):
        conf = dict(cliente_id='cliente-fixture', location_id='location-fixture', version_api='v3',
            observado_en='2026-10-03T10:00:00Z', ahora='2026-10-03T10:01:00Z',
            vigente_desde='2026-10-03T09:00:00Z', ventana_inicio='2026-10-01T00:00:00Z',
            ventana_fin='2026-10-03T00:00:00Z', cobertura_completa=False)
        conf.update(kwargs)
        return adaptar_snapshot_v3(rows if rows is not None else [self.won()], **conf)
    def won(self, **kwargs):
        row = dict(id='opp-fixture', status='won', lastStatusChangeAt='2026-10-02T22:00:00Z')
        row.update(kwargs); return row
    def test_only_last_transition_not_sale(self):
        x = self.run_snapshot(cobertura_completa=True)
        self.assertEqual(x['oportunidades'][0]['ultima_entrada_won_observada'], '2026-10-02T22:00:00+00:00')
        for f in ('fecha_venta', 'fecha_cobro', 'primer_cierre', 'cierres_cohorte', 'ratio_leads_ventas'):
            self.assertIsNone(x[f])
        self.assertFalse(x['cobertura']['historial_completo'])
    def test_no_updated_at_fallback(self):
        x = self.run_snapshot([self.won(lastStatusChangeAt=None, updatedAt='2026-10-02T22:00:00Z')])
        self.assertIsNone(x['oportunidades'][0]['ultima_entrada_won_observada'])
    def test_reopened_not_won(self):
        x = self.run_snapshot([self.won(status='open')])
        self.assertIsNone(x['oportunidades'][0]['ultima_entrada_won_observada'])
    def test_unknown_version(self):
        with self.assertRaises(ValueError): self.run_snapshot(version_api='2023-02-21')
    def test_foreign_scope(self):
        self.assertFalse(self.run_snapshot([self.won(locationId='other')])['oportunidades'])
    def test_future_transition_indeterminate(self):
        self.assertIsNone(self.run_snapshot([self.won(lastStatusChangeAt='2026-10-03T11:00:00Z')])['oportunidades'][0]['ultima_transicion_estado_documentada'])
    def test_naive_date_not_accepted(self):
        self.assertIsNone(self.run_snapshot([self.won(lastStatusChangeAt='2026-10-02T22:00:00')])['oportunidades'][0]['ultima_transicion_estado_documentada'])
        with self.assertRaises(ValueError): self.run_snapshot(ahora='2026-10-03T10:01:00')
    def test_stale_denies_snapshot(self):
        x = self.run_snapshot(observado_en='2026-10-03T08:59:59Z')
        self.assertEqual(x['estado_fuente'], 'desactualizada'); self.assertFalse(x['oportunidades'])
    def test_future_observation(self):
        with self.assertRaises(ValueError): self.run_snapshot(observado_en='2026-10-03T11:00:00Z')
    def test_duplicate_conflict(self):
        x = self.run_snapshot([self.won(), self.won(status='lost')])
        self.assertFalse(x['oportunidades'])
    def test_identical_duplicate_once(self):
        self.assertEqual(len(self.run_snapshot([self.won(), self.won()])['oportunidades']), 1)
    def test_offset_and_exclusive_end(self):
        x = self.run_snapshot([self.won(lastStatusChangeAt='2026-10-03T02:00:00+02:00')])
        self.assertFalse(x['oportunidades'][0]['ultima_transicion_en_ventana'])
    def test_no_private_fields_or_mutation(self):
        import json
        rows = [self.won(contactId='person', name='private', monetaryValue=777, email='private@example.test')]
        before = json.dumps(rows)
        dto = self.run_snapshot(rows)
        self.assertEqual(before, json.dumps(rows))
        raw = json.dumps(dto)
        for word in ('contactId', 'monetaryValue', 'private@example', '777'):
            self.assertNotIn(word, raw)
    def test_malformed_status_rejected(self):
        self.assertFalse(self.run_snapshot([self.won(status=['won'])])['oportunidades'])
    def test_unknown_status_no_auto_won(self):
        self.assertFalse(self.run_snapshot([self.won(status='Closed Won')])['oportunidades'])

if __name__ == '__main__': unittest.main()
