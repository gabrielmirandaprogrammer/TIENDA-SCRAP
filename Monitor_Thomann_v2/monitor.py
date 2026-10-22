import argparse
from datetime import date, datetime

from dotenv import load_dotenv

# Carga las credenciales antes de importar módulos que las usan.
load_dotenv(".env")

from scraper import scrape, BUSQUEDAS, alcance_busqueda
from storage import (
    load_json,
    save_json,
    guardar_lote_supabase,
    reconciliar_alcance,
    obtener_existentes_alcance,
    actualizar_precios_lote,
    obtener_tasa_eur_cop,
    calcular_precio_cop,
    cargar_exclusiones,
    guardar_exclusiones,
    obtener_alcances_en_base,
)
from comparator import compare


TAMANO_LOTE = 20
ARCHIVO_PROGRESO = "progreso_inventario.json"


def cargar_datos_locales():
    estado = load_json(
        "estado.json",
        {"ultima_ejecucion_completa": ""},
    )
    productos_anteriores = load_json("productos.json", [])
    historial = load_json("historial.json", [])

    if not isinstance(estado, dict):
        raise ValueError("estado.json debe contener un objeto JSON.")
    if not isinstance(productos_anteriores, list):
        raise ValueError("productos.json debe contener una lista.")
    if not isinstance(historial, list):
        raise ValueError("historial.json debe contener una lista.")
    if any(not isinstance(item, dict) for item in productos_anteriores):
        raise ValueError("productos.json contiene registros inválidos.")

    return estado, productos_anteriores, historial


def mostrar_diagnostico(productos):
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO DE DATOS EXTRAÍDOS")
    print("=" * 60)

    por_alcance = {}
    for producto in productos:
        alcance = producto.get("alcance_scraping", "")
        por_alcance[alcance] = por_alcance.get(alcance, 0) + 1

    for alcance, cantidad in sorted(por_alcance.items()):
        print(f"{alcance}: {cantidad} productos")

    for producto in productos[:3]:
        print()
        print(f"Nombre: {producto.get('nombre', '')}")
        print(f"SKU: {producto.get('sku', '')}")
        print(f"Marca: {producto.get('marca', '')}")
        print(f"Categoría: {producto.get('categoria', '')}")
        print("Etiqueta H2:", producto.get("categoria_etiqueta", ""))
        print("Alcance:", producto.get("alcance_scraping", ""))
        print(
            "Precio de origen:",
            producto.get("precio_origen", ""),
            "EUR",
        )
        print(f"URL: {producto.get('url', '')}")
        print(f"Imagen: {producto.get('imagen', '')}")
        print("Cantidad de imágenes:", len(producto.get("gallery", [])))

        detalles = producto.get("productDetails", [])
        print(f"Cantidad de detalles: {len(detalles)}")
        for detalle in detalles:
            print(f"  - {detalle}")

    print("=" * 60 + "\n")


def preparar_eventos(actual, anteriores):
    if not anteriores:
        return []

    eventos = compare(actual, anteriores)

    if not isinstance(eventos, list):
        raise ValueError("compare() debe devolver una lista de eventos.")

    for evento in eventos:
        if not isinstance(evento, dict):
            raise ValueError("La comparación devolvió un evento inválido.")
        if not isinstance(evento.get("mensaje"), str):
            raise ValueError("La comparación devolvió un mensaje inválido.")
        if not evento["mensaje"].strip():
            raise ValueError("La comparación devolvió un mensaje vacío.")
        if "tipo" not in evento:
            raise ValueError("La comparación devolvió un evento sin tipo.")

    return eventos


def obtener_sku(producto):
    sku_original = producto.get("sku")
    if sku_original is None or isinstance(sku_original, bool):
        raise ValueError("Se encontró un producto sin SKU válido.")

    sku = str(sku_original).strip()
    if not sku or not sku.isdigit():
        raise ValueError(f"SKU inválido: {sku!r}")

    return sku


