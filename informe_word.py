"""DOCX local puro: DTO autorizado, sin lector de fuentes, rutas, red ni persistencia."""
from collections import Counter
from datetime import date, datetime
from io import BytesIO
import re
import struct
import zipfile
import zlib
from xml.sax.saxutils import escape

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PRIVADO=re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+|(?:\+34\s*)?[6789](?:[\s.-]?\d){8}|\b(?:token|secret|password|authorization)\s*[:=]',re.I)


def texto(v, limite=1200):
    if not isinstance(v,str) or len(v)>limite or PRIVADO.search(v) or any(ord(c)<32 and c not in '\n\t' for c in v):
        raise ValueError('Contenido de informe no apto para exportación.')
    return v


def dia(v):
    if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?',v):return None
    try:
        if 'T' in v:datetime.fromisoformat(v.replace('Z','+00:00'))
        return date.fromisoformat(v[:10]).isoformat()
    except ValueError:return None


def evidencia(doc,cid,periodo):
    """Espejo del contrato112: mismo cliente/ventana, ID único y evidencia explícita."""
    nota='No hay evidencia de ejecución disponible para este periodo. Esto no significa que no se haya trabajado.'
    if not isinstance(doc,dict) or doc.get('cliente_id')!=cid or any(doc.get(k)!=periodo[k] for k in ('desde','hasta')) or not isinstance(doc.get('tareas'),list):
        return [],nota
    filas=doc['tareas'];counts=Counter(t.get('id') for t in filas if isinstance(t,dict) and isinstance(t.get('id'),str));out=[]
    for t in filas:
        if not isinstance(t,dict) or not isinstance(t.get('id'),str) or not t['id'] or counts[t['id']]!=1 or t.get('cliente_id')!=cid or t.get('tipo_evidencia') not in ('finalizacion_flujo','ejecucion_documentada'):continue
        fecha=dia(t.get('fecha_ejecucion'))
        if not fecha or not periodo['desde']<=fecha<=periodo['hasta']:continue
        def limpio(v,limite):
            if not isinstance(v,str) or PRIVADO.search(v) or any(ord(c)<32 and c not in '\n\t' for c in v):return ''
            return v[:limite]
        nombre=limpio(t.get('nombre'),300);fuente=limpio(t.get('fuente_evidencia'),300)
        descripcion=limpio(t.get('descripcion_ejecutada'),1200)
        if not nombre or not fuente:continue
        out.append({'nombre':nombre,'fecha':fecha,'fuente':fuente,'descripcion':descripcion,'tipo':t['tipo_evidencia']})
    completa=doc.get('cobertura')=='completa' and len(out)==len(filas)
    nota='Cobertura declarada completa por esta fuente y para este periodo; no acredita aceptación de entregables.' if completa else 'Copia parcial de evidencias. Puede faltar trabajo ejecutado; no acredita aceptación de entregables.'
    return out,nota


def png_valido(data):
    """PNG embebido, sin SVG activo/URLs; tamaño y expansión limitados."""
    if not isinstance(data,bytes) or len(data)>4*1024*1024 or not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('El logo real requiere PNG válido.')
    pos=8;idat=[];ancho=alto=None;fin=False
    while pos<len(data):
        if pos+12>len(data):raise ValueError('PNG incompleto.')
        n=struct.unpack('>I',data[pos:pos+4])[0];tipo=data[pos+4:pos+8];chunk=data[pos+8:pos+8+n]
        if pos+n+12>len(data) or zlib.crc32(tipo+chunk)&0xffffffff!=struct.unpack('>I',data[pos+8+n:pos+12+n])[0]:raise ValueError('PNG alterado.')
        if ancho is None:
            if tipo!=b'IHDR' or n!=13:raise ValueError('PNG sin cabecera.')
            ancho,alto,depth,color,comp,filt,inter=struct.unpack('>IIBBBBB',chunk)
            if not 0<ancho<=2048 or not 0<alto<=2048 or depth!=8 or color not in (0,2,4,6) or comp or filt or inter:raise ValueError('PNG fuera de formato admitido.')
        elif tipo==b'IHDR':raise ValueError('PNG ambiguo.')
        if tipo==b'IDAT':idat.append(chunk)
        if tipo==b'IEND':
            if n or pos+n+12!=len(data):raise ValueError('PNG con contenido adicional.')
            fin=True;break
        # No metadatos privados ni chunks auxiliares copiados al documento.
        elif tipo not in (b'IHDR',b'IDAT'):raise ValueError('Usa PNG sin metadatos adicionales.')
        pos+=n+12
    if not fin or not idat:raise ValueError('PNG incompleto.')
    canales={0:1,2:3,4:2,6:4}[color];esperado=alto*(1+ancho*canales)
    d=zlib.decompressobj();pixels=d.decompress(b''.join(idat),esperado+1)
    if len(pixels)!=esperado or not d.eof or d.unused_data or d.unconsumed_tail:raise ValueError('PNG comprimido inválido.')
    if any(pixels[i*(1+ancho*canales)]>4 for i in range(alto)):raise ValueError('Filtro PNG inválido.')
    return ancho,alto


