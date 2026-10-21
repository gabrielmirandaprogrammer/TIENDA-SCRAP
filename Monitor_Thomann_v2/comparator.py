def compare(current, previous):

    eventos = []

    actuales = {}
    anteriores = {}

    # ========================
    # INVENTARIO ACTUAL
    # ========================

    for producto in current:

        clave = (
            producto.get("sku")
            or producto.get("id")
            or producto.get("nombre", "")
                .upper()
                .strip()
        )

        actuales[clave] = producto

    # ========================
    # INVENTARIO ANTERIOR
    # ========================

    for producto in previous:

        clave = (
            producto.get("sku")
            or producto.get("id")
            or producto.get("nombre", "")
                .upper()
                .strip()
        )

        anteriores[clave] = producto

    # ========================
    # NUEVOS Y CAMBIOS
    # ========================

    for clave, producto in actuales.items():

        if clave not in anteriores:

            eventos.append({
                "tipo": "nuevo",
                "mensaje":
                    "🟢 NUEVO PRODUCTO\n"
                    + producto["nombre"]
                    + "\n💰 "
                    + str(producto["precio"])
                    + " €\n"
                    + producto["url"]
            })

        else:

            precio_anterior = anteriores[clave]["precio"]
            precio_actual = producto["precio"]

            if precio_anterior != precio_actual:

                eventos.append({
                    "tipo": "precio",
                    "mensaje":
                        "💸 CAMBIO DE PRECIO\n"
                        + producto["nombre"]
                        + "\nAntes: "
                        + str(precio_anterior)
                        + " €\nAhora: "
                        + str(precio_actual)
                        + " €\n"
                        + producto["url"]
                })

    # ========================
    # AGOTADOS
    # ========================

    for clave, producto in anteriores.items():

        if clave not in actuales:

            eventos.append({
                "tipo": "agotado",
                "mensaje":
                    "🔴 AGOTADO\n"
                    + producto["nombre"]
                    + "\nÚltimo precio: "
                    + str(producto["precio"])
                    + " €"
            })

    return eventos