def agrupar_por_alcance(productos):
    grupos = {}
    vistos = set()

    for producto in productos:
        if not isinstance(producto, dict):
            raise ValueError("El scraper devolvió un producto inválido.")

        alcance = producto.get("alcance_scraping")
        if not isinstance(alcance, str) or not alcance.strip():
            raise ValueError(
                "Un producto no tiene un alcance_scraping válido."
            )

        alcance = alcance.strip()
        sku = obtener_sku(producto)

        if sku in vistos:
            raise ValueError(f"SKU repetido entre búsquedas: {sku}")
        vistos.add(sku)

        grupos.setdefault(alcance, []).append(producto)

    if not grupos:
        raise ValueError("No se encontraron productos para procesar.")

    return grupos


def cargar_progreso():
    progreso = load_json(
        ARCHIVO_PROGRESO,
        {"skus_guardados_por_alcance": {}},
    )

    if not isinstance(progreso, dict):
        raise ValueError(
            f"{ARCHIVO_PROGRESO} debe contener un objeto JSON."
        )

    guardados = progreso.get("skus_guardados_por_alcance", {})
    if not isinstance(guardados, dict):
        raise ValueError(
            "El campo skus_guardados_por_alcance debe ser un objeto."
        )

    normalizado = {}
    for alcance, skus in guardados.items():
        if not isinstance(alcance, str) or not isinstance(skus, list):
            raise ValueError(f"Progreso inválido para el alcance {alcance!r}.")

        normalizado[alcance] = {str(sku) for sku in skus}

    return normalizado


def guardar_progreso(progreso):
    save_json(
        ARCHIVO_PROGRESO,
        {
            "skus_guardados_por_alcance": {
                alcance: sorted(skus)
                for alcance, skus in progreso.items()
            }
        },
    )


def procesar_lote_recibido(
    lote,
    alcance,
    progreso,
    solo_validar,
    estadisticas,
):
    """
    Procesa un lote tal como lo entrega el scraper, durante el recorrido.

    En modo normal, cada lote se escribe en Supabase y solo después de
    que la escritura termina bien se marca su progreso en disco.
    """
    if not isinstance(lote, list) or not lote:
        raise ValueError("El scraper entregó un lote vacío o inválido.")
    if not isinstance(alcance, str) or not alcance.strip():
        raise ValueError("El scraper entregó un lote sin alcance válido.")

    for producto in lote:
        if not isinstance(producto, dict):
            raise ValueError("El scraper entregó un producto inválido.")
        if producto.get("alcance_scraping") != alcance:
            raise ValueError(
                "Un producto del lote no coincide con el alcance entregado: "
                f"{producto.get('alcance_scraping')!r} != {alcance!r}"
            )
        obtener_sku(producto)

    ya_guardados = progreso.get(alcance, set())
    pendientes = [
        producto
        for producto in lote
        if obtener_sku(producto) not in ya_guardados
    ]

    if not pendientes:
        print(
            f"LOTE OMITIDO | {alcance} | "
            f"los {len(lote)} SKU ya estaban guardados."
        )
        return

    print(
        f"LOTE RECIBIDO | {alcance} | {len(lote)} productos | "
        f"{len(pendientes)} pendientes por guardar."
    )

    # Defensa: si el scraper entregara más de TAMANO_LOTE, se subdivide.
    for inicio in range(0, len(pendientes), TAMANO_LOTE):
        lote_guardar = pendientes[inicio:inicio + TAMANO_LOTE]
        numero_lote = estadisticas["lotes"] + 1

        if solo_validar:
            resultado = guardar_lote_supabase(
                lote_guardar,
                alcance=alcance,
                solo_validar=True,
            )
            print(
                f"VALIDACIÓN {numero_lote} OK | "
                f"{alcance} | {len(lote_guardar)} SKU | respuesta: {resultado}"
            )
            estadisticas["validados"] += len(lote_guardar)
            estadisticas["lotes"] += 1
            continue

        print(
            f"Guardando lote {numero_lote} de {alcance}: "
            f"{len(lote_guardar)} SKU."
        )

        resultado = guardar_lote_supabase(
            lote_guardar,
            alcance=alcance,
        )
        print(
            f"LOTE {numero_lote} GUARDADO EN SUPABASE | {alcance} | "
            f"{len(lote_guardar)} SKU | respuesta: {resultado}"
        )

        # El progreso se marca solo después del éxito de la escritura,
        # y se persiste de inmediato para poder reanudar si algo falla.
        progreso.setdefault(alcance, set()).update(
            obtener_sku(producto) for producto in lote_guardar
        )
        guardar_progreso(progreso)

        estadisticas["guardados"] += len(lote_guardar)
        estadisticas["lotes"] += 1


