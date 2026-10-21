from selenium import webdriver
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

import unicodedata
import time
import json
import re


MAX_ERRORES_POR_BUSQUEDA = 10

# Precio mínimo en EUR de origen para aceptar un producto.
# "Más de 100": lo que cuesta 100 o menos se excluye (así se filtran
# accesorios) sin abrir su ficha, y quedará fuera del inventario.
PRECIO_MINIMO_EUR = 100

# Frases de la página de "producto retirado", ya normalizadas (sin tildes).
MENSAJES_RETIRADO = (
    'ya no se encuentra en nuestro catalogo',
    'no dude en visitar alternativamente la pagina de categoria',
)

# Configuración de las siete búsquedas. No contiene credenciales.
BUSQUEDAS = (
    ("marcus miller", "Marcus Miller", "bajo"),
    ("ibanez guitar", "Ibanez", "guitarra"),
    ("ibanez bass", "Ibanez", "bajo"),
    ("sadowsky bass", "Sadowsky", "bajo"),
    ("warwick bass", "Warwick", "bajo"),
)


def normalizar(texto):
    return " ".join(
        "".join(c for c in unicodedata.normalize("NFKD", texto)
                if not unicodedata.combining(c)).casefold().split()
    )


def alcance_busqueda(termino):
    # Mantener exactamente el alcance anterior para reconciliar Marcus Miller.
    if normalizar(termino) == "marcus miller":
        return "busqueda:marcus miller|filtro:marcus-miller|v1"
    return f"busqueda:{normalizar(termino)}|v1"


# Reglas de clasificación del H2, evaluadas en orden sobre el texto
# normalizado (minúsculas y sin tildes) y ancladas al inicio del texto.
# "familia" es "guitarra", "bajo" o "accesorio": lo accesorio y lo fuera de
# alcance se reconoce para excluirlo sin contarlo como error de extracción.
REGLAS_ETIQUETA = tuple(
    (re.compile(patron), categoria, familia)
    for patron, categoria, familia in (
        # Encordados y cuerdas sueltas.
        (r"encordados?\b|strings?\b|string\s+sets?\b|cuerdas\b",
         "Encordados", "accesorio"),
        # "Guitar case", "Bass stand", etc.: H2 en inglés que empieza con el
        # instrumento pero es un accesorio; va antes de las reglas de
        # instrumentos para que no se cuelen como guitarra o bajo.
        (r"guitars?\s+(?:cases?|stands?|straps?|cables?|covers?|cloths?|"
         r"strings?|picks?)\b|"
         r"bass\s+(?:cases?|stands?|straps?|cables?|covers?|cloths?|strings?)\b",
         "Accesorios", "accesorio"),
        # Amplis, combos, pedales y efectos (incluye el typo "Effetc" de Thomann).
        (r"amplificadores?\b|amplis?\b|(?:guitar|bass)\s+amps?\b|combos?\b|"
         r"pedales?\b|pedalboards?\b|pedals?\b|efectos?\b|effects?\b|effetcs?\b|"
         r"multi\s+effects?\b",
         "Accesorios", "accesorio"),
        # Fundas, estuches, soportes y accesorios de manejo.
        (r"fundas?\b|gig\s?bags?\b|bolsas?\b|estuches?\b|caja\s+rigida\b|"
         r"cases?\b|cables?\b|correas?\b|straps?\b|"
         r"soportes?\b|stands?\b|afinadores?\b|tuners?\b|pastillas?\b|pickups?\b|"
         r"pin\s+pullers?\b|cloths?\b|polishing\b|pick\s+sets?\b|thrones?\b",
         "Accesorios", "accesorio"),
        # Packs y bundles.
        (r"packs?\b|bundles?\b",
         "Packs", "accesorio"),
        # Partes y repuestos.
        (r"sistema\s+de\s+tremolo\b|tremolos?\b|puentes?\b|bridges?\b|"
         r"clavijeros?\b",
         "Partes y otros", "accesorio"),
        # Otros instrumentos fuera de alcance.
        (r"ukuleles?\b|ukeleles?\b|banjos?\b|mandolinas?\b|mandolins?\b|"
         r"armonicas?\b|harmonicas?\b|guitarra\s+piccolo\b|piccolo\s+guitars?\b",
         "Otros instrumentos", "accesorio"),
        # Bajo acústico: reconocido, pero sin categoría propia en Supabase;
        # queda fuera del alcance igual que los accesorios.
        (r"bajo\s+acusticos?\b|"
         r"(?:electro[-\s]?)?acoustic\s+bass(?:\s+guitars?)?\b",
         "Bajos Acústicos", "accesorio"),
        # Bajos eléctricos (ES + EN); "Bajo" a secas también es un bajo eléctrico.
        (r"bajo\s+electrico\b|bajo\s+de\s+[4-9]\s+cuerdas\b|"
         r"bajo\s+[4-9]\s+cuerdas\b|bajos?\b",
         "Bajos Eléctricos", "bajo"),
        (r"(?:electric\s+)?bass(?:\s+guitars?)?\b|"
         r"[4-9][-\s]?strings?\s+(?:electric\s+)?bass\b|e[-\s]?bass\b",
         "Bajos Eléctricos", "bajo"),
        # Guitarras eléctricas (ES + EN); admite el H2 recortado
        # "Guitarra eléctric".
        (r"guitarra\s+electric[ao]s?\b",
         "Guitarras Eléctricas", "guitarra"),
        (r"(?:[4-9][-\s]?strings?\s+)?(?:electric\s+)?guitars?\b|"
         r"e[-\s]?guitars?\b",
         "Guitarras Eléctricas", "guitarra"),
        # Guitarras acústicas, electroacústicas, clásicas y de concierto
        # (ES + EN). "Guitarra de concierto" es el H2 de las de nylon
        # (Ibanez FRH/GA/TOD); si no se quieren vender, cambiar su familia
        # a "accesorio".
        (r"guitarra\s+(?:electroacustica|acustica)\b|"
         r"guitarra\s+(?:clasica|espanola|criolla)\b|"
         r"guitarra\s+de\s+concierto\b",
         "Guitarras Acústicas", "guitarra"),
        (r"(?:electro[-\s]?)?acoustic(?:[-\s]?electric)?\s+guitars?\b|"
         r"classical\s+guitars?\b|concert\s+guitars?\b",
         "Guitarras Acústicas", "guitarra"),
    )
)


