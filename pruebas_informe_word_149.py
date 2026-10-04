import copy
from io import BytesIO
from pathlib import Path
import struct
import tempfile
import unittest
from xml.etree import ElementTree as ET
import zipfile
import zlib
import informe_word as I


def png():
    def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\x20\x50\x90\x20\x50\x90'))+chunk(b'IEND',b'')


class Word149(unittest.TestCase):
    def setUp(self):
        self.c={'id':'fixture','nombre':'Cliente ficticio & ejemplo'}
        self.p={'desde':'2026-09-01','hasta':'2026-09-30'}
        self.f={'cliente_id':'fixture',**self.p,'apartados':[{'titulo':'Resumen','texto':'Trabajo documentado <verificado>.'}]}
        self.l={'cliente_id':'fixture','origen':'logo_cliente','contenido':png()}
        self.t={'id':'t1','cliente_id':'fixture','nombre':'Revisión de página','fecha_ejecucion':'2026-09-12','fuente_evidencia':'Registro de prueba','tipo_evidencia':'finalizacion_flujo'}
        self.e={'cliente_id':'fixture',**self.p,'tareas':[self.t],'cobertura':'parcial'}
    def generar(self,**kw):return I.crear_docx(self.c,self.p,self.f,self.e,self.l,autorizar=kw.get('autorizar',lambda:True),vigente=kw.get('vigente',lambda:True))
    def contenido(self,b):
        with zipfile.ZipFile(BytesIO(b)) as z:return ''.join(ET.fromstring(z.read('word/document.xml')).itertext())
    def test_zip_XML_logo_relaciones_y_lectura_word(self):
        b=self.generar()
        with zipfile.ZipFile(BytesIO(b)) as z:
            self.assertIsNone(z.testzip());self.assertEqual(z.read('word/media/logo.png'),png())
            for n in z.namelist():
                if n.endswith(('.xml','.rels')):ET.fromstring(z.read(n))
            self.assertNotIn(b'TargetMode="External"',z.read('word/_rels/document.xml.rels'))
        texto=self.contenido(b)
        self.assertIn('Cliente ficticio & ejemplo',texto);self.assertIn('<verificado>',texto)
        self.assertIn('aceptación no acreditada',texto)
        self.assertNotIn('t1',texto)
    def test_scope_cliente_periodo_y_duplicados(self):
        self.e['tareas'] += [{**self.t,'id':'t2','cliente_id':'ajeno','nombre':'NO AJENO'}, {**self.t,'id':'t3','fecha_ejecucion':'2026-10-01','nombre':'NO OCT'}, {**self.t,'id':'t4','fecha_ejecucion':'2026-02-30','nombre':'NO FECHA'}, {**self.t,'nombre':'NO DUP'}]
        texto=self.contenido(self.generar())
        for marca in ['NO AJENO','NO OCT','NO FECHA','NO DUP','Revisión de página']:self.assertNotIn(marca,texto)
        self.assertIn('Copia parcial',texto)
    def test_descripcion_privada_no_elimina_evidencia_segura(self):
        self.t['descripcion_ejecutada']='lead@example.com'
        contenido=self.contenido(self.generar())
        self.assertIn('Revisión de página',contenido)
        self.assertNotIn('lead@example.com',contenido)
    def test_aviso_y_privacidad_ningun_docx(self):
        for marca in ['lead@example.com','612345678','password=secreto']:
            self.f['apartados'][0]['texto']=marca
            with self.assertRaises(ValueError):self.generar()
        self.f['apartados'][0]['texto']='Seguro'
        self.f['avisos']=[{'color':'rojo','tipo':'otro_cliente'}]
        with self.assertRaises(ValueError):self.generar()
    def test_logo_obligatorio_correcto_y_png_no_payload(self):
        for cambio in [{'cliente_id':'ajeno'},{'origen':'iniciales'},{'contenido':b'HTML'}, {'contenido':png()+b'privado'}]:
            previo=self.l.copy();self.l.update(cambio)
            with self.assertRaises(ValueError):self.generar()
            self.l=previo
    def test_permiso_y_vigencia_revalidados(self):
        with self.assertRaises(PermissionError):self.generar(autorizar=lambda:False)
        llamadas=iter([True,False])
        with self.assertRaises(PermissionError):self.generar(vigente=lambda:next(llamadas))
    def test_binding_informe_y_periodo(self):
        self.f['cliente_id']='ajeno'
        with self.assertRaises(ValueError):self.generar()
        self.f['cliente_id']='fixture';self.p['hasta']='2026-09-31'
        with self.assertRaises(ValueError):self.generar()
    def test_no_mutacion_y_evidencia_ausente_no_cero(self):
        previo=copy.deepcopy([self.c,self.p,self.f,self.e,self.l]);self.generar()
        self.assertEqual(previo,[self.c,self.p,self.f,self.e,self.l])
        self.e['cliente_id']='ajeno'
        self.assertIn('Esto no significa que no se haya trabajado',self.contenido(self.generar()))

if __name__=='__main__':unittest.main()
