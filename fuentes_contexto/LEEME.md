# Contexto del cliente (4-oct-2026)

Quién es cada cliente, qué hace, qué quiere, qué le gusta y qué no, y cómo trabajar con él. Para que el account lo
tenga a mano en la Ficha sin buscar en carpetas.

## De dónde sale

Las «fichas de cliente»: un JSON que prepara Claude fuera de la app con lo que hay del cliente. Es **privado** y no
entra nunca en el repositorio. `generar_contexto.py` lo busca en este orden:

1. la variable `RO_CONTEXTO_CLIENTES`;
2. `fuentes_contexto/_privado/contexto_clientes/fichas_clientes.json` (fuera de git);
3. `<RO_CRUDOS>/contexto_clientes/fichas_clientes.json` (los datos a mano de `config.py`).

Si no lo encuentra, avisa y sale con error **sin escribir nada**. Tampoco escribe si salen 0 clientes, si la entrada
está rota o si salen menos de la mitad que la última vez (salvo `--forzar`).

## Qué escribe

`data/contexto/contexto_clientes.json`, una fila por cliente:
`cliente_id, en_una_frase, que_hacen, con_ro, objetivos, lo_que_nos_han_dicho, les_gusta, no_les_gusta,
como_trabajar_con_ellos, situacion_actual, huecos, estado, actualizado`.

Solo pasan los clientes de `data/clientes.json` (por id o por nombre). Registrado en `reglas_permisos.json`
(`contexto/contexto_clientes`): módulo `ficha`, sin Administración. El servidor recorta por cartera: cada uno ve
solo sus clientes.

## Privacidad

- Se quita `quien_esta_detras` entero (personas del despacho) y el nombre del account de RO.
- En las citas, el nombre de quien habla se cambia por su papel («socio», «gerente»…).
- Un solo mapa con las personas de TODAS las fichas: el nombre de una persona puede salir en la ficha de otro cliente.
  Se busca sin importar tildes, mayúsculas ni espacios («José García» = «JOSE  garcia»): nombre completo (también lo
  del paréntesis y cada uno de «A y B»), y nombre de pila o apellido sueltos (≥3 letras, con mayúscula, palabra
  entera). Se cambian por su papel en ese cliente; si es de otro cliente o hay varios papeles, por «[persona]».
- Se dejan a propósito, sueltos: los que forman el nombre del propio cliente («García Abogados»), los que son un sitio
  de `donde`, y los que también son palabra corriente («Rosa», «Paz», «Claro»…) a principio de frase.
- El papel también se limpia (a veces nombra a otra persona).
- Correos y teléfonos, en cualquier texto: «[dato quitado]». Teléfonos con espacios dobles, barras, rayas, paréntesis,
  prefijo (+34, 0034, (+34)) o pegados a letras («tlf600…»). No se tocan años, dinero, fechas ni porcentajes.
- No pasan `nombre`, `carpeta`, `bloque` ni `fuentes`. El `cliente_id` pasa tal cual (es la clave de la app).
- No se puede garantizar: un nombre que no esté en `quien_esta_detras`, un mote, o los casos de arriba. Lo revisa
  quien prepara las fichas.
- La salida se escribe de forma atómica (temporal único, fsync, `os.replace`).

## Cómo se corre

```
python3 fuentes_contexto/generar_contexto.py               # escribe
python3 fuentes_contexto/generar_contexto.py --comprobar   # solo valida
python3 fuentes_contexto/generar_contexto.py --entrada X --salida Y
python3 fuentes_contexto/probar_contexto.py                # pruebas con clientes inventados
```

## Cómo se pinta (pendiente)

En la Ficha, un bloque **«Contexto del cliente»**, solo lectura:
- arriba, `en_una_frase` y «Actualizado el …» (de `actualizado`, fecha en castellano);
- qué hacen y qué tienen con RO; objetivos; lo que nos han dicho (cita, fecha y papel);
- les gusta / no les gusta / cómo trabajar con ellos, en listas cortas;
- situación actual; y los `huecos` en gris, como «Nos falta saber…».
- Si el cliente no tiene fila, el bloque no sale (no un hueco vacío).
