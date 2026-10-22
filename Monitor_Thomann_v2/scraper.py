from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

import re
import time
import unicodedata


MAX_ERRORES_POR_BUSQUEDA = 10
PRECIO_MINIMO_EUR = 100
TAMANO_LOTE = 20

# Tolerancia al comparar el precio del listado con el guardado en base.
TOLERANCIA_PRECIO_EUR = 0.01

MENSAJES_RETIRADO = (
    "ya no se encuentra en nuestro catalogo",
    "no dude en visitar alternativamente la pagina de categoria",
)


# Textos de disponibilidad de Thomann, ya normalizados (minúsculas, sin tildes).
PATRON_DISPONIBILIDAD = re.compile(
    r"^(?:"
    r"en stock"
    r"|disponible(?: .*)?"
    r"|envio (?:inmediato|en \d+.*|gratuito.*)"
    r"|plazo de entrega.*"
    r"|no disponible.*"
    r"|agotado.*"
    r"|bajo pedido.*"
    r"|proximamente.*"
    r"|entrega (?:en|aproximada|prevista).*"
    r"|listo para (?:el )?envio.*"
    r")$"
)


BUSQUEDAS = (
    ("marcus miller", "Marcus Miller", "bajo"),
    ("ibanez guitar", "Ibanez", "guitarra"),
    ("ibanez bass", "Ibanez", "bajo"),
    ("sadowsky bass", "Sadowsky", "bajo"),
    ("warwick bass", "Warwick", "bajo"),
)

def normalizar(texto):
    texto = texto or ""
    return " ".join(
        "".join(
            caracter
            for caracter in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caracter)
        ).casefold().split()
    )


def alcance_busqueda(termino):
    if normalizar(termino) == "marcus miller":
        return "busqueda:marcus miller|filtro:marcus-miller|v1"
    return f"busqueda:{normalizar(termino)}|v1"


REGLAS_ETIQUETA = tuple(
    (re.compile(patron), categoria, familia)
    for patron, categoria, familia in (
        (
            r"encordados?\b|strings?\b|string\s+sets?\b|cuerdas\b",
            "Encordados",
            "accesorio",
        ),
        (
            r"guitars?\s+(?:cases?|stands?|straps?|cables?|covers?|cloths?|strings?|picks?)\b|"
            r"bass\s+(?:cases?|stands?|straps?|cables?|covers?|cloths?|strings?)\b",
            "Accesorios",
            "accesorio",
        ),
        (
            r"amplificadores?\b|amplis?\b|(?:guitar|bass)\s+amps?\b|combos?\b|"
            r"pedales?\b|pedalboards?\b|pedals?\b|efectos?\b|effects?\b|effetcs?\b|"
            r"multi\s+effects?\b",
            "Accesorios",
            "accesorio",
        ),
        (
            r"fundas?\b|gig\s?bags?\b|bolsas?\b|estuches?\b|caja\s+rigida\b|"
            r"cases?\b|cables?\b|correas?\b|straps?\b|soportes?\b|stands?\b|"
            r"afinadores?\b|tuners?\b|pastillas?\b|pickups?\b|pin\s+pullers?\b|"
            r"cloths?\b|polishing\b|pick\s+sets?\b|thrones?\b",
            "Accesorios",
            "accesorio",
        ),
        (r"packs?\b|bundles?\b", "Packs", "accesorio"),
        (
            r"sistema\s+de\s+tremolo\b|tremolos?\b|puentes?\b|bridges?\b|clavijeros?\b",
            "Partes y otros",
            "accesorio",
        ),
        (
            r"ukuleles?\b|ukeleles?\b|banjos?\b|mandolinas?\b|mandolins?\b|"
            r"armonicas?\b|harmonicas?\b|guitarra\s+piccolo\b|piccolo\s+guitars?\b",
            "Otros instrumentos",
            "accesorio",
        ),
        (
            r"bajo\s+acusticos?\b|(?:electro[-\s]?)?acoustic\s+bass(?:\s+guitars?)?\b",
            "Bajos Acústicos",
            "accesorio",
        ),
        (
            r"bajo\s+electrico\b|bajo\s+de\s+[4-9]\s+cuerdas\b|"
            r"bajo\s+[4-9]\s+cuerdas\b|bajos?\b",
            "Bajos Eléctricos",
            "bajo",
        ),
        (
            r"(?:electric\s+)?bass(?:\s+guitars?)?\b|"
            r"[4-9][-\s]?strings?\s+(?:electric\s+)?bass\b|e[-\s]?bass\b",
            "Bajos Eléctricos",
            "bajo",
        ),
        (
            r"guitarra\s+electric[ao]s?\b",
            "Guitarras Eléctricas",
            "guitarra",
        ),
        (
            r"(?:[4-9][-\s]?strings?\s+)?(?:electric\s+)?guitars?\b|e[-\s]?guitars?\b",
            "Guitarras Eléctricas",
            "guitarra",
        ),
        (
            r"guitarra\s+(?:electroacustica|acustica)\b|"
            r"guitarra\s+(?:clasica|espanola|criolla)\b|"
            r"guitarra\s+de\s+concierto\b",
            "Guitarras Acústicas",
            "guitarra",
        ),
        (
            r"(?:electro[-\s]?)?acoustic(?:[-\s]?electric)?\s+guitars?\b|"
            r"classical\s+guitars?\b|concert\s+guitars?\b",
            "Guitarras Acústicas",
            "guitarra",
        ),
    )
)


