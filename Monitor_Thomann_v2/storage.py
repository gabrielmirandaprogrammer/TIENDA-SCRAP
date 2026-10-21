from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import json
import os
import tempfile

from supabase_config import supabase


PROVEEDOR_ID = 1
DOMINIOS_ORIGEN = {"www.thomann.es", "thomann.es"}

CATEGORIAS_POR_TIPO = {
    "guitarra": {"Guitarras Eléctricas", "Guitarras Acústicas"},
    "bajo": {"Bajos Eléctricos"},
}

MARCA_CREABLE = "Sadowsky"


# ---------------------------------------------------------------------
# TASA DE CAMBIO Y PRECIO
# ---------------------------------------------------------------------

def obtener_tasa_eur_cop():
    api_key = os.environ.get("ALLRATESTODAY_API_KEY")
    if not api_key:
        raise ValueError(
            "Configura ALLRATESTODAY_API_KEY en el entorno."
        )

    parametros = urlencode({"source": "EUR", "target": "COP"})
    solicitud = Request(
        "https://allratestoday.com/api/v1/rates?" + parametros,
        headers={"Authorization": "Bearer " + api_key},
    )

    with urlopen(solicitud, timeout=20) as respuesta:
        filas = json.loads(respuesta.read().decode("utf8"))

    if not isinstance(filas, list):
        raise ValueError("La API de tasa devolvió una respuesta inválida.")

    fila = next(
        (
            item for item in filas
            if item.get("source") == "EUR"
            and item.get("target") == "COP"
        ),
        None,
    )

    if not fila:
        raise ValueError("La API no devolvió la tasa EUR/COP esperada.")

    tasa = Decimal(str(fila.get("rate")))
    if not tasa.is_finite() or tasa <= 0:
        raise ValueError("La tasa EUR/COP es inválida.")

    print(f"Tasa EUR/COP: {tasa}; fecha fuente: {fila.get('time')}")
    return tasa


def calcular_precio_cop(precio_origen, tasa):
    origen = Decimal(str(precio_origen))
    tasa = Decimal(str(tasa))

    if not origen.is_finite() or origen <= 0:
        raise ValueError("Precio de origen inválido.")
    if not tasa.is_finite() or tasa <= 0:
        raise ValueError("Tasa de cambio inválida.")

    venta = (
        origen
        * Decimal("1.20")
        * Decimal("1.20")
        * tasa
        * Decimal("1.05")
        / Decimal("0.80")
    )

    return int(
        (venta / Decimal("10000")).to_integral_value(
            rounding=ROUND_CEILING
        )
        * Decimal("10000")
    )


# ---------------------------------------------------------------------
# ARCHIVOS JSON LOCALES
# ---------------------------------------------------------------------

def load_json(file, default):
    """Lee JSON local; si no existe o está vacío, devuelve default."""
    if not os.path.exists(file):
        return default

    with open(file, "r", encoding="utf8") as archivo:
        contenido = archivo.read().strip()

    if not contenido:
        return default

    try:
        return json.loads(contenido)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{file} está dañado: {error}"
        ) from error


def save_json(file, data):
    """Escribe JSON con reemplazo atómico; los errores se propagan."""
    carpeta = os.path.dirname(os.path.abspath(file))
    descriptor, temporal = tempfile.mkstemp(
        prefix=".tmp_",
        suffix=".json",
        dir=carpeta,
    )

    try:
        with os.fdopen(descriptor, "w", encoding="utf8") as archivo:
            json.dump(data, archivo, ensure_ascii=False, indent=2)
            archivo.flush()
            os.fsync(archivo.fileno())

        os.replace(temporal, file)

    except Exception:
        if os.path.exists(temporal):
            os.remove(temporal)
        raise


# ---------------------------------------------------------------------
# VALIDACIÓN Y CONSULTAS
# ---------------------------------------------------------------------

