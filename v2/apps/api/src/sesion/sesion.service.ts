import { createHash } from 'node:crypto';
import { readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Injectable } from '@nestjs/common';
import { compararComoPython, horaMadrid } from '@ro/compat';
import { mirandoComo, recortar, reglas, ver, type Persona } from '@ro/permisos';
import { CrudoService, type CrudoRo } from '../permisos/crudo.service.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { modulosActuales } from '../permisos/recarga.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { RastroService } from '../rastro/rastro.service.js';

const RAIZ = fileURLToPath(new URL('../../../../../', import.meta.url));

/** permisos.py › PERSONA_PUBLICA: lo único de una persona que sale en la sesión. */
const PERSONA_PUBLICA = ['id', 'nombre', 'alias', 'puestos', 'prueba', 'estado', 'activo', 'jefe', 'zona', 'rol', 'pais', 'fecha_ingreso', 'cumple_dia_mes', 'etiquetas'] as const;

/** piloto_lectura.py */
const MODULOS_PILOTO = new Set(['prioridades-cliente', 'mi-trabajo', 'captacion', 'salud-crm', 'reuniones', 'ficha', 'paneles']);
export function pilotoActivo(): boolean {
  return !['', '0', 'no', 'false'].includes((process.env.RO_PILOTO_LECTURA ?? '').trim().toLowerCase());
}

/** servir.py › EXT_LOGO */
const EXT_LOGO: Record<string, string> = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif' };
const RE_LOGO = /^data:(image\/(?:jpeg|png|webp|gif));base64,(.+)$/s;

type Obj = Record<string, unknown>;

function publica(p: Persona): Obj {
  const out: Obj = {};
  for (const k of PERSONA_PUBLICA) out[k] = p[k] ?? null;
  return out;
}

/** str() de Python para el alias del rastro (None si falta). */
const py = (x: unknown) => (x === null || x === undefined ? 'None' : String(x));

@Injectable()
export class SesionService {
  private readonly logos = new Map<string, { uri: string; v: string; ext: string } | null>();
  private pasos?: { marca: number; tabla: Record<string, string[]> };

  constructor(
    private readonly crudo: CrudoService,
    private readonly rastro: RastroService,
    private readonly prisma: PrismaService,
  ) {}

  /** servir.py › _api_get › /api/sesion: lo que cada persona necesita para pintar la app, ya recortado. */
  async sesion(vista: VistaConContexto): Promise<Obj> {
    const crudo = await this.crudo.actual();
    const real = vista.real as Persona;
    const persona = (vista.como ?? vista.real) as Persona;
    const soloLectura = Boolean(vista.como);
    if (vista.como) {
      await this.rastro.registrar(null, {
        quien: real.id,
        coleccion: 'sesion',
        accion: 'ver_como',
        clave: persona.id,
        datos: { detalle: `${py(real.alias)} ve como ${py(persona.alias)} (solo lectura)` },
        como: persona.id,
      });
    }
    const calcular = () => {
      const datos = this.logosADirecciones(recortar(persona, crudo) as unknown as Obj, crudo);
      return { datos, puedeVerComo: ver(real, { tipo: 'ver_como' }, vista.cpReal).ok };
    };
    const r = vista.como ? mirandoComo(real, crudo, calcular) : calcular();
    let datos = r.datos;
    const [sellos, generado] = await this.sellosDeLaTuberia();
    if (sellos.length || generado) {
      datos = { ...datos, meta: { ...(datos.meta as Obj | undefined), sellos, generado_tuberia: generado } };
    }
    const modulos = modulosActuales();
    const almacenes = Object.keys(((reglas() as unknown as Obj).almacenes_privados as Obj) ?? {}).sort(compararComoPython);
    return {
      modulos_puestos: pilotoActivo() ? Object.fromEntries(Object.entries(modulos).filter(([k]) => MODULOS_PILOTO.has(k))) : modulos,
      servidor: true,
      // servir.py › ahora(): hora de pared de Madrid sin zona; RO_RELOJ no la congela.
      hora: horaMadrid(new Date(), ''),
      real: publica(real),
      persona: publica(persona),
      soloLectura: soloLectura || pilotoActivo(),
      pilotoLectura: pilotoActivo(),
      puedeVerComo: r.puedeVerComo,
      datos,
      // Duda 29: la lista la llena el escáner de servir.py al arrancar; Nest no escanea y no la sabe.
      bloqueados: [],
      almacenes_privados: almacenes,
    };
  }