def crear_docx(cliente,periodo,informe,evidencias,logo,*,autorizar,vigente):
    """Devuelve bytes. Callbacks obligatorios del servidor, nunca del cuerpo HTTP."""
    def puerta():
        if autorizar() is not True or vigente() is not True:raise PermissionError('Contexto no autorizado o desactualizado.')
    puerta()
    cid=cliente.get('id');nombre=texto(cliente.get('nombre'),200)
    if not isinstance(cid,str) or not re.fullmatch(r'[\w-]+',cid):raise ValueError('Cliente no válido.')
    inicio,fin=dia(periodo.get('desde')),dia(periodo.get('hasta'))
    if inicio!=periodo.get('desde') or fin!=periodo.get('hasta') or not inicio or not fin or inicio>fin or (date.fromisoformat(fin)-date.fromisoformat(inicio)).days>366:raise ValueError('Periodo no válido.')
    if informe.get('cliente_id')!=cid or any(informe.get(k)!=periodo[k] for k in ('desde','hasta')):raise ValueError('Informe de otro cliente o periodo.')
    if any(a.get('color')=='rojo' and a.get('tipo') in ('otro_cliente','datos_leads') for a in informe.get('avisos') or []):raise ValueError('Corrige los avisos de privacidad antes de exportar.')
    if logo.get('cliente_id')!=cid or logo.get('origen')!='logo_cliente':raise ValueError('El informe requiere el logo real del mismo cliente.')
    imagen=logo.get('contenido');ancho,alto=png_valido(imagen)
    apartados=informe.get('apartados') or []
    if not isinstance(apartados,list) or len(apartados)>30:raise ValueError('Apartados no válidos.')
    def par(t,style=None):
        pp=f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ''
        return '<w:p>'+pp+'<w:r><w:t xml:space="preserve">'+escape(t)+'</w:t></w:r></w:p>'
    # Bounding box preserves aspect ratio; no hyperlinks or external relationships.
    cx=min(1800000,int(650000*ancho/alto));cy=int(cx*alto/ancho)
    dibujo=f'''<w:p><w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="1" name="Logo del cliente"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="Logo"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''
    partes=[dibujo,par('Informe · '+nombre,'Title'),par(inicio+' — '+fin)]
    for a in apartados:
        if not isinstance(a,dict) or set(a)-{'titulo','texto'}:raise ValueError('Apartado no permitido.')
        partes.append(par(texto(a.get('titulo'),200),'Heading1'))
        for linea in texto(a.get('texto'),8000).splitlines():partes.append(par(linea))
    tablas=informe.get('tablas') or []
    if not isinstance(tablas,list) or len(tablas)>10:raise ValueError('Tablas no válidas.')
    for tabla in tablas:
        if not isinstance(tabla,dict) or set(tabla)!={'titulo','columnas','filas'} or tabla['columnas']!=['Indicador','Valor observado'] or not isinstance(tabla['filas'],list) or len(tabla['filas'])>30:raise ValueError('Tabla no permitida.')
        partes.append(par(texto(tabla['titulo'],200),'Heading1'))
        rows=[]
        for n,f in enumerate([tabla['columnas']]+tabla['filas']):
            if not isinstance(f,list) or len(f)!=2:raise ValueError('Fila no válida.')
            label=texto(f[0],300)
            value=texto(f[1],100) if n==0 else f[1]
            if n and (not isinstance(value,str) or not re.fullmatch(r'\d{1,13}(?:\.\d{1,12})?(?:[eE][+-]?\d{1,3})?',value)):raise ValueError('Indicador numérico no válido.')
            cells=''.join('<w:tc><w:tcPr><w:tcW w:w="4500" w:type="dxa"/></w:tcPr>'+par(v)+'</w:tc>' for v in (label,value))
            rows.append('<w:tr>'+cells+'</w:tr>')
        partes.append('<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/></w:tblPr><w:tblGrid><w:gridCol w:w="4500"/><w:gridCol w:w="4500"/></w:tblGrid>'+''.join(rows)+'</w:tbl>')
    filas,nota=evidencia(evidencias,cid,periodo)
    partes.extend([par('Trabajo ejecutado documentado','Heading1'),par(nota)])
    for f in filas:
        partes.extend([par(f['nombre'],'Heading2'),par(f['fecha']+' · '+f['fuente']),par('Finalización de flujo registrada; aceptación no acreditada' if f['tipo']=='finalizacion_flujo' else 'Ejecución documentada')])
        if f['descripcion']:partes.append(par(f['descripcion']))
    document=f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>'+''.join(partes)+'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'
    styles=f'<w:styles xmlns:w="{W}"><w:docDefaults><w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>'+''.join(f'<w:style w:type="paragraph" w:styleId="{n}"><w:name w:val="{n}"/><w:pPr><w:keepNext/>'+ (f'<w:outlineLvl w:val="{l}"/>' if l is not None else '')+f'</w:pPr><w:rPr><w:b/><w:sz w:val="{sz}"/></w:rPr></w:style>' for n,l,sz in [('Title',None,36),('Heading1',0,28),('Heading2',1,24)])+'</w:styles>'
    types='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="png" ContentType="image/png"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'
    rel=lambda rows:'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="{i}" Type="{R}/{t}" Target="{p}"/>' for i,t,p in rows)+'</Relationships>'
    files={'[Content_Types].xml':types,'_rels/.rels':rel([('rDoc','officeDocument','word/document.xml')]),'word/document.xml':document,'word/styles.xml':styles,'word/_rels/document.xml.rels':rel([('rLogo','image','media/logo.png'),('rStyles','styles','styles.xml')]),'word/media/logo.png':imagen}
    b=BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in files.items():z.writestr(name,content if isinstance(content,bytes) else ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+content).encode())
    puerta()
    return b.getvalue()