def _texto_obligatorio(valor, campo, sku):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"SKU {sku}: falta un valor válido para {campo}.")
    return valor.strip()


def _validar_url(valor, campo, sku):
    valor = _texto_obligatorio(valor, campo, sku)
    partes = urlparse(valor)

    if partes.scheme not in ("http", "https") or not partes.netloc:
        raise ValueError(f"SKU {sku}: {campo} no es una URL válida.")

    return valor


def _consultar_paginas(consulta, tamano=500):
    filas = []
    inicio = 0

    while True:
        respuesta = (
            consulta()
            .order("id")
            .range(inicio, inicio + tamano - 1)
            .execute()
        )

        if respuesta.data is None:
            raise RuntimeError("Supabase no devolvió datos de consulta.")

        filas.extend(respuesta.data)

        if len(respuesta.data) < tamano:
            return filas

        inicio += tamano


def _en_lotes(valores, tamano=100):
    valores = list(valores)
    for inicio in range(0, len(valores), tamano):
        yield valores[inicio:inicio + tamano]


def _normalizar_nombre(texto):
    return " ".join(str(texto or "").split()).casefold()


def _resolver_catalogo(tabla, nombres, permitir_creacion=None):
    filas = _consultar_paginas(
        lambda: supabase.table(tabla).select("id,nombre,activo")
    )
    resultado = {}

    for nombre in sorted(nombres):
        coincidencias = [
            fila for fila in filas
            if _normalizar_nombre(fila.get("nombre"))
            == _normalizar_nombre(nombre)
        ]

        if len(coincidencias) > 1:
            raise ValueError(f"{tabla}: nombre duplicado: {nombre}")

        if not coincidencias:
            if permitir_creacion and nombre == permitir_creacion:
                resultado[nombre] = None
                continue
            raise ValueError(
                f"{tabla}: falta el registro requerido: {nombre}"
            )

        fila = coincidencias[0]
        if fila.get("activo") is not True or fila.get("id") is None:
            raise ValueError(
                f"{tabla}: registro inactivo o inválido: {nombre}"
            )

        resultado[nombre] = fila["id"]

    return resultado


def _imagenes_existentes(ids_producto):
    por_producto = {}

    for lote in _en_lotes(ids_producto):
        filas = _consultar_paginas(
            lambda lote=lote: (
                supabase.table("producto_imagenes")
                .select("id,producto_id,url")
                .in_("producto_id", lote)
            )
        )

        for fila in filas:
            por_producto.setdefault(fila["producto_id"], []).append(fila)

    return por_producto


