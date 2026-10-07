import { createHash } from 'node:crypto';
import { HttpException, Injectable } from '@nestjs/common';
import { CrudoService } from '../permisos/crudo.service.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { moduloVigente, puertaModulo } from '../permisos/puerta-modulo.js';
import { recortarModuloConVista } from '../permisos/recortar-modulo.js';
import { RastroService } from '../rastro/rastro.service.js';
import { estadoClientes, quitarBajas } from './bajas.js';
import { contratosSoloTomas, sanearContratos } from './contratos-privados.js';

/** Python `\w` admite tildes: el mismo conjunto, más el guion de las rutas. */
const REL_OK = /^[\p{L}\p{N}_\-/]+$/u;
const VACIO = 'El fichero de datos está vacío y no hay un dato anterior en el servidor.';

type Fila = Record<string, unknown>;
const esFila = (x: unknown): x is Fila => !!x && typeof x === 'object' && !Array.isArray(x);

export interface LecturaModulo {
  codigo: number;
  cuerpo?: unknown;
  etag?: string;
}

@Injectable()
export class DatosService {
  constructor(
    private readonly crudo: CrudoService,
    private readonly rastro: RastroService,
  ) {}

  /** servir.py › GET /api/modulo/<rel>, sin los enriquecedores que esta noche se quedan por el proxy. */
  async leer(vista: VistaConContexto, rel: string, ifNoneMatch?: string | null): Promise<LecturaModulo> {
    if (!REL_OK.test(rel)) throw new HttpException('No existe esa ruta de la API.', 404);
    const crudo = await this.crudo.actual();
    const sello = await this.crudo.sello();
    const pm = await puertaModulo(vista, rel, crudo, { rastro: this.rastro, apuntar: true, sello });
    if (pm.error) throw new HttpException(pm.error.texto, pm.error.codigo);
    // fichero() antepone APP/data/: la ruta es relativa a data/, como en CrudoService.
    let doc: unknown;
    try {
      doc = await this.crudo.fichero(`${rel}.json`);
    } catch {
      throw new HttpException('El fichero de datos está roto o a medio escribir y no hay un dato anterior: vuelve a probar en un minuto.', 503);
    }
    if (doc === undefined) throw new HttpException(`No existe data/${rel}.json`, 404);
    const aviso = doc === null || (Array.isArray(doc) && doc.length === 0) || (esFila(doc) && Object.keys(doc).length === 0)
      ? { dato_de: null, motivo: VACIO }
      : null;
    if (!(await moduloVigente(vista, rel, crudo, pm, doc))) {
      throw new HttpException('El ámbito o el cliente de estos datos no está autorizado.', 403);
    }
    const conf = pm.conf ?? {};
    const estado = estadoClientes(await this.crudo.fichero('verdad/estado_clientes.json'), sello);
    let salida = quitarBajas(
      recortarModuloConVista(vista, doc, pm.nivel, conf, crudo.clientes ?? []),
      rel,
      estado,
    );
    if (aviso && esFila(salida)) salida = { ...salida, _ultimo_dato_bueno: aviso };
    // contratos_privados.py: la respuesta que no es de Tomás (real y vista) no lleva claves ni enlaces de contrato.
    const vistaPersona = vista.como ?? vista.real;
    if (!contratosSoloTomas(vista.real, vistaPersona)) salida = sanearContratos(salida);
    if (!(await moduloVigente(vista, rel, crudo, pm, doc))) {
      throw new HttpException('El ámbito cambió durante la lectura.', 403);
    }
    const etag = `"${createHash('sha1').update(JSON.stringify(salida)).digest('hex').slice(0, 24)}"`;
    if ((ifNoneMatch ?? '').trim() === etag) return { codigo: 304, etag };
    return { codigo: 200, cuerpo: salida, etag };
  }
}