def clasificar_etiqueta(etiqueta):
    """Reglas explícitas en español e inglés; no asignar categoría por nombre comercial."""
    texto = normalizar(etiqueta)
    for patron, categoria, familia in REGLAS_ETIQUETA:
        if patron.match(texto):
            return categoria, familia
    return None


def obtener_categoria(driver):
    selector = "h2.fx-headline.fx-headline--3.fx-space-bottom--m"
    elementos = WebDriverWait(driver, 20).until(
        lambda d: [e for e in d.find_elements(By.CSS_SELECTOR, selector)
                   if e.is_displayed() and e.text.strip()],
        message="No apareció la etiqueta H2 del producto.",
    )
    etiquetas = list(dict.fromkeys(e.text.strip() for e in elementos))
    clasificaciones = [(e, clasificar_etiqueta(e)) for e in etiquetas]
    instrumentos = [(e, valor) for e, valor in clasificaciones
                    if valor and valor[1] in ("guitarra", "bajo")]
    accesorios = [(e, valor) for e, valor in clasificaciones
                  if valor and valor[1] == "accesorio"]
    if instrumentos:
        # Un H2 accesorio (p.ej. "Encordado") en la misma página del producto
        # no invalida al H2 del instrumento; dos instrumentos distintos sí
        # impiden clasificar con certeza.
        if len({valor[0] for _, valor in instrumentos}) > 1:
            return " / ".join(etiquetas), "Sin Categoría", "accesorio"
        etiqueta, (categoria, familia) = instrumentos[0]
        return etiqueta, categoria, familia
    if accesorios:
        # Página de accesorio u otro producto fuera de alcance: se devuelve
        # tal cual y el filtro de familia del bucle lo excluye.
        etiqueta, (categoria, familia) = accesorios[0]
        return etiqueta, categoria, familia
    # H2 sin ninguna regla (bundles, productos raros): fuera de alcance, sin
    # error; el filtro de familia del bucle lo excluye y queda fuera de
    # Supabase hasta que se le cree una regla.
    return " / ".join(etiquetas), "Sin Categoría", "accesorio"


def aceptar_cookies(driver, wait):

    try:

        btn = wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "button.js-accept-all-cookies"
                )
            )
        )

        driver.execute_script(
            "arguments[0].click();",
            btn
        )

    except:
        pass


def obtener_total_resultados(driver):

    try:

        total = driver.find_element(
            By.CSS_SELECTOR,
            "[data-track-id='resultCountContainer']"
        ).text.strip()

        total = int(
            total.replace(".", "")
        )

        return total

    except Exception as e:

        print(
            f"Error obteniendo total: {e}"
        )

        return 0