def clasificar_etiqueta(etiqueta):
    texto = normalizar(etiqueta)
    for patron, categoria, familia in REGLAS_ETIQUETA:
        if patron.match(texto):
            return categoria, familia
    return None


def obtener_categoria(driver, nombre_producto=""):
    """
    Clasifica el producto por el H2 de la ficha.
    Si la ficha no trae H2 (B-Stock, maquetaciones distintas), usa el
    breadcrumb y el nombre del listado; si aun así no hay regla, devuelve
    "Sin Categoría"/"accesorio" para que el filtro de familia lo excluya
    sin contarlo como error de extracción.
    """
    selector = "h2.fx-headline.fx-headline--3.fx-space-bottom--m"

    try:
        elementos = WebDriverWait(driver, 15).until(
            lambda navegador: [
                elemento
                for elemento in navegador.find_elements(By.CSS_SELECTOR, selector)
                if elemento.is_displayed() and elemento.text.strip()
            ],
            message="No apareció la etiqueta H2 del producto.",
        )
        etiquetas = list(dict.fromkeys(
            elemento.text.strip() for elemento in elementos
        ))
    except TimeoutException:
        etiquetas = []
        for elemento in driver.find_elements(
            By.CSS_SELECTOR,
            "[class*='breadcrumb'] a, nav[aria-label*='readcrumb'] a",
        ):
            texto = elemento.text.strip()
            if texto and texto not in etiquetas:
                etiquetas.append(texto)
        if nombre_producto:
            etiquetas.append(nombre_producto)
        print(
            "AVISO: ficha sin H2; se clasifica por breadcrumb/nombre: "
            f"{etiquetas}"
        )

    clasificaciones = [
        (etiqueta, clasificar_etiqueta(etiqueta))
        for etiqueta in etiquetas
    ]

    instrumentos = [
        (etiqueta, resultado)
        for etiqueta, resultado in clasificaciones
        if resultado and resultado[1] in ("guitarra", "bajo")
    ]
    accesorios = [
        (etiqueta, resultado)
        for etiqueta, resultado in clasificaciones
        if resultado and resultado[1] == "accesorio"
    ]

    if instrumentos:
        if len({resultado[0] for _, resultado in instrumentos}) > 1:
            return " / ".join(etiquetas), "Sin Categoría", "accesorio"
        etiqueta, (categoria, familia) = instrumentos[0]
        return etiqueta, categoria, familia

    if accesorios:
        etiqueta, (categoria, familia) = accesorios[0]
        return etiqueta, categoria, familia

    return " / ".join(etiquetas), "Sin Categoría", "accesorio"

def aceptar_cookies(driver, wait):
    try:
        boton = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "button.js-accept-all-cookies")
            )
        )
        driver.execute_script("arguments[0].click();", boton)
    except Exception:
        pass


def obtener_total_resultados(driver):
    try:
        texto = driver.find_element(
            By.CSS_SELECTOR,
            "[data-track-id='resultCountContainer']",
        ).text.strip()
        return int(texto.replace(".", "").replace(",", ""))
    except Exception as exc:
        print(f"No se pudo leer el total anunciado: {exc}")
        return 0


def limpiar_precio(texto):
    texto = (texto or "").replace("€", "").replace("$", "")
    texto = texto.replace(" ", "").replace("\u00a0", "")
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except (TypeError, ValueError):
        return 0.0


