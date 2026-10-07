import { BadRequestException, Body, Controller, ForbiddenException, Get, HttpCode, HttpException, Post, Query, Req } from '@nestjs/common';
import { cortar, horaMadrid, jsonComoPython, longitud } from '@ro/compat';
import { reglas } from '@ro/permisos';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { moduloConocido, RastroLecturaService, veAlguno } from './rastro-lectura.service.js';
import { RastroService } from './rastro.service.js';
import { VerificarService } from './verificar.service.js';

const RESTO = new Set(['accion', 'modulo', 'objeto', 'clave', 'motivo', 'anula_a']);

function listaReglas(clave: string): string[] {
  const v = (reglas() as unknown as Record<string, unknown>)[clave];
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [];
}

function cuerpoDe(b: unknown): Record<string, unknown> {
  if (!b || typeof b !== 'object' || Array.isArray(b)) return {};
  return b as Record<string, unknown>;
}

/**
 * Las tres rutas del rastro. La declaración lleva el texto de servir.py; aquí no se decide quién entra.
 */
@Controller('rastro')
export class RastroController {
  constructor(
    private readonly verificarSrv: VerificarService,
    private readonly rastro: RastroService,
    private readonly lectura: RastroLecturaService,
    private readonly prisma: PrismaService,
  ) {}

  @Permiso({
    tipo: 'rastro_todo',
    mensaje: 'Solo dirección.',
    sinRecorte: 'no lleva datos de clientes: estado de la cadena',
  })
  @Get('verificar')
  verificar(@Query('desde') desde?: string | string[]) {
    const d = Array.isArray(desde) ? desde[0] : desde;
    if (d !== undefined && d !== 'anotado' && !/^\d+$/.test(d)) {
      throw new BadRequestException('«desde» es un número de fila o «anotado».');
    }
    return this.verificarSrv.verificar(d);
  }

  @Permiso({
    soloIdentidad: 'toda persona activa puede anotar en el rastro, como servir.py › POST /api/rastro',
    sinRecorte: 'la respuesta es ok, id y hora, sin datos de clientes',
  })
  @Post()
  @HttpCode(200)
  async anotar(@Req() req: { vista: VistaConContexto }, @Body() body: unknown) {
    const b = cuerpoDe(body);
    const real = req.vista.real;
    if (!this.rastro.topeNavegador(real.id)) {
      throw new HttpException('Demasiadas anotaciones en un minuto: espera un poco.', 429);
    }
    let accion = cortar(!b.accion ? 'evento' : String(b.accion), 60);
    if (listaReglas('rastro_solo_servidor').includes(accion)) {
      throw new ForbiddenException('Esa acción solo la apunta el servidor.');
    }
    if (!listaReglas('rastro_navegador').includes(accion)) {
      accion = `nav:${cortar(accion.toLowerCase().replace(/[^a-z0-9_]/g, ''), 40)}`;
    }
    const motivoTxt = typeof b.motivo === 'string' ? b.motivo : '';
    if (accion === 'no_aplica' && !motivoTxt.trim()) {
      throw new BadRequestException('«No aplica» necesita un motivo.');
    }
    const col = String(b.modulo || b.coleccion || 'app');
    if (col !== 'app' && (!moduloConocido(col) || !veAlguno(real, [col]))) {
      await this.rastro.registrarAgrupado(real.id, 'rastro', 'denegado', cortar(col, 40), { motivo: 'colección ajena desde el navegador' }, null, null);
      throw new ForbiddenException('Desde el navegador solo se apunta en una pantalla que ves.');
    }
    const claveTxt = String(b.objeto || b.clave || '');
    // El tope mide b.get("datos"), que es null si la clave no viene: json.dumps(None) = "null".
    const medido = jsonComoPython(b.datos === undefined ? null : b.datos, { ensureAscii: false });
    if (claveTxt.includes('_privado') || longitud(medido) > 4000) {
      throw new BadRequestException('Anotación no válida (almacén privado o demasiado larga).');
    }
    if (b.anula_a != null && !/^\d{1,12}$/.test(String(b.anula_a))) {
      throw new BadRequestException('«anula_a» tiene que ser el número de una fila.');
    }
    const anula = b.anula_a ? Number(b.anula_a) : b.anula_a === 0 ? 0 : null;
    const datos = 'datos' in b ? b.datos : Object.fromEntries(Object.entries(b).filter(([k]) => !RESTO.has(k)));
    const motivo = b.motivo == null ? null : String(b.motivo);
    const clave = b.objeto || b.clave ? String(b.objeto || b.clave) : null;
    const id = await this.prisma.db.$transaction(async (tx) => {
      if (anula) {
        const previa = (
          await tx.$queryRaw<{ quien: string; coleccion: string }[]>`
            SELECT quien, coleccion FROM registro WHERE id = ${anula}`
        )[0];
        if (!previa || previa.quien !== real.id || previa.coleccion !== col) {
          throw new ForbiddenException('Solo se anula una fila propia de la misma pantalla.');
        }
      }
      return this.rastro.registrar(tx, {
        quien: real.id,
        coleccion: col,
        accion,
        clave,
        datos,
        motivo,
        anula_a: anula,
      });
    }, { maxWait: 10_000, timeout: 10_000 });
    return { ok: true, id, hora: horaMadrid(new Date(), '') };
  }

  @Permiso({
    soloIdentidad: 'toda persona activa lee su rastro, como servir.py › GET /api/rastro',
    sinRecorte: 'el recorte lo hace fila_visible/recortar_vistas, línea a línea como servir.py:2808-2813',
  })
  @Get()
  async leer(@Req() req: { vista: VistaConContexto }) {
    try {
      return await this.lectura.leer(req.vista);
    } catch (e) {
      if (e instanceof Error && e.message === 'AMBITO') {
        throw new ForbiddenException('El ámbito actual del rastro no está disponible.');
      }
      if (e instanceof Error && e.message === 'CAMBIO') {
        throw new ForbiddenException('El ámbito del rastro cambió durante la lectura.');
      }
      throw e;
    }
  }
}
