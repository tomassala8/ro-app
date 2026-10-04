"""PageSpeed v5: GET opt-in, normalización mínima y caché privada. Sin trabajo al importar."""
import datetime as dt
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import tempfile
import stat
import urllib.error
import urllib.parse
import urllib.request

API = 'https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed'
MAX_BYTES = 12 * 1024 * 1024
AUDITS = {'first-contentful-paint':'fcp_ms', 'largest-contentful-paint':'lcp_ms',
          'total-blocking-time':'tbt_ms', 'cumulative-layout-shift':'cls', 'speed-index':'speed_index_ms'}


def url_publica(valor):
    if not isinstance(valor, str) or len(valor) > 2048 or any(ord(c) < 33 for c in valor):
        raise ValueError('url_invalida')
    p = urllib.parse.urlsplit(valor)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None,443) or p.query or p.fragment:
        raise ValueError('url_invalida')
    host = p.hostname.lower().rstrip('.')
    if ':' in host: raise ValueError('url_invalida')
    if host == 'localhost' or '.' not in host or host.endswith(('.local','.localhost','.internal')):
        raise ValueError('url_privada')
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global: raise ValueError('url_privada')
    except ValueError as e:
        if str(e) == 'url_privada': raise
    return urllib.parse.urlunsplit(('https', host, p.path or '/', '', ''))


def numero(v):
    return v if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v >= 0 else None


def fecha(v):
    if not isinstance(v,str): return None
    try:
        f=dt.datetime.fromisoformat(v.replace('Z','+00:00'))
        return f.astimezone(dt.timezone.utc).isoformat() if f.tzinfo else None
    except ValueError: return None


def normalizar(raw, solicitado, estrategia):
    """Nunca persiste screenshots, HTML, recursos, diagnósticos libres ni respuesta cruda."""
    if not isinstance(raw,dict) or not isinstance(raw.get('lighthouseResult'),dict):
        raise ValueError('respuesta_incompleta')
    lh=raw['lighthouseResult']
    dispositivo=(lh.get('configSettings') or {}).get('formFactor') or (lh.get('configSettings') or {}).get('emulatedFormFactor')
    if dispositivo and dispositivo != estrategia: raise ValueError('estrategia_no_coincide')
    if lh.get('runtimeError'): raise ValueError('analisis_fallido')
    instante=fecha(raw.get('analysisUTCTimestamp')) or fecha(lh.get('fetchTime'))
    if not instante: raise ValueError('fecha_ausente')
    final=url_publica(lh.get('finalUrl') or raw.get('id') or solicitado)
    solicitado=url_publica(solicitado)
    score=numero(lh.get('categories',{}).get('performance',{}).get('score'))
    if score is None or score>1: raise ValueError('puntuacion_ausente')
    audits=lh.get('audits') or {}
    metricas={nombre: numero(audits.get(key,{}).get('numericValue')) for key,nombre in AUDITS.items()}
    # Percentiles CrUX tienen unidades diferentes del laboratorio; se mantienen separados.
    campo=raw.get('loadingExperience') or {}
    origen=raw.get('originLoadingExperience') or {}
    def experiencia(e):
        if not isinstance(e,dict) or not isinstance(e.get('metrics'),dict): return {'estado':'sin_dato','metricas':{}}
        nombres={'LARGEST_CONTENTFUL_PAINT_MS':'lcp_ms','FIRST_CONTENTFUL_PAINT_MS':'fcp_ms',
                 'INTERACTION_TO_NEXT_PAINT':'inp_ms','CUMULATIVE_LAYOUT_SHIFT_SCORE':'cls_centésimas'}
        medidas={alias:numero(e['metrics'].get(k,{}).get('percentile')) for k,alias in nombres.items()}
        return {'estado':'medido' if any(v is not None for v in medidas.values()) else 'sin_dato', 'metricas':medidas,'estadistico':'percentil_75'}
    return {'estado':'medido','fuente':'Google PageSpeed Insights v5','fecha_medicion':instante,
            'estrategia':estrategia,'url_solicitada':solicitado,'url_final':final,
            'redireccion_otro_dominio':urllib.parse.urlsplit(final).hostname.removeprefix('www.') != urllib.parse.urlsplit(solicitado).hostname.removeprefix('www.'),
            'laboratorio':{'performance':round(score*100,1),'metricas':metricas,'version':str(lh.get('lighthouseVersion') or '')[:40]},
            'campo_url':experiencia(campo),'campo_origen':experiencia(origen),
            'cobertura':'Una URL y estrategia; prueba de laboratorio, no todas las páginas ni estado contractual.'}


