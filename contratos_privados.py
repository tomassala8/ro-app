"""Defensa de salida de contratos: exclusivamente identidad REAL y VISTA tomas.
Sin lecturas de documentos/red. No configura permisos externos de Drive/Sign.
"""
from contextvars import ContextVar
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import json,os,re,unicodedata

_IDENTIDAD=ContextVar('ro_contratos_identidad',default=None)
CLAVES=re.compile(r'^(contratos?|contrato_.+|.+_contratos?|agreements?|documentos?_firmados?|signed_documents?|zoho_sign|contratos_sign|contract(s|_.*)?)$')
TIPOS={'contrato','contrato_firmado','documento_firmado','signed_document','agreement','contract'}
_URL=re.compile(r'https?://[^\s<>"\]\[)]+',re.I)


def permitido(real,vista):
    return isinstance(real,dict) and isinstance(vista,dict) and real.get('id')=='tomas' and vista.get('id')=='tomas'


def _norm(s):
    return re.sub(r'[^a-z0-9]+','_',unicodedata.normalize('NFKD',re.sub(r'([a-z0-9])([A-Z])',r'\1_\2',str(s))).encode('ascii','ignore').decode().lower()).strip('_')


def indice_confirmado(p):
    """Sólo IDs con declaración explícita + procedencia. Ausencia no habilita Sign."""
    try: d=json.loads(Path(p).read_text())
    except (OSError,ValueError):return frozenset()
    out=set()
    if not isinstance(d,dict):return frozenset()
    for r in d.get('documentos') or []:
        if not isinstance(r,dict) or r.get('confirmado') is not True or r.get('tipo')!='contrato_firmado' or not r.get('fuente'):continue
        if r.get('proveedor') not in ('google_drive','zoho_sign'):continue
        id_=r.get('document_id')
        if isinstance(id_,str) and re.fullmatch(r'[A-Za-z0-9_-]{10,200}',id_):out.add(id_)
    return frozenset(out)


def url_contrato(s,ids):
    try:
        u=urlsplit(s);host=(u.hostname or '').lower()
        if host in ('sign.zoho.com','sign.zoho.eu','sign.zoho.in','sign.zoho.com.au','sign.zoho.jp','sign.zoho.ca','sign.zoho.com.cn'):return True
        if host in ('zoho.com','www.zoho.com','zoho.eu','www.zoho.eu') and u.path.startswith('/sign'):return True
        if host in ('docs.google.com','drive.google.com'):
            m=re.search(r'/(?:d|folders)/([A-Za-z0-9_-]+)',u.path)
            doc=(m.group(1) if m else None) or (parse_qs(u.query).get('id') or [None])[0]
            return doc in ids
        return False
    except (ValueError,TypeError):return False


def _registro(o):
    if not isinstance(o,dict):return False
    if any(_norm(o.get(k,'')) in TIPOS for k in ('tipo','type','categoria','clase')):return True
    # Documento etiquetado explícitamente: cuarentena aunque su URL aún no esté indexada.
    return any(_norm(o.get(k,'')).startswith(('contrato_de_prestacion','contrato_firmado','acuerdo_de_colaboracion'))
               or _norm(o.get(k,'')) in ('contrato','contrato_pdf')
               for k in ('nombre','titulo','filename','document_name'))


def sanear(o,ids=frozenset()):
    if isinstance(o,list):return [sanear(v,ids) for v in o if not _registro(v)]
    if isinstance(o,dict):
        if _registro(o):return None
        return {k:sanear(v,ids) for k,v in o.items() if not CLAVES.fullmatch(_norm(k))}
    if isinstance(o,str):
        # Una URL sola queda ausente; en texto se conserva la queja/SOP y se oculta sólo el enlace.
        if _URL.fullmatch(o.strip()) and url_contrato(o.strip(),ids):return None
        return _URL.sub(lambda m:'[Documento reservado]' if url_contrato(m.group(0),ids) else m.group(0),o)
    return o


def ruta_privada(ruta):
    return any(_norm(p) in ('contrato','contratos','contratos_sign','documentos_firmados','contract','contracts','signed_documents') for p in ruta.split('/'))


def enganchar(Manejador,S=None,*,indice=None):
    """Último hook de privacidad, ANTES de piloto. Envuelve DTO y cache JSON."""
    if indice is None:
        indice=os.environ.get('RO_CONTRATOS_INDICE') or Path(__file__).parent/'fuentes_contratos'/'_privado'/'indice_documentos.json'
    get_orig,post_orig=Manejador._api_get,Manejador.api_post
    responder_orig,cache_orig=Manejador.responder,Manejador.responder_guardado
    def ids():return indice_confirmado(indice)
    def es_tomas():
        par=_IDENTIDAD.get()
        return bool(par) and permitido(*par)
    def get(self,ruta,q,real,vista):
        t=_IDENTIDAD.set((real,vista))
        try:
            if ruta_privada(ruta) and not permitido(real,vista):
                return self.responder(403,{'error':'Documento reservado a Tomás.','codigo':'contrato_privado'})
            return get_orig(self,ruta,q,real,vista)
        finally:_IDENTIDAD.reset(t)
    def post(self,ruta,real,vista,cuerpo):
        t=_IDENTIDAD.set((real,vista))
        try:
            if not permitido(real,vista) and (ruta_privada(ruta) or sanear(cuerpo,ids())!=cuerpo):
                return self.responder(403,{'error':'Documento reservado a Tomás.','codigo':'contrato_privado'})
            return post_orig(self,ruta,real,vista,cuerpo)
        finally:_IDENTIDAD.reset(t)
    def responder(self,codigo,obj):
        return responder_orig(self,codigo,obj if es_tomas() else sanear(obj,ids()))
    def cache(self,e):
        if es_tomas():return cache_orig(self,e)
        try:
            o=json.loads(e['cuerpo']);nuevo=sanear(o,ids())
        except (ValueError,KeyError,TypeError):
            return responder_orig(self,503,{'error':'Respuesta temporalmente no disponible.'})
        if nuevo==o:return cache_orig(self,e)
        # Una proyección efímera no pertenece a CACHE_RESP: comprimirla allí
        # exige tam y sumaría bytes sin una entrada que pueda expulsarse.
        # La respuesta normal negocia gzip/br sin contabilidad ni ETag ajenos.
        return responder_orig(self,200,nuevo)
    Manejador._api_get=get;Manejador.api_post=post
    Manejador.responder=responder;Manejador.responder_guardado=cache
