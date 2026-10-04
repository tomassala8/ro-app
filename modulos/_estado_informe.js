// Estado del informe: una acción en la cola nunca demuestra que se haya enviado al cliente.
const vp = a => { try { return typeof a.vista_previa === 'string' ? JSON.parse(a.vista_previa) : a.vista_previa || {}; } catch { return {}; } };
const ultimo = filas => filas.slice().sort((a, b) => Number(b.id || 0) - Number(a.id || 0))[0] || null;
const estadoEnvio = a => {
  const e = typeof a.envio_estado === 'object' ? a.envio_estado?.estado : a.envio_estado;
  return e === 'confirmado' ? 'enviado' : ['simulado', 'simulada'].includes(e) ? 'simulado'
    : ['fallido', 'rebotado'].includes(e) ? 'fallido' : 'pendiente';
};

export function estadoInforme(acc = [], cid, pid) {
  const obj = `informe/${cid}/${pid}`;
  const revisado = ultimo(acc.filter(a => a.tipo === 'marcar' && a.objeto === `${obj}:revisado`));
  const borrador = ultimo(acc.filter(a => a.herramienta === 'app' && a.tipo === 'borrador_informe' && a.objeto === obj));
  const envios = acc.filter(a => a.herramienta === 'desk' && a.tipo === 'correo' && vp(a)?.informe === obj);
  // Un intento posterior fallido no revoca una entrega ya confirmada.
  const enviado = ultimo(envios.filter(a => estadoEnvio(a) === 'enviado'));
  const envio = enviado || ultimo(envios);
  const estado = envio ? estadoEnvio(envio) : null;
  return { revisado, borrador, enviado, envio, estado,
    simulado: estado === 'simulado' ? envio : null,
    pendiente: estado === 'pendiente' ? envio : null,
    fallido: estado === 'fallido' ? envio : null };
}

export function textoEstadoInforme(e) {
  return e.enviado ? 'Envío confirmado en Desk' : e.fallido ? 'Envío fallido · sin entregar'
    : e.simulado ? 'Simulado · no enviado' : e.pendiente ? 'Pendiente de confirmación en Desk'
      : e.borrador ? 'Borrador guardado · sin enviar' : '';
}

// Fecha del proveedor: nunca la de creación de la acción (podría haberse confirmado varios días después).
export function fechaConfirmada(a) {
  return a?.envio_fecha || a?.envio_hora || (typeof a?.envio_estado === 'object' ? a.envio_estado.hora : null) || null;
}

export function filaConEstadoInforme(f, e) {
  if (!e.enviado || ['enviado', 'otra_via', 'exento', 'no_aplica'].includes(f.estado)) return f;
  const fecha = fechaConfirmada(e.enviado);
  const dia = fecha ? String(fecha).slice(0, 10) : null;
  return { ...f, estado: 'enviado', plazo: dia ? (dia <= f.limite ? 'verde' : 'ambar') : 'gris',
    dias_retraso: dia && dia > f.limite ? Math.round((new Date(`${dia}T12:00:00`) - new Date(`${f.limite}T12:00:00`)) / 864e5) : 0,
    enviado: { fecha, metodo: 'Confirmado en Desk desde la app', fecha_pendiente: !fecha } };
}