class Cliente:
    def __init__(self, catalogo, clave=None, abrir=None, timeout=55):
        """Catálogo fijado por servidor: {cliente_id: URL autorizada}; no acepta URL del navegador."""
        self.catalogo={cid:url_publica(u) for cid,u in catalogo.items()}
        self.clave=clave
        self.abrir=abrir or urllib.request.urlopen
        self.timeout=timeout

    def medir(self, cliente_id, estrategia='mobile', ahora=None):
        if cliente_id not in self.catalogo: raise PermissionError('cliente_no_autorizado')
        if estrategia not in ('mobile','desktop'): raise ValueError('estrategia_invalida')
        instante=(ahora or dt.datetime.now(dt.timezone.utc)).isoformat()
        base={'cliente_id':cliente_id,'estrategia':estrategia,'intento':instante,'url_solicitada':self.catalogo[cliente_id]}
        q={'url':self.catalogo[cliente_id],'strategy':estrategia,'category':'performance'}
        if self.clave: q['key']=self.clave
        req=urllib.request.Request(API+'?'+urllib.parse.urlencode(q),headers={'Accept':'application/json'})
        try:
            with self.abrir(req, timeout=self.timeout) as r:
                contenido=r.read(MAX_BYTES+1)
            if len(contenido)>MAX_BYTES: raise ValueError('respuesta_demasiado_grande')
            datos=normalizar(json.loads(contenido),self.catalogo[cliente_id],estrategia)
            return {**base,'ok':True,'medicion':datos}
        except urllib.error.HTTPError as e:
            codigo='sin_autorizacion' if e.code in (401,403) else 'cuota_o_limite' if e.code==429 else 'proveedor_error'
            return {**base,'ok':False,'error':codigo,'http':e.code}
        except (urllib.error.URLError,TimeoutError,OSError):
            return {**base,'ok':False,'error':'red_o_timeout'}
        except (ValueError,TypeError,AttributeError):
            return {**base,'ok':False,'error':'respuesta_no_utilizable'}


def guardar_cache(carpeta, resultado):
    """Fallo conserva medición anterior y su fecha. Carpeta exclusiva privada; no datos públicos."""
    carpeta=Path(carpeta)
    if carpeta.is_symlink(): raise ValueError('cache_insegura')
    if not carpeta.exists(): carpeta.mkdir(mode=0o700,parents=True)
    # No modificar permisos de directorios ajenos existentes: rechazar si no es privado.
    if carpeta.stat().st_mode & 0o077: raise ValueError('cache_no_privada')
    key=hashlib.sha256((resultado['cliente_id']+'\0'+resultado['estrategia']).encode()).hexdigest()
    destino=carpeta/(key+'.json')
    if destino.is_symlink(): raise ValueError('cache_insegura')
    anterior={}
    if destino.exists():
        fd=os.open(destino,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_mode & 0o077: raise ValueError('cache_insegura')
            with os.fdopen(fd,'rb',closefd=False) as f: contenido=f.read(128*1024+1)
            if len(contenido)>128*1024:raise ValueError('cache_demasiado_grande')
            anterior=json.loads(contenido)
        finally:os.close(fd)
    salida={'cliente_id':resultado['cliente_id'],'estrategia':resultado['estrategia'],
            'url_solicitada':resultado.get('url_solicitada'),
            'ultimo_intento':resultado['intento'],'ultimo_intento_ok':resultado['ok'],
            'error':resultado.get('error'), 'http':resultado.get('http'),
            'medicion':resultado.get('medicion') if resultado['ok'] else (anterior.get('medicion') if anterior.get('url_solicitada') == resultado.get('url_solicitada') else None)}
    fd,nombre=tempfile.mkstemp(dir=carpeta,prefix='.pagespeed-',suffix='.tmp')
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as f: json.dump(salida,f,ensure_ascii=False,allow_nan=False); f.flush();os.fsync(f.fileno())
        os.replace(nombre,destino)
    finally:
        if os.path.exists(nombre):os.unlink(nombre)
    return salida