def limpiar_precio(texto):

    texto = texto.replace("€", "")
    texto = texto.replace("$", "")
    texto = texto.replace(" ", "")
    texto = texto.replace("\u00a0", "")
    texto = texto.replace(".", "")
    texto = texto.replace(",", ".")

    try:
        return float(texto)

    except:
        return 0


def extraer_tarjetas_listado(driver):
    from urllib.parse import urljoin

    selector_tarjetas = (
        "div.fx-product-list-entry"
        "[data-track-id='product']"
        "[data-product-id]"
    )

    elementos = driver.find_elements(By.CSS_SELECTOR, selector_tarjetas)
    print(f"Tarjetas de producto encontradas: {len(elementos)}")

    productos = []
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

            marca = texto_de(".title__manufacturer")
            nombre = texto_de(".title__name")
            texto_tarjeta = elemento.text

            precio_texto = ""
            precio_eur = None
            coincidencia = re.search(
                r"([\d.]+(?:,\d{1,2})?)\s*€",
                texto_tarjeta
            )

            if coincidencia:
                precio_texto = coincidencia.group(0).strip()
                valor_normalizado = (
                    coincidencia.group(1)
                    .replace(".", "")
                    .replace(",", ".")
                )
                precio_eur = float(valor_normalizado)

            enlaces = elemento.find_elements(
                By.CSS_SELECTOR,
                "a.product__content[href], a.product__image[href]"
            )
            href = enlaces[0].get_attribute("href") if enlaces else ""
            url = urljoin(driver.current_url, href) if href else ""

            productos.append({
                "sku": sku,
                "marca": marca,
                "nombre": nombre,
                "precio_eur": precio_eur,
                "precio_texto": precio_texto,
                "url": url,
            })

        except Exception as exc:
            print(
                f"Error leyendo una tarjeta: {type(exc).__name__}: {exc}"
            )

    print(f"Tarjetas extraídas: {len(productos)}")
    if productos:
        print("Primera tarjeta extraída:", productos[0])

    return productos

def obtener_sku(driver):

    try:

        html = driver.page_source

        match = re.search(
            r'"artnr":"(\d+)"',
            html
        )

        if match:
            return match.group(1)

    except:
        pass

    return None


def producto_disponible(driver):
    # innerText reúne el texto aunque esté dividido entre etiquetas.
    # Se compara contra el texto normalizado, sin tildes ni mayúsculas.
    texto = driver.execute_script(
        "return document.body ? document.body.innerText : '';"
    ) or ""
    texto = normalizar(texto)

    return not any(mensaje in texto for mensaje in MENSAJES_RETIRADO)


def esperar_producto_o_retirada(driver):

    def comprobar(navegador):

        if not producto_disponible(navegador):
            return ('retirado', None)

        sku = obtener_sku(navegador)

        if sku:
            return ('producto', sku)

        return False

    return WebDriverWait(driver, 40).until(
        comprobar,
        message='No se pudo confirmar el SKU ni la retirada del catálogo.'
    )


def obtener_galeria_hd(driver):

    gallery = []

    try:

        imagenes = driver.find_elements(
            By.TAG_NAME,
            "img"
        )

        for img in imagenes:

            src = img.get_attribute("src")

            if (
                src
                and "static-thomann.de" in src
                and "padthumb600x600" in src
                and "logos" not in src
                and not src.endswith(".svg")
            ):

                if src not in gallery:

                    gallery.append(src)

        print(
            f"Galeria encontrada: {len(gallery)} imagenes"
        )

        return gallery[:10]

    except Exception as e:

        print(
            f"Error obteniendo galeria: {e}"
        )

        return []


def obtener_galeria_producto(driver):

    # 1. Producto actual.
    gallery = obtener_galeria_hd(driver)

    if gallery:

        print(
            f"GALERIA PRODUCTO ACTUAL: "
            f"{len(gallery)} imagenes"
        )

        return gallery

    # 2. Producto original (para B-Stock y similares).
    try:

        enlaces = driver.find_elements(
            By.CSS_SELECTOR,
            ".seeother a"
        )

        if not enlaces:

            print(
                "No existe producto original"
            )

            return []

        url_original = enlaces[0].get_attribute(
            "href"
        )

        print(
            f"PRODUCTO ORIGINAL -> "
            f"{url_original}"
        )

        ventana_actual = driver.current_window_handle

        try:

            driver.switch_to.new_window("tab")
            driver.get(url_original)

            time.sleep(3)

            gallery = obtener_galeria_hd(
                driver
            )

            print(
                f"GALERIA PRODUCTO ORIGINAL: "
                f"{len(gallery)} imagenes"
            )

            return gallery

        finally:

            if driver.current_window_handle != ventana_actual:
                driver.close()

            driver.switch_to.window(ventana_actual)

    except Exception as e:

        print(
            f"Error galeria: {e}"
        )

        return []