def _preparar_productos(productos, alcance):
    if not isinstance(alcance, str) or not alcance.strip():
        raise ValueError("El alcance debe ser un texto no vacío.")

    alcance = alcance.strip()

    if not isinstance(productos, list) or not productos:
        raise ValueError(
            f"{alcance}: el lote está vacío o no es una lista."
        )

    preparados = []
    codigos = set()

    for producto in productos:
        if not isinstance(producto, dict):
            raise ValueError("El lote contiene un producto inválido.")

        sku_original = producto.get("sku")
        if sku_original is None or isinstance(sku_original, bool):
            raise ValueError("Producto sin SKU válido.")

        sku = str(sku_original).strip()
        if not sku or not sku.isdigit():
            raise ValueError(f"SKU inválido: {sku!r}")
        if sku in codigos:
            raise ValueError(f"SKU duplicado en el lote: {sku}")
        codigos.add(sku)

        nombre = _texto_obligatorio(producto.get("nombre"), "nombre", sku)
        descripcion = _texto_obligatorio(
            producto.get("descripcion"), "descripcion", sku
        )
        disponibilidad = _texto_obligatorio(
            producto.get("disponibilidad_texto"),
            "disponibilidad_texto",
            sku,
        )
        url = _validar_url(producto.get("url"), "url", sku)

        if urlparse(url).hostname not in DOMINIOS_ORIGEN:
            raise ValueError(f"SKU {sku}: dominio de origen inesperado.")

        try:
            precio_origen = Decimal(str(producto.get("precio_origen")))
        except Exception as error:
            raise ValueError(
                f"SKU {sku}: precio_origen inválido."
            ) from error

        if not precio_origen.is_finite() or precio_origen <= 0:
            raise ValueError(f"SKU {sku}: precio_origen inválido.")

        imagen = producto.get("imagen")
        if imagen:
            imagen = _validar_url(imagen, "imagen", sku)

        galeria = producto.get("gallery", [])
        if not isinstance(galeria, list):
            raise ValueError(f"SKU {sku}: gallery debe ser una lista.")

        galeria_validada = []
        for url_imagen in galeria:
            url_imagen = _validar_url(url_imagen, "gallery", sku)
            if url_imagen not in galeria_validada:
                galeria_validada.append(url_imagen)

        if not galeria_validada:
            raise ValueError(f"SKU {sku}: galería vacía.")

        marca = _texto_obligatorio(producto.get("marca"), "marca", sku)
        categoria = _texto_obligatorio(
            producto.get("categoria"), "categoria", sku
        )
        alcance_producto = _texto_obligatorio(
            producto.get("alcance_scraping"),
            "alcance_scraping",
            sku,
        )

        if alcance_producto != alcance:
            raise ValueError(
                f"SKU {sku}: su alcance es {alcance_producto!r}, "
                f"pero esta llamada recibió {alcance!r}."
            )

        preparados.append({
            "sku": sku,
            "nombre": nombre,
            "descripcion": descripcion,
            "disponibilidad_texto": disponibilidad,
            "url": url,
            "imagen": imagen,
            "gallery": galeria_validada,
            "marca": marca,
            "categoria": categoria,
            "origen": precio_origen,
        })

    return preparados


# ---------------------------------------------------------------------
# GUARDADO NO DESTRUCTIVO
# ---------------------------------------------------------------------

