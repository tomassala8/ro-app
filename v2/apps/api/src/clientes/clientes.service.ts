import { HttpException, Injectable } from '@nestjs/common';
import { conVista, recortar, type Persona } from '@ro/permisos';
import { CrudoService } from '../permisos/crudo.service.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import {
  administracion581,
  clienteVigente581,
  documentoRaiz581,
  fuentesSoloContrato,
  puertaCliente581,
  type PuertaCliente,
} from '../permisos/puerta-cliente.js';
import { recortarFichaConVista } from '../permisos/recortar-ficha.js';

/**
 * GET /api/cliente/<cid> (servir.py:2780-2820).
 * piloto_lectura.py engancha /api/cliente/ si RO_PILOTO_LECTURA está puesto; sin esa variable no hace nada
 * (piloto_lectura.py:37 y :55). Esta noche no se enciende.
 * DatoSecreto no se reimplementa: la puerta de secretos corre en la tubería y en PuertaSecretosGuard (duda 29).
 */

type Fila = Record<string, unknown>;
const esFila = (x: unknown): x is Fila => !!x && typeof x === 'object' && !Array.isArray(x);

const VACIO = 'El fichero de datos está vacío y no hay un dato anterior en el servidor.';
const ROTO = 'La ficha de este cliente está a medio escribir: vuelve a probar en un minuto.';

function personaDe(p: { id: string; nombre?: unknown; puestos?: string[] }): Persona {
  return { ...(p as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: p.puestos ?? [] };
}

/** Verdad de Python (`if doc`): None, False, 0, "" , [] y {} no. Un objeto con claves sí. */
function hayDoc(doc: unknown): boolean {
  if (doc == null || doc === false || doc === 0 || doc === '') return false;
  if (Array.isArray(doc)) return doc.length > 0;
  if (typeof doc === 'object') return Object.keys(doc).length > 0;
  return true;
}

@Injectable()
export class ClientesService {
  constructor(private readonly crudoSvc: CrudoService) {}

  async ficha(vista: VistaConContexto, cid: string): Promise<Fila> {
    const real = personaDe(vista.real);
    const aplicar = () => this.armar(vista, cid);
    if (vista.como && vista.cpReal) return conVista({ real, cp: vista.cpReal }, aplicar);
    return aplicar();
  }

  private async armar(vista: VistaConContexto, cid: string): Promise<Fila> {
    const crudo = await this.crudoSvc.actual();
    const firma = await this.crudoSvc.sello();
    const puerta = puertaCliente581(vista, crudo, cid, firma);
    if (!puerta) throw new HttpException('El cliente o el ámbito actual de Ficha no está autorizado.', 403);
    const persona = personaDe(vista.como ?? vista.real);
    const resumen = recortar(persona, crudo).clientes.find((c) => c.id === cid) ?? null;
    if (!resumen) throw new HttpException('El cliente no está disponible en este ámbito.', 403);
    const admin = administracion581(puerta.ambito.ps);
    if (puerta.nivel === 'resumen' && !admin) {
      if (!clienteVigente581(vista, crudo, puerta, await this.crudoSvc.sello())) {
        throw new HttpException('El ámbito cambió durante la lectura.', 403);
      }
      return { cliente: resumen, fuentes: null, nivel: 'resumen' };
    }
    const previo: PuertaCliente = { ...puerta, conFichero: true, marca: firma };
    const { doc, aviso } = await this.leerFicha(cid);
    if (
      !clienteVigente581(vista, crudo, previo, await this.crudoSvc.sello()) ||
      !documentoRaiz581(doc, `clientes/${cid}`, crudo, puerta.ambito.ps, puerta.ambito.cps, puerta.niveles)
    ) {
      throw new HttpException('El ámbito o la referencia del cliente cambió durante la lectura.', 403);
    }
    const res: Fila = {
      cliente: resumen,
      fuentes: hayDoc(doc) ? recortarFichaConVista(vista, cid, doc) : null,
    };
    // servir.py:2813 — el filtro de la ruta va DESPUÉS de recortar_ficha.
    if (admin && esFila(res.fuentes)) {
      const permitidas = new Set(fuentesSoloContrato());
      const internas = esFila(res.fuentes.fuentes) ? res.fuentes.fuentes : {};
      const filtradas: Fila = {};
      for (const [k, v] of Object.entries(internas)) {
        if (permitidas.has(k)) filtradas[k] = v;
      }
      res.fuentes.fuentes = filtradas;
    }
    if (aviso) res._ultimo_dato_bueno = aviso;
    if (!clienteVigente581(vista, crudo, previo, await this.crudoSvc.sello())) {
      throw new HttpException('El ámbito cambió durante la lectura.', 403);
    }
    return res;
  }

  /** data/clientes/<cid>.json relativo a data/ (fichero() ya antepone APP/data/). Sin fila: null, no 404. */
  private async leerFicha(cid: string): Promise<{ doc: unknown; aviso: { dato_de: null; motivo: string } | null }> {
    let doc: unknown;
    try {
      doc = await this.crudoSvc.fichero(`clientes/${cid}.json`);
    } catch {
      return { doc: null, aviso: { dato_de: null, motivo: ROTO } };
    }
    if (doc === undefined) return { doc: null, aviso: null };
    const vacio =
      doc === null || (Array.isArray(doc) && doc.length === 0) || (esFila(doc) && Object.keys(doc).length === 0);
    if (vacio) return { doc, aviso: { dato_de: null, motivo: VACIO } };
    return { doc, aviso: null };
  }
}
