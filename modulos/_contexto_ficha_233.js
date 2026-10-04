// Una ficha pertenece a una identidad y a un recorte de permisos concretos.
const TIPOS = ['cliente_detalle', 'contactos_cliente', 'chat_cliente', 'inversion', 'cuota', 'cobros', 'horas_cliente', 'responder_cliente'];
export function exigirFichaVigente233(ctx) {
  if (ctx.vigente && !ctx.vigente()) throw new Error('La ficha ha cambiado. Vuelve a abrirla.');
}
export function contextoFicha233(base, raiz, clienteId = null) {
  const firma = () => JSON.stringify({
    real: [base.real?.id, base.real?.puestos, base.real?.estado],
    vista: [base.persona?.id, base.persona?.puestos, base.persona?.estado],
    modo: [base.soloLectura, base.servidor, base.piloto, base.nivel, base.ambito],
    clientes: base.clientes, visibles: base.clientesVisibles,
    modulo: base.veModulo?.('ficha'),
    permisos: clienteId && TIPOS.map(tipo => [tipo, base.ver({ tipo, cliente_id: clienteId })]),
  });
  const inicial = firma();
  const ctx = Object.create(base);
  ctx.vigente = () => {
    try {
      const scope = !clienteId || (base.clientes?.filter(c => c.id === clienteId).length === 1
        && base.clientesVisibles?.filter(c => c.id === clienteId).length === 1
        && !!base.clientes.find(c => c.id === clienteId)?.detalle
        && base.ver({ tipo: 'cliente_detalle', cliente_id: clienteId }).ok);
      const viva = raiz.isConnected && scope && base.veModulo?.('ficha') !== false && (!base.vigente || base.vigente()) && firma() === inicial;
      if (!viva) raiz.replaceChildren();
      return viva;
    } catch { raiz.replaceChildren(); return false; }
  };
  // La revocación también quita la información ya pintada, antes del próximo repintado.
  // Sin temporizador: el guard se evalúa en cada lectura y callback de la ficha.
  const comprobar = () => {
    if (!ctx.vigente()) { raiz.replaceChildren(); exigirFichaVigente233(ctx); }
  };
  for (const nombre of ['api', 'datosModulo', 'verDato', 'accion', 'rastro']) {
    if (typeof base[nombre] !== 'function') continue;
    ctx[nombre] = async (...args) => {
      comprobar();
      const dato = await base[nombre](...args);
      comprobar();
      return dato;
    };
  }
  for (const nombre of ['titulo', 'navegar']) {
    if (typeof base[nombre] !== 'function') continue;
    ctx[nombre] = (...args) => { comprobar(); return base[nombre](...args); };
  }
  return ctx;
}