def guardar_lote_supabase(
    productos,
    *,
    alcance,
    tasa=None,
    solo_validar=False,
):
    """
    Inserta o actualiza únicamente los productos recibidos.

    Esta función NO elimina productos ausentes, no reconcilia el alcance
    y no borra imágenes existentes. Es la función apropiada para lotes
    parciales de scraping.
    """
    preparados = _preparar_productos(productos, alcance)

    if tasa is None:
        tasa = obtener_tasa_eur_cop()
    else:
        tasa = Decimal(str(tasa))

    if not tasa.is_finite() or tasa <= 0:
        raise ValueError("La tasa de cambio no es válida.")

    for producto in preparados:
        producto["precio_cop"] = calcular_precio_cop(
            producto["origen"],
            tasa,
        )

    codigos_lote = {producto["sku"] for producto in preparados}

    existentes = _consultar_paginas(
        lambda: (
            supabase.table("productos")
            .select(
                "id,codigo_proveedor,precio_origen,alcance_scraping"
            )
            .eq("proveedor_id", PROVEEDOR_ID)
        )
    )

    por_codigo = {}
    for fila in existentes:
        codigo = str(fila.get("codigo_proveedor") or "").strip()
        if codigo not in codigos_lote:
            continue

        if codigo in por_codigo:
            raise ValueError(
                f"SKU {codigo}: hay registros duplicados en Supabase."
            )

        alcance_anterior = fila.get("alcance_scraping")
        if alcance_anterior not in (None, "", alcance):
            raise ValueError(
                f"SKU {codigo} ya pertenece al alcance "
                f"{alcance_anterior!r}; se bloquea el cambio."
            )

        por_codigo[codigo] = fila

    marcas = _resolver_catalogo(
        "marcas",
        {producto["marca"] for producto in preparados},
        permitir_creacion=MARCA_CREABLE,
    )
    categorias = _resolver_catalogo(
        "categorias",
        {producto["categoria"] for producto in preparados},
    )

    resumen = {
        "alcance": alcance,
        "productos_validados": len(preparados),
        "por_crear": sum(
            producto["sku"] not in por_codigo
            for producto in preparados
        ),
        "por_actualizar": sum(
            producto["sku"] in por_codigo
            for producto in preparados
        ),
        "creados": 0,
        "actualizados": 0,
        "eliminados": 0,
    }

    if solo_validar:
        return resumen

    try:
        # Crear la marca autorizada solamente si todavía no existe.
        for nombre, identificador in list(marcas.items()):
            if identificador is not None:
                continue

            respuesta = (
                supabase.table("marcas")
                .insert({"nombre": nombre, "activo": True})
                .execute()
            )

            if (
                not respuesta.data
                or len(respuesta.data) != 1
                or respuesta.data[0].get("id") is None
            ):
                raise RuntimeError(
                    f"No se confirmó la creación de la marca {nombre}."
                )

            marcas[nombre] = respuesta.data[0]["id"]

        ahora = datetime.now(timezone.utc).isoformat()
        imagenes_actuales = _imagenes_existentes(
            fila["id"] for fila in por_codigo.values()
        )

        for producto in preparados:
            sku = producto["sku"]
            anterior = por_codigo.get(sku)

            datos = {
                "nombre": producto["nombre"],
                "sku": sku,
                "codigo_proveedor": sku,
                "precio": producto["precio_cop"],
                "precio_origen": float(producto["origen"]),
                "descripcion": producto["descripcion"],
                "disponibilidad_texto": producto["disponibilidad_texto"],
                "url_origen": producto["url"],
                "moneda": "EUR",
                "proveedor_id": PROVEEDOR_ID,
                "marca_id": marcas[producto["marca"]],
                "categoria_id": categorias[producto["categoria"]],
                "alcance_scraping": alcance,
                "disponible_origen": True,
                "ultima_actualizacion": ahora,
                "ultimo_scraping": ahora,
            }

            if producto["imagen"]:
                datos["imagen_principal"] = producto["imagen"]

            if anterior:
                producto_id = anterior["id"]

                respuesta = (
                    supabase.table("productos")
                    .update(datos)
                    .eq("proveedor_id", PROVEEDOR_ID)
                    .eq("id", producto_id)
                    .execute()
                )

                if not respuesta.data:
                    raise RuntimeError(
                        f"SKU {sku}: actualización sin confirmación."
                    )

                precio_anterior = anterior.get("precio_origen")
                if (
                    precio_anterior is not None
                    and Decimal(str(precio_anterior)) != producto["origen"]
                ):
                    respuesta = (
                        supabase.table("historial_precios")
                        .insert({
                            "producto_id": producto_id,
                            "precio_anterior": precio_anterior,
                            "precio_nuevo": float(producto["origen"]),
                            "moneda": "EUR",
                        })
                        .execute()
                    )
                    if not respuesta.data:
                        raise RuntimeError(
                            f"SKU {sku}: historial sin confirmación."
                        )

                # Agrega imágenes nuevas. No elimina imágenes existentes.
                urls_existentes = {
                    fila["url"]
                    for fila in imagenes_actuales.get(producto_id, [])
                }
                nuevas = [
                    url_imagen
                    for url_imagen in producto["gallery"]
                    if url_imagen not in urls_existentes
                ]

                if nuevas:
                    respuesta = (
                        supabase.table("producto_imagenes")
                        .insert([
                            {"producto_id": producto_id, "url": url_imagen}
                            for url_imagen in nuevas
                        ])
                        .execute()
                    )
                    if (
                        not respuesta.data
                        or len(respuesta.data) != len(nuevas)
                    ):
                        raise RuntimeError(
                            f"SKU {sku}: imágenes sin confirmación."
                        )

                resumen["actualizados"] += 1

            else:
                # No se deduce inventario físico a partir del listado web.
                datos["stock"] = 0
                datos["stock_origen"] = 0

                respuesta = (
                    supabase.table("productos")
                    .insert(datos)
                    .execute()
                )

                if (
                    not respuesta.data
                    or respuesta.data[0].get("id") is None
                ):
                    raise RuntimeError(
                        f"SKU {sku}: inserción sin confirmación."
                    )

                producto_id = respuesta.data[0]["id"]

                respuesta = (
                    supabase.table("producto_imagenes")
                    .insert([
                        {"producto_id": producto_id, "url": url_imagen}
                        for url_imagen in producto["gallery"]
                    ])
                    .execute()
                )

                if (
                    not respuesta.data
                    or len(respuesta.data) != len(producto["gallery"])
                ):
                    raise RuntimeError(
                        f"SKU {sku}: imágenes sin confirmación."
                    )

                resumen["creados"] += 1

        # Verifica que los SKU de este lote estén presentes.
        guardados = _consultar_paginas(
            lambda: (
                supabase.table("productos")
                .select("id,codigo_proveedor")
                .eq("proveedor_id", PROVEEDOR_ID)
                .eq("alcance_scraping", alcance)
            )
        )

        codigos_guardados = {
            str(fila.get("codigo_proveedor") or "").strip()
            for fila in guardados
        }

        if not codigos_lote.issubset(codigos_guardados):
            raise RuntimeError(
                f"{alcance}: faltan SKU del lote después del guardado."
            )

        respuesta = (
            supabase.table("scraping_logs")
            .insert({
                "proveedor_id": PROVEEDOR_ID,
                "productos_procesados": len(preparados),
                "productos_creados": resumen["creados"],
                "productos_actualizados": resumen["actualizados"],
                "errores": 0,
                "observacion": (
                    f"Lote parcial no destructivo. Alcance: {alcance}; "
                    "no se eliminaron productos ni imágenes."
                ),
            })
            .execute()
        )

        if not respuesta.data:
            raise RuntimeError(
                f"{alcance}: log de scraping sin confirmación."
            )

    except Exception:
        print(
            f"{alcance}: el guardado del lote se interrumpió. "
            "Supabase puede conservar escrituras parciales; "
            "no se eliminan registros."
        )
        raise

    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return resumen