def obtener_disponibilidad(driver):
    """Lee el texto de disponibilidad visible en la ficha del producto."""
    def leer_disponibilidad(navegador):
        textos = {
            " ".join(elemento.text.split())
            for elemento in navegador.find_elements(By.TAG_NAME, "span")
            if elemento.is_displayed()
            and elemento.text.strip()
            and (
                elemento.text.strip() == "En stock"
                or elemento.text.strip().startswith("Disponible dentro de")
            )
        }

        if len(textos) > 1:
            raise ValueError(
                f"Disponibilidad ambigua: {sorted(textos)}"
            )

        return next(iter(textos), False)

    return WebDriverWait(driver, 20).until(
        leer_disponibilidad,
        message="No apareció el texto de disponibilidad en la ficha."
    )

def obtener_product_details(driver):

    detalles = []

    try:

        # CASO 1: Lista UL
        items = driver.find_elements(
            By.CSS_SELECTOR,
            "ul.product-text__list li .list-item__text"
        )

        if items:

            for item in items:

                texto = item.text.strip()

                if texto:
                    detalles.append(texto)

            return detalles

        # CASO 2: Párrafo único
        parrafo = driver.find_element(
            By.CSS_SELECTOR,
            "p.product-text__description"
        )

        texto = parrafo.text.strip()

        if not texto:
            return []

        texto = re.sub(
            r"^B-Stock,\s*",
            "",
            texto,
            flags=re.IGNORECASE
        )

        detalles = [
            p.strip()
            for p in texto.split(",")
            if p.strip()
        ]

    except Exception as e:

        print(
            f"Error obteniendo detalles: {e}"
        )

    return detalles


def cargar_todos_los_productos(driver):
    selector_productos = "div.fx-product-list-entry"
    selector_boton = "button.search-pagination__show-more"

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
            botones = driver.find_elements(By.CSS_SELECTOR, selector_boton)

            print(
                f"PAGINACION SIN AVANCE: intento {fallos_sin_avance}/3 | "
                f"tarjetas={cantidad_final} | "
                f"total={total_final} | "
                f"botones encontrados={len(botones)} | "
                f"{type(e).__name__}: {e}"
            )

            if fallos_sin_avance >= 3:
                if cantidad_final <= 0:
                    raise ValueError(
                        "El listado quedó vacío durante la carga."
                    ) from e

                if cantidad_final < cantidad_actual:
                    raise ValueError(
                        "El listado perdió tarjetas durante la paginación."
                    ) from e

                print(
                    "ADVERTENCIA: carga detenida tras 3 intentos sin avance. "
                    f"Tarjetas={cantidad_final}, "
                    f"total anunciado={total_final}. "
                    "Se continúa con las tarjetas obtenidas; "
                    "no se garantiza que el catálogo esté completo."
                )
                return