  /** servir.py › logos_a_direcciones: en la sesión, el logo es la dirección del fichero con versión, no el base64. */
  private logosADirecciones(datos: Obj, crudo: CrudoRo): Obj {
    const clientes = ((datos.clientes as Obj[]) ?? []).map((c) => {
      if (!c || typeof c !== 'object' || !c.logo) return c;
      const lg = this.logoDe(String(c.id), crudo);
      return lg ? { ...c, logo: `logos/${String(c.id)}.${lg.ext}?v=${lg.v}` } : c;
    });
    return { ...datos, clientes };
  }

  /** servir.py › logo_de: tipo y huella (sha1 de los bytes, 12) del logo del cliente, si es una imagen de mapa de bits. */
  private logoDe(cid: string, crudo: CrudoRo): { v: string; ext: string } | null {
    const uri = crudo.logos?.[cid];
    const previo = this.logos.get(cid);
    if (previo && previo.uri === uri) return previo;
    const m = RE_LOGO.exec(typeof uri === 'string' ? uri : '');
    if (!m) return null;
    const bytes = Buffer.from(m[2] ?? '', 'base64');
    const r = { uri: uri as string, v: createHash('sha1').update(bytes).digest('hex').slice(0, 12), ext: EXT_LOGO[m[1] ?? ''] ?? '' };
    this.logos.set(cid, r);
    return r;
  }

  /** servir.py › _modulos_de_paso_n12: qué pantallas alimenta cada paso de despliegue/pasos.json. */
  private modulosDePaso(): Record<string, string[]> {
    const fichero = process.env.RO_PASOS_JSON ?? join(RAIZ, 'despliegue', 'pasos.json');
    try {
      const marca = statSync(fichero).mtimeMs;
      if (!this.pasos || this.pasos.marca !== marca) {
        const pasos = (JSON.parse(readFileSync(fichero, 'utf8')) as { pasos?: Obj[] }).pasos ?? [];
        const tabla: Record<string, string[]> = {};
        for (const p of pasos) {
          const ids: string[] = [];
          for (const trozo of String(p.modulo || '').replace(/\([^)]*\)/g, '').split('·')) {
            const palabras = trozo.split(/\s+/).filter(Boolean);
            const w = palabras[0];
            if (w && /^[a-z][a-z0-9-]*$/.test(w) && w !== 'comun') ids.push(w);
          }
          tabla[String(p.id)] = ids;
        }
        this.pasos = { marca, tabla };
      }
    } catch {
      return {};
    }
    return this.pasos?.tabla ?? {};
  }

  /** servir.py › sellos_de_la_tuberia (N-12): solo los pasos que NO van bien y la hora de la última vuelta acabada. */
  private async sellosDeLaTuberia(): Promise<[Obj[], string | null]> {
    try {
      const filas = await this.prisma.db.$queryRaw<{ paso: string; ultimo_bueno: string | null; estado: string | null }[]>`
        SELECT paso, ultimo_bueno, estado FROM sellos ORDER BY paso`;
      const ult = await this.prisma.db.$queryRaw<{ fin: string | null }[]>`
        SELECT fin FROM ejecuciones WHERE fin IS NOT NULL AND estado <> ${'en_curso'} ORDER BY id DESC LIMIT 1`;
      const modulos = this.modulosDePaso();
      const sellos: Obj[] = [];
      for (const { paso, ultimo_bueno, estado } of filas) {
        const ids = modulos[paso] ?? [];
        if (ids.length && estado !== 'bien') sellos.push({ paso, modulo: ids[0], modulos: ids, estado, ultimo_bueno });
      }
      return [sellos, ult[0]?.fin ?? null];
    } catch {
      return [[], null];
    }
  }
}