def cargar_todos_los_productos(driver, max_intentos_sin_boton=4):
    selector_productos = "div.fx-product-list-entry"
    selector_boton = "button.search-pagination__show-more"

    # Si al final solo faltan pocas tarjetas respecto al total anunciado,
    # se continúa con lo obtenido en vez de abortar toda la ejecución.
    TOLERANCIA_TARJETAS_FALTANTES = 5

    def contar(navegador):
        return len(navegador.find_elements(By.CSS_SELECTOR, selector_productos))

    WebDriverWait(driver, 40).until(
        lambda navegador: contar(navegador) > 0,
        message="No aparecieron tarjetas en el listado."
    )

    cantidad_anterior = None
    fallos_sin_avance = 0

    while True:
        cantidad_actual = contar(driver)
        total_actual = obtener_total_resultados(driver)

        print(
            f"Productos cargados: {cantidad_actual} | "
            f"Total anunciado: {total_actual}"
        )

        if cantidad_actual <= 0:
            raise ValueError("El listado quedó vacío durante la carga.")

        # El total es suficiente para saber que ya terminó la paginación.
        if total_actual > 0 and cantidad_actual >= total_actual:
            print(
                f"Carga completa: se alcanzó el total anunciado "
                f"({cantidad_actual}/{total_actual})."
            )
            return

        if cantidad_anterior is not None and cantidad_actual < cantidad_anterior:
            raise ValueError("El listado perdió tarjetas durante la paginación.")

        if cantidad_anterior is not None and cantidad_actual > cantidad_anterior:
            fallos_sin_avance = 0

        cantidad_anterior = cantidad_actual

        try:
            def boton_o_avance(navegador):
                # Si una petición anterior añadió tarjetas, vuelve al inicio
                # del bucle para actualizar los contadores.
                if contar(navegador) > cantidad_actual:
                    return True

                return EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, selector_boton)
                )(navegador)

            resultado = WebDriverWait(driver, 20).until(
                boton_o_avance,
                message="Botón mostrar más ausente, oculto o deshabilitado."
            )

            if resultado is True:
                continue

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                resultado
            )
            driver.execute_script("arguments[0].click();", resultado)

            WebDriverWait(driver, 40).until(
                lambda navegador: contar(navegador) > cantidad_actual,
                message=(
                    "El botón fue pulsado, pero no aparecieron "
                    "nuevas tarjetas."
                )
            )

        except (TimeoutException, StaleElementReferenceException) as e:
            cantidad_final = contar(driver)
            total_final = obtener_total_resultados(driver)

            # Si avanzó mientras se procesaba la excepción, actualizar
            # cantidades y continuar.
            if cantidad_final > cantidad_actual:
                continue

            # Si el listado ya llegó al total, la ausencia del botón es normal.
            if total_final > 0 and cantidad_final >= total_final:
                print(
                    f"Carga completa: {cantidad_final}/{total_final}. "
                    "No quedan más tarjetas por cargar."
                )
                return

            fallos_sin_avance += 1

            print(
                f"PAGINACION SIN AVANCE: intento {fallos_sin_avance}/"
                f"{max_intentos_sin_boton} | tarjetas={cantidad_final} | "
                f"total={total_final} | {type(e).__name__}"
            )

            if fallos_sin_avance >= max_intentos_sin_boton:
                deficit = (
                    total_final - cantidad_final
                    if total_final > 0
                    else 0
                )

                # Caso 254/257: faltan muy pocas tarjetas y el botón ya no
                # aparece. Continuar es mejor que perder toda la ejecución;
                # esos pocos SKU quedarán para la siguiente pasada.
                if total_final > 0 and deficit <= TOLERANCIA_TARJETAS_FALTANTES:
                    print(
                        f"ADVERTENCIA: «mostrar más» no cargó las últimas "
                        f"{deficit} tarjetas tras {max_intentos_sin_boton} "
                        f"intentos. Se continúa con las {cantidad_final} "
                        "obtenidas; no se garantiza el listado completo."
                    )
                    return

                raise ValueError(
                    "No se pudo completar la carga del listado con "
                    f"«mostrar más». Hay {cantidad_final} tarjetas cargadas "
                    f"y el total anunciado es {total_final}."
                ) from e

            # Pausa y scroll al fondo: el botón a veces tarda en re-renderizar.
            time.sleep(5)
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )


def extraer_tarjetas_listado(driver):
    elementos = driver.find_elements(
        By.CSS_SELECTOR,
        "div.fx-product-list-entry[data-track-id='product'][data-product-id]",
    )

    tarjetas = []
    skus_vistos = set()

    for elemento in elementos:
        try:
            sku = elemento.get_attribute("data-product-id")
            if not sku or sku in skus_vistos:
                continue
            skus_vistos.add(sku)

            def texto_de(selector):
                encontrados = elemento.find_elements(By.CSS_SELECTOR, selector)
                return encontrados[0].text.strip() if encontrados else ""

            enlaces = elemento.find_elements(
                By.CSS_SELECTOR,
                "a.product__content[href], a.product__image[href]",
            )
            href = enlaces[0].get_attribute("href") if enlaces else ""

            texto_tarjeta = elemento.text
            coincidencia = re.search(
                r"([\d.]+(?:,\d{1,2})?)\s*€",
                texto_tarjeta,
            )
            precio = None
            precio_texto = ""

            if coincidencia:
                precio_texto = coincidencia.group(0).strip()
                precio = float(
                    coincidencia.group(1)
                    .replace(".", "")
                    .replace(",", ".")
                )

            tarjetas.append({
                "sku_listado": str(sku),
                "marca": texto_de(".title__manufacturer"),
                "nombre": texto_de(".title__name"),
                "precio": precio,
                "precio_texto": precio_texto,
                "url": href,
                "agotado": bool(
                    re.search(
                        r"el producto est[aá] agotado",
                        texto_tarjeta,
                        re.IGNORECASE,
                    )
                ),
            })
        except Exception as exc:
            print(f"ERROR LEYENDO TARJETA: {type(exc).__name__}: {exc}")

    print(f"TARJETAS ÚNICAS EN EL LISTADO: {len(tarjetas)}")
    return tarjetas


def obtener_sku(driver):
    try:
        coincidencia = re.search(
            r'"artnr"\s*:\s*"(\d+)"',
            driver.page_source,
        )
        return coincidencia.group(1) if coincidencia else None
    except Exception:
        return None


def producto_disponible(driver):
    texto = driver.execute_script(
        "return document.body ? document.body.innerText : '';"
    ) or ""
    texto = normalizar(texto)
    return not any(mensaje in texto for mensaje in MENSAJES_RETIRADO)


def esperar_producto_o_retirada(driver):
    def comprobar(navegador):
        if not producto_disponible(navegador):
            return "retirado", None

        sku = obtener_sku(navegador)
        if sku:
            return "producto", sku
        return False

    return WebDriverWait(driver, 40).until(
        comprobar,
        message="No se pudo confirmar el SKU ni la retirada del catálogo.",
    )


def obtener_galeria_hd(driver):
    galeria = []
    for imagen in driver.find_elements(By.TAG_NAME, "img"):
        src = imagen.get_attribute("src")
        if (
            src
            and "static-thomann.de" in src
            and "padthumb600x600" in src
            and "logos" not in src
            and not src.endswith(".svg")
            and src not in galeria
        ):
            galeria.append(src)
    return galeria[:10]


def obtener_galeria_producto(driver):
    galeria = obtener_galeria_hd(driver)
    if galeria:
        return galeria

    enlaces = driver.find_elements(By.CSS_SELECTOR, ".seeother a")
    if not enlaces:
        return []

    url_original = enlaces[0].get_attribute("href")
    ventana_actual = driver.current_window_handle

    try:
        driver.switch_to.new_window("tab")
        driver.get(url_original)
        time.sleep(3)
        return obtener_galeria_hd(driver)
    except Exception as exc:
        print(f"ERROR OBTENIENDO GALERÍA DEL PRODUCTO ORIGINAL: {exc}")
        return []
    finally:
        if driver.current_window_handle != ventana_actual:
            driver.close()
        driver.switch_to.window(ventana_actual)


def obtener_disponibilidad(driver, espera=10):
    """
    Lee el texto de disponibilidad de la ficha.
    Es un campo informativo: si no se reconoce, devuelve "" en vez de
    lanzar una excepción y tumbar el producto.
    """
    def leer(navegador):
        candidatos = navegador.execute_script(r"""
            const patron = /(en stock|disponible|env[ií]o|plazo de entrega|no disponible|agotado|bajo pedido|pr[oó]ximamente)/i;
            const vistos = new Set();
            const salida = [];
            for (const el of document.querySelectorAll('span, div, p, strong, b')) {
                if (el.children.length > 0) continue;
                const texto = (el.innerText || '').replace(/\s+/g, ' ').trim();
                if (!texto || texto.length > 80) continue;
                if (!patron.test(texto)) continue;
                if (vistos.has(texto)) continue;
                vistos.add(texto);
                salida.push(texto);
            }
            return salida;
        """) or []

        reconocidos = [
            texto for texto in candidatos
            if PATRON_DISPONIBILIDAD.match(normalizar(texto))
        ]
        return reconocidos or False

    try:
        textos = WebDriverWait(driver, espera).until(
            leer,
            message="Sin texto de disponibilidad reconocible.",
        )
    except TimeoutException:
        return ""

    # Si la ficha muestra varios textos, se toma el más corto (el específico).
    return sorted(set(textos), key=len)[0]