def scrape():
    """Extrae las siete búsquedas sin escribir archivos ni acceder a Supabase."""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=es-CO")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    productos_unicos = {}
    try:
        principal = driver.current_window_handle
        for termino, marca_objetivo, familia_objetivo in BUSQUEDAS:
            alcance = alcance_busqueda(termino)
            print(f"\nBUSQUEDA: {termino} | ALCANCE: {alcance}")
            driver.get("https://www.thomann.es/")
            aceptar_cookies(driver, WebDriverWait(driver, 3))
            wait = WebDriverWait(driver, 40)
            search = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input[type='search']")
            ))
            search.clear()
            search.send_keys(termino)
            search.send_keys(Keys.ENTER)
            time.sleep(5)
            aceptar_cookies(driver, WebDriverWait(driver, 3))
            total_inicial = obtener_total_resultados(driver)
            order = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "select.fx-input-select-simple__field")
            ))
            Select(order).select_by_value("pra")
            time.sleep(5)
            cargar_todos_los_productos(driver)
            tarjetas = driver.execute_script("""
                return Array.from(document.querySelectorAll('div.fx-product-list-entry'))
                .map(p => {
                    const leer = s => {
                    const e = p.querySelector(s);
                    if (!e) throw new Error('Tarjeta incompleta: ' + s);
                    return e;
                    };
                    return {
                    marca: leer('span.title__manufacturer').innerText.trim(),
                    nombre: leer('span.title__name').innerText.trim(),
                    precio: leer('div.product__price-primary').innerText.trim(),
                    url: leer('a.product__image').href,
                    agotado: /el producto est(a|á) agotado/i.test(p.innerText || '')
                    };
                });
            """)

            # Los agotados del listado no se visitan: de ahí no se extrae nada.
            agotados = [t for t in tarjetas if t.get("agotado")]
            tarjetas = [t for t in tarjetas if not t.get("agotado")]
            if agotados:
                print(f"AGOTADOS OMITIDOS ({termino}): {len(agotados)}")
                for tarjeta_agotada in agotados:
                    print(f"  - {tarjeta_agotada['nombre']} | {tarjeta_agotada['url']}")
            total_tarjetas = len(tarjetas) + len(agotados)

            if not tarjetas:
                if agotados:
                    raise ValueError(
                    f"{termino}: los {len(agotados)} productos del listado están "
                    "agotados; se bloquea la ejecución para no vaciar el alcance."
                    )
                raise ValueError(f"{termino}: listado vacío; se bloquea la ejecución.")
            total_final = obtener_total_resultados(driver)
            if total_inicial != total_tarjetas or total_final != total_tarjetas:
                print(f"ADVERTENCIA CONTADOR: inicial={total_inicial}, "
                    f"final={total_final}, tarjetas={total_tarjetas}. Se continúa.")

            cantidad = 0
            errores = []
            retirados = []
            excluidos_precio = 0
            excluidos_tipo = 0
            urls_vistas = set()
            for ficha in tarjetas:
                try:
                    if not all(ficha.get(k) for k in ("marca", "nombre", "precio", "url")):
                        raise ValueError(f"Tarjeta incompleta: {ficha}")

                    if normalizar(ficha["marca"]) != normalizar(marca_objetivo):
                        print(f"EXCLUIDO POR MARCA: {ficha['marca']} {ficha['nombre']}")
                        continue

                    # Filtro de precio mínimo antes de abrir la ficha.
                    precio = limpiar_precio(ficha["precio"])
                    if precio <= 0:
                        raise ValueError(
                            f"Precio ilegible en la tarjeta: {ficha['precio']!r}"
                        )
                    if precio <= PRECIO_MINIMO_EUR:
                        print(
                            f"EXCLUIDO POR PRECIO (<= {PRECIO_MINIMO_EUR} EUR): "
                            f"{ficha['marca']} {ficha['nombre']} | EUR {precio}"
                        )
                        excluidos_precio += 1
                        continue

                    url = ficha["url"]
                    if url in urls_vistas:
                        continue
                    urls_vistas.add(url)
                    driver.switch_to.new_window("tab")
                    driver.get(url)
                    estado, sku = esperar_producto_o_retirada(driver)
                    if estado == "retirado":
                        print(f"PRODUCTO RETIRADO (se omite): {url}")
                        retirados.append(url)
                        continue

                    etiqueta, categoria, familia = obtener_categoria(driver)
                    if familia != familia_objetivo:
                        print(f"EXCLUIDO POR TIPO: {etiqueta} | {url}")
                        excluidos_tipo += 1
                        continue

                    disponibilidad = obtener_disponibilidad(driver)
                    detalles = WebDriverWait(driver, 20).until(
                        lambda d: obtener_product_details(d),
                        message=f"SKU {sku}: descripción vacía.",
                    )
                    galeria = obtener_galeria_hd(driver)
                    if not galeria:
                        for img in driver.find_elements(
                            By.CSS_SELECTOR, "img[itemprop='image']"
                        ):
                            src = img.get_attribute("src")
                            if src and "static-thomann.de" in src and "/pics/prod/" in src:
                                galeria.append(src)
                    if not galeria:
                        galeria = obtener_galeria_producto(driver)
                    if not galeria:
                        raise ValueError(f"SKU {sku}: no se extrajo galería.")

                    nombre = ficha["nombre"].replace("B-Stock", "").replace("B‑Stock", "").strip()
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
                    anterior = productos_unicos.get(str(sku))
                    if anterior and anterior != producto:
                        raise ValueError(
                            f"SKU {sku}: repetido con datos o alcance distintos."
                        )
                    productos_unicos[str(sku)] = producto
                    cantidad += 1
                    print(f"SKU {sku} | {marca_objetivo} | {categoria} | EUR {precio}")
                except Exception as exc:
                    mensaje = f"{ficha.get('url')} | {type(exc).__name__}: {exc}"
                    print(f"ERROR PRODUCTO: {mensaje}")
                    errores.append(mensaje)
                finally:
                    # Cerrar también las pestañas auxiliares del producto original.
                    for ventana in list(driver.window_handles):
                        if ventana != principal:
                            driver.switch_to.window(ventana)
                            driver.close()
                    driver.switch_to.window(principal)
            if retirados:
                print(f"RETIRADOS OMITIDOS ({termino}): {len(retirados)} "
                    "(se eliminarán de Supabase como ausentes):")
                for url_retirada in retirados:
                    print(f"  - {url_retirada}")
            if excluidos_precio:
                print(f"EXCLUIDOS POR PRECIO ({termino}): {excluidos_precio} productos "
                    f"<= {PRECIO_MINIMO_EUR} EUR (se eliminarán de Supabase como ausentes)")
            if excluidos_tipo:
                print(f"EXCLUIDOS POR TIPO ({termino}): {excluidos_tipo} productos fuera de "
                    "alcance o sin categoría (se eliminarán de Supabase como ausentes)")
            if errores:
                print(f"ADVERTENCIA {termino}: se omitieron {len(errores)} "
                    "productos con error de extracción (se eliminarán de Supabase):")
                for mensaje in errores:
                    print(f"  - {mensaje}")
                # Protección: si fallan demasiados, probablemente la página no cargó bien.
                if len(errores) > MAX_ERRORES_POR_BUSQUEDA:
                    raise ValueError(
                    f"{termino}: {len(errores)} errores de extracción, supera el "
                    f"límite de {MAX_ERRORES_POR_BUSQUEDA}. No se sincronizará."
                    )
            if cantidad == 0:
                raise ValueError(
                    f"{termino}: ningún producto válido "
                    f"({excluidos_precio} excluidos por precio, {excluidos_tipo} por tipo). "
                    "No se permite vaciar un alcance por esta ejecución."
                )
            print(f"BUSQUEDA TERMINADA: {termino} | {cantidad} productos | "
                  f"{len(retirados)} retirados | {len(agotados)} agotados | "
                  f"{excluidos_precio} excluidos por precio | "
                  f"{excluidos_tipo} excluidos por tipo")
        datos = sorted(productos_unicos.values(), key=lambda p: (p["alcance_scraping"], p["precio"]))
        print(f"TOTAL EXTRAIDO: {len(datos)} SKU únicos")
        return datos
    finally:
        driver.quit()


