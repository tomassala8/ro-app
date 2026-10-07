// Mensaje público de entrada: no revela errores internos ni instrucciones técnicas.
export function falloEntrada562(error) {
  return error?.status === 403
    ? { titulo: 'No tienes acceso', porque: 'Pídeselo a Mili.' }
    : { titulo: 'La app no responde', porque: 'Avisa a Mili para que pueda revisarlo.' };
}
