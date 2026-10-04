def leer(p):
    try:return json.loads(p.read_text())
    except (OSError,ValueError):return {}