def crear_callback_lotes(progreso, solo_validar=False):
    """
    Devuelve el callback on_batch(lote, alcance) que el scraper llamará
    cada vez que complete un lote de hasta TAMANO_LOTE productos válidos.
    """
    estadisticas = {"guardados": 0, "validados": 0, "lotes": 0}

    def on_batch(lote, alcance):
        procesar_lote_recibido(
            lote,
            alcance,
            progreso,
            solo_validar,
            estadisticas,
        )

    on_batch.estadisticas = estadisticas
    return on_batch


def verificar_progreso_completo(grupos, progreso):
    pendientes = []

    for alcance, productos_alcance in grupos.items():
        guardados = progreso.get(alcance, set())

        for producto in productos_alcance:
            sku = obtener_sku(producto)
            if sku not in guardados:
                pendientes.append((alcance, sku))

    if pendientes:
        muestra = ", ".join(
            f"{alcance}:SKU {sku}"
            for alcance, sku in pendientes[:10]
        )
        raise RuntimeError(
            "Aún hay SKU pendientes; no se cerrará el inventario. "
            f"Ejemplos: {muestra}"
        )


def finalizar_inventario(actual, estado, anteriores, historial):
    eventos = preparar_eventos(actual, anteriores)
    historial_nuevo = list(historial)

    if not anteriores:
        print("Primer inventario: sin alertas de comparación.")
    else:
        print(f"Cambios detectados: {len(eventos)}")

    for evento in eventos:
        print(f"\nCAMBIO [{evento['tipo']}]\n{evento['mensaje']}")
        historial_nuevo.append({
            "fecha": datetime.now().isoformat(),
            "tipo": evento["tipo"],
            "mensaje": evento["mensaje"],
        })

    estado_nuevo = dict(estado)
    estado_nuevo["ultima_ejecucion_completa"] = date.today().isoformat()

    # Se guardan los archivos locales solamente después de completar
    # el guardado de todos los lotes. Este bloque ya no depende de ningún
    # envío externo: antes, un fallo de Telegram dejaba estos JSON sin
    # actualizar aunque Supabase estuviera al día.
    save_json("productos.json", actual)
    save_json("historial.json", historial_nuevo)
    save_json("estado.json", estado_nuevo)

    # El progreso deja de ser necesario tras completar el inventario.
    if ARCHIVO_PROGRESO:
        save_json(
            ARCHIVO_PROGRESO,
            {"skus_guardados_por_alcance": {}},
        )

    print("Inventario e historial locales actualizados.")
    print("PROCESO FINALIZADO.")