# Sobrescribe el flujo anterior con una prueba de consola segura.
def extraer_tarjetas_listado(driver):
    from urllib.parse import urljoin

    selector_tarjetas = (
        "div.fx-product-list-entry"
        "[data-track-id='product']"
        "[data-product-id]"
    )

    elementos = driver.find_elements(By.CSS_SELECTOR, selector_tarjetas)
    print(f"Tarjetas de producto encontradas: {len(elementos)}")

    productos = []
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

            marca = texto_de(".title__manufacturer")
            nombre = texto_de(".title__name")
            texto_tarjeta = elemento.text

            precio_texto = ""
            precio_eur = None
            coincidencia = re.search(
                r"([\d.]+(?:,\d{1,2})?)\s*€",
                texto_tarjeta
            )

            if coincidencia:
                precio_texto = coincidencia.group(0).strip()
                valor_normalizado = (
                    coincidencia.group(1)
                    .replace(".", "")
                    .replace(",", ".")
                )
                precio_eur = float(valor_normalizado)

            enlaces = elemento.find_elements(
                By.CSS_SELECTOR,
                "a.product__content[href], a.product__image[href]"
            )
            href = enlaces[0].get_attribute("href") if enlaces else ""
            url = urljoin(driver.current_url, href) if href else ""

            productos.append({
                "sku": sku,
                "marca": marca,
                "nombre": nombre,
                "precio_eur": precio_eur,
                "precio_texto": precio_texto,
                "url": url,
            })

        except Exception as exc:
            print(
                f"Error leyendo una tarjeta: {type(exc).__name__}: {exc}"
            )

    print(f"Tarjetas extraídas: {len(productos)}")
    if productos:
        print("Primera tarjeta extraída:", productos[0])

    return productos

if __name__ == "__main__":
    scrape()