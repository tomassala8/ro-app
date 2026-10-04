-- Lo imborrable tampoco se vacía de golpe (4-oct). Los disparadores «sin_delete» son por fila y un TRUNCATE no los
-- dispara: borraría el rastro, las acciones o los mensajes enteros sin ningún aviso. A cada tabla con «<x>_sin_delete»
-- se le añade «<x>_sin_delete_truncate» (BEFORE TRUNCATE, por sentencia) con el mismo mensaje. Lo mismo hace
-- despliegue/base.py › esquema_postgres para las tablas que crea la app de hoy al arrancar.
DO $$
DECLARE
  d record;
  mensaje text;
BEGIN
  FOR d IN
    SELECT t.tgname, c.relname, pg_get_triggerdef(t.oid) AS def
    FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND NOT t.tgisinternal AND t.tgname LIKE '%\_sin\_delete'
  LOOP
    mensaje := replace(substring(d.def FROM 'ro_prohibido\(''(.*)''\)'), '''''', '''');
    IF mensaje IS NULL THEN
      mensaje := 'No se borra';
    END IF;
    EXECUTE format('DROP TRIGGER IF EXISTS %I ON public.%I', d.tgname || '_truncate', d.relname);
    EXECUTE format('CREATE TRIGGER %I BEFORE TRUNCATE ON public.%I FOR EACH STATEMENT EXECUTE FUNCTION public.ro_prohibido(%L)',
                   d.tgname || '_truncate', d.relname, mensaje);
  END LOOP;
END $$;