def guardar_supabase(
    productos,
    *,
    alcance,
    tasa=None,
    solo_validar=False,
):
    """
    Compatibilidad con el nombre anterior.
    Ahora guarda de manera no destructiva: nunca elimina ausentes.
    """
    return guardar_lote_supabase(
        productos,
        alcance=alcance,
        tasa=tasa,
        solo_validar=solo_validar,
    )


def guardar_inventario_supabase(productos, *, solo_validar=False):
    """
    Guarda los productos recibidos agrupados por alcance.

    No comprueba que estén presentes las siete búsquedas y no elimina
    ningún producto ausente. Puede recibir un inventario parcial.
    """
    if not isinstance(productos, list) or not productos:
        raise ValueError("Inventario vacío o inválido.")

    grupos = {}
    vistos = set()

    for producto in productos:
        if not isinstance(producto, dict):
            raise ValueError("Producto inválido en el inventario.")

        alcance = producto.get("alcance_scraping")
        if not isinstance(alcance, str) or not alcance.strip():
            raise ValueError("Producto sin alcance_scraping válido.")

        sku = str(producto.get("sku") or "").strip()
        if not sku.isdigit() or sku in vistos:
            raise ValueError(f"SKU inválido o repetido: {sku!r}")

        vistos.add(sku)
        grupos.setdefault(alcance.strip(), []).append(producto)

    tasa = obtener_tasa_eur_cop()

    return [
        guardar_lote_supabase(
            lote,
            alcance=alcance,
            tasa=tasa,
            solo_validar=solo_validar,
        )
        for alcance, lote in grupos.items()
    ]