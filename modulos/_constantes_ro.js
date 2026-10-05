// modulos/_constantes_ro.js · L-34: los números de negocio que se repetían en las pantallas viven aquí, una sola vez.
// Es una hoja: no importa nada (así ningún módulo crea un ciclo al importarla). El texto pintado no cambia.

/** Tarifa interna por hora, en euros (D-85, Mili y Coti ven la rentabilidad a esta tarifa; antes escrita a mano en dinero_cliente.js). */
export const TARIFA_HORA_EUR = 31.47;
/** La misma tarifa como texto de pantalla, con coma decimal («31,47»). */
export const TARIFA_HORA_TXT = String(TARIFA_HORA_EUR).replace('.', ',');

/** Horas al mes de referencia para medir la carga (horas.js, Ajustes: «128 h menos ausencias»). Es una referencia histórica, no un objetivo contractual. */
export const HORAS_MES_REFERENCIA = 128;

/** Tope de proyectos por silla: 12 por account, 16 por trafficker y CRM (D-07, D-25; antes en personas.js y mi_dia_bloques.js). Referencia operativa, no capacidad horaria. */
export const TOPE_CARTERA = { account: 12, trafficker: 16, crm: 16 };

/** Salud del cliente: verde desde 60, ámbar de 40 a 59, rojo por debajo de 40 (D-02, provisional; antes en componentes.js). */
export const SALUD = { verde: 60, ambar: 40 };
