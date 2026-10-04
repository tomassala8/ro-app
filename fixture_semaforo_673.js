function semaforo(valor, { verde, ambar, mejorSi = 'alto' }) {
  if (valor === null || valor === undefined) return 'gris';
  if (mejorSi === 'alto') return valor >= verde ? 'verde' : valor >= ambar ? 'ambar' : 'rojo';
  return valor <= verde ? 'verde' : valor <= ambar ? 'ambar' : 'rojo';
}
