import argparse
from datetime import date, datetime

from dotenv import load_dotenv

# Carga las credenciales antes de importar módulos que las usan.
load_dotenv(".env")

from scraper import scrape
from storage import (
    load_json,
    save_json,
    guardar_lote_supabase,
)
from comparator import compare
from telegram_bot import send


TAMANO_LOTE = 40
ARCHIVO_PROGRESO = "progreso_inventario.json"


def enviar_texto_largo(texto, limite=3500):
    """Divide mensajes largos antes de enviarlos."""
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("No se puede enviar un mensaje vacío.")

    pendientes = texto

    while pendientes:
        if len(pendientes) <= limite:
            send(pendientes)
            return

        corte = pendientes.rfind("\n", 0, limite + 1)
        if corte <= 0:
            corte = limite

        fragmento = pendientes[:corte].strip()
        if fragmento:
            send(fragmento)

        pendientes = pendientes[corte:].lstrip("\n")


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


def construir_inventario_diario(productos):
    bloques = [
        "INVENTARIO DIARIO",
        "",
        f"Productos encontrados: {len(productos)}",
        "",
    ]

    for producto in productos:
        bloques.extend([
            producto.get("nombre", ""),
            (
                f"{producto.get('marca', '')} | "
                f"{producto.get('categoria', '')}"
            ),
            f"Precio de origen: {producto.get('precio_origen', '')} EUR",
            producto.get("url", ""),
            "",
        ])

    return "\n".join(bloques)


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


def guardar_lotes_parciales(grupos, progreso, solo_validar=False):
    """
    Guarda lotes de hasta TAMANO_LOTE por alcance.

    En modo normal, solo registra un SKU como procesado después de que
    la escritura del lote en Supabase termina correctamente.
    """
    resultados = []

    for alcance, productos_alcance in grupos.items():
        ya_guardados = progreso.get(alcance, set())

        pendientes = [
            producto
            for producto in productos_alcance
            if obtener_sku(producto) not in ya_guardados
        ]

        print(
            f"{alcance}: {len(productos_alcance)} productos; "
            f"{len(pendientes)} pendientes."
        )

        if solo_validar:
            for inicio in range(0, len(pendientes), TAMANO_LOTE):
                lote = pendientes[inicio:inicio + TAMANO_LOTE]
                resultado = guardar_lote_supabase(
                    lote,
                    alcance=alcance,
                    solo_validar=True,
                )
                resultados.append(resultado)
            continue

        progreso.setdefault(alcance, set())

        for inicio in range(0, len(pendientes), TAMANO_LOTE):
            lote = pendientes[inicio:inicio + TAMANO_LOTE]
            numero_lote = inicio // TAMANO_LOTE + 1

            print(
                f"Guardando {alcance}, lote {numero_lote}: "
                f"{len(lote)} SKU."
            )

            resultado = guardar_lote_supabase(
                lote,
                alcance=alcance,
            )
            resultados.append(resultado)

            # Solo se marca el lote como completado después del éxito.
            progreso[alcance].update(
                obtener_sku(producto) for producto in lote
            )
            save_json(
                ARCHIVO_PROGRESO,
                {
                    "skus_guardados_por_alcance": {
                        clave: sorted(skus)
                        for clave, skus in progreso.items()
                    }
                },
            )

    return resultados


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
        enviar_texto_largo(evento["mensaje"])
        historial_nuevo.append({
            "fecha": datetime.now().isoformat(),
            "tipo": evento["tipo"],
            "mensaje": evento["mensaje"],
        })

    hoy = date.today().isoformat()
    estado_nuevo = dict(estado)

    if estado.get("ultima_ejecucion_completa") != hoy:
        enviar_texto_largo(construir_inventario_diario(actual))

    estado_nuevo["ultima_ejecucion_completa"] = hoy

    # Se guardan los archivos locales solamente después de completar
    # el guardado de todos los lotes.
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


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Monitor de Thomann con guardado no destructivo "
            "en lotes por búsqueda."
        )
    )
    parser.add_argument(
        "--solo-validar",
        action="store_true",
        help=(
            "Extrae y valida lotes contra Supabase sin escribir "
            "en la base, modificar JSON ni enviar mensajes."
        ),
    )
    args = parser.parse_args()

    estado, anteriores, historial = cargar_datos_locales()

    # scrape() debe devolver los productos extraídos en esta ejecución.
    # El monitor los divide en lotes; no presupone que scrape() ya lo haga.
    actual = scrape()

    if not isinstance(actual, list) or not actual:
        raise ValueError(
            "Inventario vacío o inválido. No se sincronizará."
        )

    print(f"Productos encontrados: {len(actual)}")
    mostrar_diagnostico(actual)

    grupos = agrupar_por_alcance(actual)

    if args.solo_validar:
        progreso = {
            alcance: set()
            for alcance in grupos
        }
        guardar_lotes_parciales(
            grupos,
            progreso,
            solo_validar=True,
        )
        print(
            "VALIDACIÓN FINALIZADA. No se escribió en Supabase, "
            "no se modificaron archivos locales y no se enviaron mensajes."
        )
        return

    progreso = cargar_progreso()

    try:
        guardar_lotes_parciales(grupos, progreso)
        verificar_progreso_completo(grupos, progreso)
    except Exception:
        print(
            "ERROR AL PROCESAR LOS LOTES. No se actualizarán "
            "productos.json, historial.json ni estado.json. "
            "El progreso confirmado se conserva para reanudar."
        )
        raise

    print("Todos los lotes de esta extracción fueron guardados.")

    for alcance, productos_alcance in grupos.items():
        print(
            f"{alcance}: {len(productos_alcance)} productos "
            "procesados; no se eliminó ningún SKU ausente."
        )

    finalizar_inventario(actual, estado, anteriores, historial)


if __name__ == "__main__":
    main()