def advertir_alcances_huerfanos():
    """
    Compara los alcances con productos en la base contra los alcances que
    producen las búsquedas actuales del scraper. Cualquier alcance antiguo
    (por ejemplo, el de una búsqueda cuya fórmula cambió) o vacío aloja
    registros que ninguna reconciliación puede limpiar, porque esta filtra
    por alcance exacto.
    """
    alcances_validos = {
        alcance_busqueda(termino) for termino, _, _ in BUSQUEDAS
    }
    alcances_base = obtener_alcances_en_base()

    huerfanos = {
        alcance if alcance else "(sin alcance)": cantidad
        for alcance, cantidad in sorted(alcances_base.items())
        if alcance not in alcances_validos
    }

    if huerfanos:
        detalle = ", ".join(
            f"{alcance}: {cantidad}"
            for alcance, cantidad in huerfanos.items()
        )
        print(
            "\nADVERTENCIA: hay productos en la base con alcances que ya "
            f"no produce ninguna búsqueda actual ({detalle}). La "
            "reconciliación no puede eliminarlos; límpialos a mano en "
            "Supabase (imágenes, historial de precios y productos)."
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Monitor de Thomann con guardado no destructivo en lotes "
            "de hasta 20 productos, reconciliación al cierre de cada "
            "búsqueda y salto de fichas ya guardadas con imágenes."
        )
    )
    parser.add_argument(
        "--solo-validar",
        action="store_true",
        help=(
            "Extrae y valida lotes contra Supabase sin escribir "
            "en la base ni modificar JSON."
        ),
    )
    args = parser.parse_args()

    estado, anteriores, historial = cargar_datos_locales()

    if args.solo_validar:
        # La validación siempre arranca limpia y nunca toca el progreso.
        progreso = {}
    else:
        progreso = cargar_progreso()

        pendientes_previos = sum(len(skus) for skus in progreso.values())
        if pendientes_previos:
            print(
                f"PROGRESO PREVIO: {pendientes_previos} SKU ya confirmados "
                "en Supabase; se reanuda sin duplicarlos."
            )

    # SKUs vigentes por alcance según la página: lo llena finalizar_alcance
    # cada vez que la reconciliación corre con listado completo.
    skus_vigentes = {}
    reconciliacion = {"ejecutadas": 0, "omitidas": 0}

    # Cambios de precio aplicados desde el listado sin abrir la ficha:
    # {sku: precio_origen_en_eur}. Sirven para actualizar también la
    # copia local del inventario.
    cambios_precio = {}

    # Caché de SKU excluidos (skus_excluidos.json): el scraper los omite
    # sin abrir su ficha, en esta y en las siguientes ejecuciones.
    exclusiones = cargar_exclusiones()

    if exclusiones:
        print(
            f"CACHÉ DE EXCLUSIONES: {len(exclusiones)} SKU se omitirán "
            "sin abrir su ficha."
        )

    # ESTAS FUNCIONES VAN DENTRO DE main() porque necesitan
    # args.solo_validar. El scraper las llama durante el recorrido.
    def finalizar_alcance(alcance, skus_en_pagina, skus_agotados, listado_completo):
        if not listado_completo:
            reconciliacion["omitidas"] += 1
            print(
                f"RECONCILIACIÓN OMITIDA ({alcance}): el listado no cargó "
                "completo; no se borra nada para no eliminar productos "
                "válidos por error."
            )
            return

        reconciliacion["ejecutadas"] += 1
        reconciliar_alcance(
            alcance,
            skus_en_pagina,
            skus_agotados,
            solo_validar=args.solo_validar,
        )
        skus_vigentes[alcance] = skus_en_pagina

    def actualizar_precios(actualizaciones, alcance):
        for item in actualizaciones:
            cambios_precio[str(item["sku"])] = item["precio_origen"]

        actualizar_precios_lote(
            actualizaciones,
            alcance,
            solo_validar=args.solo_validar,
        )

    def obtener_exclusiones_actuales():
        return exclusiones

    def registrar_exclusion(sku, datos):
        sku_limpio = str(sku).strip()

        if not sku_limpio.isdigit():
            raise ValueError(f"Exclusión con SKU inválido: {sku!r}")
        if datos.get("razon") not in ("tipo", "retirado"):
            raise ValueError(
                "El scraper reportó una exclusión desconocida: "
                f"{datos.get('razon')!r}"
            )

        registro = dict(datos)
        registro["fecha"] = datetime.now().isoformat()
        exclusiones[sku_limpio] = registro

        # En --solo-validar el caché se consulta pero no se escribe.
        if not args.solo_validar:
            guardar_exclusiones(exclusiones)

    callback = crear_callback_lotes(
        progreso,
        solo_validar=args.solo_validar,
    )

    # El scraper entrega cada lote de hasta 20 productos válidos durante
    # el recorrido; consulta la base para saltarse fichas ya guardadas;
    # actualiza precios desde el listado, omite los SKU del caché de
    # exclusiones y reconcilia al cierre de cada búsqueda.
    actual = scrape(
        on_batch=callback,
        batch_size=TAMANO_LOTE,
        on_fin_alcance=finalizar_alcance,
        on_precios=actualizar_precios,
        obtener_existentes=obtener_existentes_alcance,
        obtener_exclusiones=obtener_exclusiones_actuales,
        on_excluir=registrar_exclusion,
    )

    if not isinstance(actual, list):
        raise ValueError(
            "El scraper devolvió un inventario inválido. No se sincronizará."
        )

    estadisticas = callback.estadisticas
    print(
        f"\nProductos nuevos extraídos: {len(actual)} | "
        f"SKU guardados en esta ejecución: {estadisticas['guardados']} | "
        f"lotes guardados: {estadisticas['lotes']} | "
        f"SKU validados: {estadisticas['validados']} | "
        f"precios actualizados desde el listado: {len(cambios_precio)}"
    )

    if actual:
        mostrar_diagnostico(actual)

    # Aviso temprano de registros bajo alcances que ya no produce ninguna
    # búsqueda: es la causa típica de "productos que siguen en la base pero
    # ya no están en la página". Corre también en --solo-validar.
    advertir_alcances_huerfanos()

    # Con el salto de fichas ya guardadas, una ejecución puede terminar
    # con cero productos nuevos y aun así ser exitosa.
    grupos = agrupar_por_alcance(actual) if actual else {}

    if args.solo_validar:
        print(
            "VALIDACIÓN FINALIZADA. No se escribió en Supabase "
            "ni se modificaron archivos locales."
        )
        return

    try:
        verificar_progreso_completo(grupos, progreso)
    except Exception:
        print(
            "ERROR AL CERRAR EL INVENTARIO: hay SKU de esta extracción "
            "sin confirmar en Supabase. No se actualizarán productos.json, "
            "historial.json ni estado.json. El progreso confirmado se "
            "conserva para reanudar."
        )
        raise

    print("Todos los lotes de esta extracción fueron guardados.")

    # Reconstrucción del inventario completo: scrape() solo devuelve los
    # productos NUEVOS (las fichas ya guardadas se saltan), así que se
    # parte de la copia local anterior, se le suman los nuevos, se le
    # aplican los precios actualizados desde el listado y se le quitan
    # los SKU que la reconciliación eliminó de la base.
    inventario = {obtener_sku(p): p for p in anteriores}
    for producto in actual:
        inventario[obtener_sku(producto)] = producto

    if cambios_precio:
        tasa = obtener_tasa_eur_cop()

        for sku, precio_eur in cambios_precio.items():
            registro = inventario.get(sku)
            if registro:
                registro["precio_origen"] = precio_eur
                registro["precio"] = calcular_precio_cop(precio_eur, tasa)

    # Solo se descartan registros locales de alcances donde la
    # reconciliación corrió con listado completo; los demás se conservan.
    for alcance, vigentes in skus_vigentes.items():
        inventario = {
            sku: p
            for sku, p in inventario.items()
            if p.get("alcance_scraping") != alcance or sku in vigentes
        }

    completos = list(inventario.values())
    print(
        f"Inventario completo reconstruido: {len(completos)} productos | "
        f"nuevos={len(actual)} | "
        f"precios actualizados={len(cambios_precio)} | "
        f"reconciliaciones ejecutadas={reconciliacion['ejecutadas']} | "
        f"omitidas={reconciliacion['omitidas']}"
    )

    finalizar_inventario(completos, estado, anteriores, historial)


if __name__ == "__main__":
    main()