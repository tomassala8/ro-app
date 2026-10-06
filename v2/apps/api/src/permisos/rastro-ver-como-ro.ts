import { Injectable } from '@nestjs/common';
import { ModuleRef } from '@nestjs/core';
import { horaMadrid } from '@ro/compat';
import { RastroService } from '../rastro/rastro.service.js';
import { rutaLecturaVerComo585 } from './identidad.guard.js';
import type { RastroVerComo, Vista } from './motor.js';

/** Tope de claves en memoria antes de vaciarla (servir.py › _LECTURAS_VISTAS). */
const TOPE = 5000;

/**
 * servir.py › apuntar_lectura_ver_como: cada lectura en «ver como» deja UNA fila por persona real, persona vista,
 * familia de ruta y minuto (hora de Madrid, como ahora()). La clave se guarda solo después de escribir la fila.
 */
@Injectable()
export class RastroVerComoRo implements RastroVerComo {
  private readonly vistas = new Map<string, Promise<void>>();

  // El rastro se busca al primer uso: así PermisosModule se monta sin base (su prueba lo hace) y, en la app, el
  // RastroService es el de RastroModule. Si no está, get() lanza y la guarda responde 503: sin rastro no hay «ver como».
  constructor(private readonly modulos: ModuleRef) {}

  private get rastro(): RastroService {
    return this.modulos.get(RastroService, { strict: false });
  }

  async apuntar(vista: Vista, _metodo: string, ruta: string): Promise<void> {
    if (!vista.como) return;
    const familia = rutaLecturaVerComo585(ruta);
    const minuto = horaMadrid(new Date(), '').slice(0, 16).replace('T', ' ');
    const clave = `${vista.real.id}|${vista.como.id}|${familia}|${minuto}`;
    const previa = this.vistas.get(clave);
    if (previa) return previa;
    const escribir = this.rastro
      .registrar(null, {
        quien: vista.real.id,
        coleccion: 'ver_como',
        accion: 'lectura',
        clave: familia,
        // «GET» siempre, como servir.py (también en un POST de lectura).
        datos: { metodo: 'GET', evento: 'solicitud', agrupacion: 'familia_minuto' },
        como: vista.como.id,
      })
      .then(() => undefined);
    if (this.vistas.size >= TOPE) this.vistas.clear();
    this.vistas.set(clave, escribir);
    try {
      await escribir;
    } catch (e) {
      this.vistas.delete(clave);
      throw e;
    }
  }
}