def obtener_product_details(driver):
    items = driver.find_elements(
        By.CSS_SELECTOR,
        "ul.product-text__list li .list-item__text",
    )
    if items:
        detalles = [
            item.text.strip()
            for item in items
            if item.text.strip()
        ]
        if detalles:
            return detalles

    try:
        parrafo = driver.find_element(
            By.CSS_SELECTOR,
            "p.product-text__description",
        )
        texto = parrafo.text.strip()
        texto = re.sub(
            r"^B-Stock,\s*",
            "",
            texto,
            flags=re.IGNORECASE,
        )
        return [
            parte.strip()
            for parte in texto.split(",")
            if parte.strip()
        ]
    except Exception:
        return []


def cerrar_pestanas_producto(driver, ventana_principal):
    for ventana in list(driver.window_handles):
        if ventana != ventana_principal:
            driver.switch_to.window(ventana)
            driver.close()
    driver.switch_to.window(ventana_principal)


def emitir_lote(on_batch, lote, alcance, termino, numero_lote):
    if not lote:
        return

    print(
        f"LOTE {numero_lote} LISTO | búsqueda={termino} | "
        f"productos={len(lote)}"
    )

    # Si el callback falla, el error se propaga y detiene el proceso.
    # Así no se continúa como si el lote se hubiera guardado correctamente.
    on_batch(lote, alcance)


def imprimir_lote_consola(lote, alcance):
    skus = [producto["sku"] for producto in lote]
    print(
        f"LOTE DE PRUEBA | alcance={alcance} | "
        f"{len(lote)} productos | SKU: {', '.join(skus)}"
    )


def emitir_precios(on_precios, actualizaciones, alcance, termino, numero_lote):
    if not actualizaciones:
        return

    print(
        f"LOTE DE PRECIOS {numero_lote} LISTO | búsqueda={termino} | "
        f"productos={len(actualizaciones)}"
    )

    on_precios(actualizaciones, alcance)


def imprimir_precios_consola(actualizaciones, alcance):
    print(
        f"PRECIOS DE PRUEBA | alcance={alcance} | "
        f"{len(actualizaciones)} cambios | "
        + ", ".join(
            f"{item['sku']}: EUR {item['precio_origen']}"
            for item in actualizaciones
        )
    )


