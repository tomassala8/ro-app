-- L-14: cinturón de permisos sobre el rastro. En Docker «ro» es superusuario (POSTGRES_USER) y este REVOKE no se nota:
-- lo frenan los disparadores *_sin_update/_sin_delete/_sin_delete_truncate de 0_base. En la nube la app conecta con un rol
-- sin propiedad (BUENAS_PRACTICAS §3.3) y el REVOKE se aplica a ese rol.
-- Solo si el rol «ro» existe: en otras bases (Supabase) el rol de la app se llama distinto y este paso no debe romper el despliegue.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ro') THEN
    REVOKE UPDATE, DELETE, TRUNCATE ON TABLE registro, historial, registro_huellas FROM ro;
  END IF;
END
$$;