def scrape(
    on_batch=None,
    batch_size=TAMANO_LOTE,
    on_fin_alcance=None,
    on_precios=None,
    obtener_existentes=None,
    obtener_exclusiones=None,
    on_excluir=None,
):
    """
    Carga el listado completo de cada búsqueda y recorre sus fichas en orden.

    Al completar cada lote, llama on_batch(lote, alcance).
    Al terminar cada búsqueda llama
    on_fin_alcance(alcance, skus_en_pagina, skus_agotados, listado_completo)
    para que el monitor reconcilie la base contra el listado completo de la
    página: borra los SKU que ya no aparecen y marca los agotados.

    Si se recibe obtener_existentes(alcance) -> {sku: {...}}, solo se abre la
    ficha de los SKU nuevos o sin imágenes; los que ya están completos en la
    base se omiten o se actualizan únicamente de precio desde el listado,
    entregados por on_precios(actualizaciones, alcance).

    Si se recibe obtener_exclusiones() -> {sku: {...}}, los SKU ya excluidos
    en otras búsquedas o ejecuciones anteriores (razón "tipo" con otra
    familia, o "retirado") se omiten sin abrir su ficha. Cada exclusión
    nueva detectada se reporta con on_excluir(sku, datos) para que el
    monitor la guarde.
    """
    if not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError("batch_size debe ser un entero positivo.")

    callback = on_batch or imprimir_lote_consola
    callback_precios = on_precios or imprimir_precios_consola

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=es-CO")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    productos_unicos = {}
    ventana_principal = None

    try:
        ventana_principal = driver.current_window_handle

        for termino, marca_objetivo, familia_objetivo in BUSQUEDAS:
            alcance = alcance_busqueda(termino)
            print(f"\n{'=' * 70}")
            print(f"BÚSQUEDA: {termino} | ALCANCE: {alcance}")
            print(f"TAMAÑO DE LOTE: {batch_size}")
            print(f"{'=' * 70}")

            driver.get("https://www.thomann.es/")
            aceptar_cookies(driver, WebDriverWait(driver, 3))

            wait = WebDriverWait(driver, 40)
            campo_busqueda = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input[type='search']")
                )
            )
            campo_busqueda.clear()
            campo_busqueda.send_keys(termino)
            campo_busqueda.send_keys(Keys.ENTER)
            time.sleep(5)
            aceptar_cookies(driver, WebDriverWait(driver, 3))

            total_inicial = obtener_total_resultados(driver)

            selector_orden = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "select.fx-input-select-simple__field")
                )
            )
            Select(selector_orden).select_by_value("pra")
            time.sleep(5)

            # Carga todo el listado primero para conocer cantidad y orden.
            cargar_todos_los_productos(driver)
            tarjetas = extraer_tarjetas_listado(driver)

            if not tarjetas:
                raise ValueError(
                    f"{termino}: no se encontraron tarjetas. "
                    "Se detiene la ejecución."
                )

            total_anunciado = obtener_total_resultados(driver)
            print(
                f"INICIO DE EXTRACCIÓN: {termino} | "
                f"tarjetas={len(tarjetas)} | "
                f"total anunciado={total_anunciado or 'desconocido'} | "
                f"total inicial={total_inicial or 'desconocido'}"
            )

            # Inventario completo que ofrece la página hoy: incluye agotados
            # y excluidos (marca/precio/tipo), que también son tarjetas del
            # listado. Con esto el monitor reconcilia la base al cierre.
            skus_en_pagina = {t["sku_listado"] for t in tarjetas}
            skus_agotados = {
                t["sku_listado"] for t in tarjetas if t["agotado"]
            }
            skus_retirados = set()

            # Solo se reconcilia si el listado cargó completo: con un caso
            # 254/257 la lista no es autoritativa y borrar sería un error.
            listado_completo = (
                total_anunciado > 0 and len(tarjetas) >= total_anunciado
            )

            # Estado actual en base para este alcance: permite saltarse la
            # ficha de los productos que ya están completos.
            existentes = {}
            if obtener_existentes:
                existentes = obtener_existentes(alcance) or {}
                print(
                    f"BASE DE DATOS: {len(existentes)} SKU registrados "
                    f"para este alcance."
                )

            # Caché de exclusiones: SKU que ya se abrieron antes y
            # resultaron retirados o de otra familia. Su ficha no se
            # vuelve a abrir, en esta búsqueda ni en las siguientes.
            cache_exclusiones = {}
            if obtener_exclusiones:
                recibido = obtener_exclusiones()
                if not isinstance(recibido, dict):
                    raise ValueError(
                        "obtener_exclusiones debe devolver un diccionario."
                    )
                cache_exclusiones = dict(recibido)
                if cache_exclusiones:
                    print(
                        f"CACHÉ DE EXCLUSIONES: {len(cache_exclusiones)} "
                        "SKU se omitirán sin abrir ficha."
                    )

            lote = []
            lote_precios = []
            numero_lote = 0
            numero_lote_precios = 0
            cantidad_validos = 0
            sin_cambios = 0
            precios_actualizados = 0
            errores = []
            retirados = 0
            agotados = 0
            excluidos_precio = 0
            excluidos_tipo = 0
            urls_vistas = set()
            omitidos_cache = {"retirado": 0, "tipo": 0}

            for indice, ficha in enumerate(tarjetas, start=1):
                print(
                    f"\nPROGRESO {termino}: "
                    f"tarjeta {indice}/{len(tarjetas)}"
                )

                if ficha["agotado"]:
                    agotados += 1
                    print(
                        f"AGOTADO, se omite: {ficha['nombre']} | {ficha['url']}"
                    )
                    continue

                if not all(
                    ficha.get(campo)
                    for campo in ("marca", "nombre", "url")
                ):
                    mensaje = f"Tarjeta incompleta: {ficha}"
                    print(f"ERROR: {mensaje}")
                    errores.append(mensaje)
                    continue

                if normalizar(ficha["marca"]) != normalizar(marca_objetivo):
                    print(
                        f"EXCLUIDO POR MARCA: {ficha['marca']} "
                        f"{ficha['nombre']}"
                    )
                    continue

                precio = ficha.get("precio")
                if precio is None or precio <= 0:
                    mensaje = (
                        f"Precio ilegible en {ficha['url']}: "
                        f"{ficha['precio_texto']!r}"
                    )
                    print(f"ERROR: {mensaje}")
                    errores.append(mensaje)
                    continue

                if precio <= PRECIO_MINIMO_EUR:
                    excluidos_precio += 1
                    print(
                        f"EXCLUIDO POR PRECIO (<= {PRECIO_MINIMO_EUR} EUR): "
                        f"{ficha['marca']} {ficha['nombre']} | EUR {precio}"
                    )
                    continue

                # Exclusiones ya confirmadas en otras búsquedas o en
                # ejecuciones anteriores: se omite sin abrir la ficha.
                sku_listado = ficha["sku_listado"]
                exclusion = cache_exclusiones.get(sku_listado)

                if exclusion:
                    razon = exclusion.get("razon")

                    if razon == "retirado":
                        omitidos_cache["retirado"] += 1
                        # La confirmación de retirada es vieja, así que no
                        # se elimina de la base: se trata como agotado para
                        # que la reconciliación lo saque de venta.
                        skus_agotados.add(sku_listado)
                        print(
                            f"RETIRADO (caché), se omite sin abrir ficha: "
                            f"{ficha['nombre']} | {ficha['url']}"
                        )
                        continue

                    if (
                        razon == "tipo"
                        and exclusion.get("familia") != familia_objetivo
                    ):
                        omitidos_cache["tipo"] += 1
                        print(
                            f"EXCLUIDO POR TIPO (caché): "
                            f"{exclusion.get('categoria_etiqueta', '')} | "
                            f"{ficha['nombre']} | {ficha['url']}"
                        )
                        continue

                    # familia == familia_objetivo: el producto sí pertenece
                    # a esta búsqueda; se procesa normalmente.

                # Ya está en base y tiene imágenes: no hace falta abrir la
                # ficha. Solo se actualiza si el precio del listado cambió.
                registro = existentes.get(sku_listado)

                if registro and registro.get("tiene_imagenes"):
                    precio_anterior = registro.get("precio_origen")

                    if (
                        precio_anterior is not None
                        and abs(float(precio_anterior) - precio)
                        <= TOLERANCIA_PRECIO_EUR
                    ):
                        sin_cambios += 1
                        print(
                            f"SIN CAMBIOS, se omite sin abrir ficha: "
                            f"{sku_listado} | EUR {precio}"
                        )
                        continue

                    lote_precios.append({
                        "sku": sku_listado,
                        "precio_origen": precio,
                        "precio_anterior": precio_anterior,
                    })
                    precios_actualizados += 1
                    print(
                        f"PRECIO ACTUALIZADO (sin abrir ficha): "
                        f"{sku_listado} | EUR {precio_anterior} -> {precio}"
                    )

                    if len(lote_precios) >= batch_size:
                        numero_lote_precios += 1
                        emitir_precios(
                            callback_precios,
                            lote_precios,
                            alcance,
                            termino,
                            numero_lote_precios,
                        )
                        lote_precios = []
                    continue

                url = ficha["url"]
                if url in urls_vistas:
                    print(f"URL DUPLICADA, se omite: {url}")
                    continue
                urls_vistas.add(url)

                try:
                    driver.switch_to.new_window("tab")
                    driver.get(url)

                    estado, sku = esperar_producto_o_retirada(driver)
                    if estado == "retirado":
                        retirados += 1
                        skus_retirados.add(sku_listado)
                        if on_excluir:
                            on_excluir(sku_listado, {
                                "razon": "retirado",
                                "nombre": ficha["nombre"],
                                "url": url,
                            })
                        print(f"PRODUCTO RETIRADO, se omite: {url}")
                        continue

                    etiqueta, categoria, familia = obtener_categoria(
                        driver, ficha["nombre"]
                    )
                    if familia != familia_objetivo:
                        excluidos_tipo += 1
                        if on_excluir:
                            on_excluir(sku_listado, {
                                "razon": "tipo",
                                "familia": familia,
                                "categoria": categoria,
                                "categoria_etiqueta": etiqueta,
                                "nombre": ficha["nombre"],
                                "url": url,
                            })
                        print(
                            f"EXCLUIDO POR TIPO: {etiqueta} | "
                            f"{ficha['nombre']} | {url}"
                        )
                        continue

                    disponibilidad = obtener_disponibilidad(driver)
                    detalles = WebDriverWait(driver, 20).until(
                        lambda navegador: obtener_product_details(navegador),
                        message=f"SKU {sku}: descripción vacía.",
                    )

                    galeria = obtener_galeria_hd(driver)

                    if not galeria:
                        for imagen in driver.find_elements(
                            By.CSS_SELECTOR,
                            "img[itemprop='image']",
                        ):
                            src = imagen.get_attribute("src")
                            if (
                                src
                                and "static-thomann.de" in src
                                and "/pics/prod/" in src
                                and src not in galeria
                            ):
                                galeria.append(src)

                    if not galeria:
                        galeria = obtener_galeria_producto(driver)

                    if not galeria:
                        raise ValueError(f"SKU {sku}: no se extrajo galería.")

                    nombre = (
                        ficha["nombre"]
                        .replace("B-Stock", "")
                        .replace("B‑Stock", "")
                        .strip()
                    )
                    nombre_completo = f"{marca_objetivo} {nombre}"

                    producto = {
                        "id": nombre_completo.upper(),
                        "sku": str(sku),
                        "marca": marca_objetivo,
                        "categoria": categoria,
                        "categoria_etiqueta": etiqueta,
                        "alcance_scraping": alcance,
                        "nombre": nombre_completo,
                        "precio": precio,
                        "precio_origen": precio,
                        "disponibilidad_texto": disponibilidad,
                        "url": url,
                        "imagen": galeria[0],
                        "gallery": list(dict.fromkeys(galeria)),
                        "descripcion": "\n".join(detalles),
                        "productDetails": detalles,
                        "es_bstock": "b_stock" in url.lower(),
                    }

                    sku_producto = str(sku)
                    anterior = productos_unicos.get(sku_producto)
                    if anterior and anterior != producto:
                        raise ValueError(
                            f"SKU {sku_producto} repetido con datos distintos."
                        )

                    productos_unicos[sku_producto] = producto
                    lote.append(producto)
                    cantidad_validos += 1

                    print(
                        f"SKU VALIDADO {sku_producto} | {marca_objetivo} | "
                        f"{categoria} | EUR {precio} | "
                        f"válidos en búsqueda={cantidad_validos}"
                    )

                except Exception as exc:
                    mensaje = f"{url} | {type(exc).__name__}: {exc}"
                    print(f"ERROR PRODUCTO: {mensaje}")
                    errores.append(mensaje)

                finally:
                    cerrar_pestanas_producto(driver, ventana_principal)

                # La entrega queda fuera del try de extracción para que
                # un fallo del callback no se confunda con error de producto.
                if len(lote) >= batch_size:
                    numero_lote += 1
                    emitir_lote(
                        callback,
                        lote,
                        alcance,
                        termino,
                        numero_lote,
                    )
                    lote = []

            if lote:
                numero_lote += 1
                emitir_lote(
                    callback,
                    lote,
                    alcance,
                    termino,
                    numero_lote,
                )
                lote = []

            if lote_precios:
                numero_lote_precios += 1
                emitir_precios(
                    callback_precios,
                    lote_precios,
                    alcance,
                    termino,
                    numero_lote_precios,
                )
                lote_precios = []

            if errores:
                print(
                    f"ADVERTENCIA {termino}: {len(errores)} "
                    "productos tuvieron errores de extracción."
                )
                for mensaje in errores:
                    print(f"  - {mensaje}")

                if len(errores) > MAX_ERRORES_POR_BUSQUEDA:
                    raise ValueError(
                        f"{termino}: {len(errores)} errores, supera el límite "
                        f"de {MAX_ERRORES_POR_BUSQUEDA}. Se detiene la ejecución."
                    )

            # Una búsqueda puede terminar sin productos nuevos porque todo
            # estaba ya en base: eso es un éxito, no un fallo.
            if (
                cantidad_validos == 0
                and precios_actualizados == 0
                and sin_cambios == 0
            ):
                raise ValueError(
                    f"{termino}: no se obtuvo ningún producto válido. "
                    "Se detiene la ejecución."
                )

            # Cierre de la búsqueda: el listado ya está completamente
            # cargado, así que esta es la lista autoritativa de SKUs
            # vigentes (se restan los retirados confirmados en su ficha).
            if on_fin_alcance:
                on_fin_alcance(
                    alcance,
                    skus_en_pagina - skus_retirados,
                    skus_agotados,
                    listado_completo,
                )

            print(
                f"\nBÚSQUEDA TERMINADA: {termino} | "
                f"productos válidos={cantidad_validos} | "
                f"lotes entregados={numero_lote} | "
                f"sin cambios={sin_cambios} | "
                f"precios actualizados={precios_actualizados} | "
                f"retirados omitidos={retirados} | "
                f"agotados omitidos={agotados} | "
                f"excluidos por precio={excluidos_precio} | "
                f"excluidos por tipo={excluidos_tipo} | "
                f"omitidos por caché (retirado/tipo)="
                f"{omitidos_cache['retirado']}/{omitidos_cache['tipo']} | "
                f"skus en listado={len(skus_en_pagina)} | "
                f"listado completo={'sí' if listado_completo else 'NO'}"
            )

        print(
            f"\nTOTAL DE SKU ÚNICOS VALIDADOS: {len(productos_unicos)}"
        )
        return list(productos_unicos.values())

    finally:
        driver.quit()


if __name__ == "__main__":
    # Ejecución de prueba: imprime cada lote y no escribe en Supabase.
    scrape(batch_size=20)