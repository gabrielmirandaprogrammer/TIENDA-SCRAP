import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import { supabase } from "../services/supabase";
import { agregarProducto } from "../services/carrito";
import "./css/ProductDetails.css";
import Footer from "../components/Footer";

// El precio guardado en la base siempre está en COP (calculado por
// calcular_precio_cop con la tasa y el margen), así que se formatea
// directamente en pesos sin depender de la columna moneda.
function formatearPrecioCOP(precio) {
  if (precio === null || precio === undefined || precio === "") {
    return "Precio no disponible";
  }

  const valor = Number(precio);

  if (!Number.isFinite(valor)) {
    return "Precio no disponible";
  }

  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(valor);
}

function ProductDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [producto, setProducto] = useState(null);
  const [imagenes, setImagenes] = useState([]);
  const [indice, setIndice] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [ampliada, setAmpliada] = useState(false);
  const [avisoCarrito, setAvisoCarrito] = useState("");
  const avisoTimer = useRef(0);

  useEffect(() => {
    let activo = true;

    async function cargarProducto() {
      setCargando(true);
      setProducto(null);
      setImagenes([]);
      setIndice(0);
      setError("");
      setAmpliada(false);
      setAvisoCarrito("");

      try {
        const { data, error: errorConsulta } = await supabase
          .from("productos")
          .select(
            "id, nombre, descripcion, precio, precio_origen, stock, imagen_principal, sku, disponible_origen"
          )
          .eq("id", id)
          .maybeSingle();

        if (!activo) return;

        if (errorConsulta) throw errorConsulta;

        if (!data) {
          setError("Este producto no existe o no está disponible.");
          return;
        }

        setProducto(data);

        // La galería completa vive en producto_imagenes: la imagen
        // principal va primero y el resto conserva el orden del scrape.
        const lista = data.imagen_principal
          ? [data.imagen_principal]
          : [];

        try {
          const { data: filas, error: errorImagenes } = await supabase
            .from("producto_imagenes")
            .select("url")
            .eq("producto_id", data.id)
            .order("id");

          if (errorImagenes) throw errorImagenes;

          for (const fila of filas ?? []) {
            if (fila?.url && !lista.includes(fila.url)) {
              lista.push(fila.url);
            }
          }
        } catch (errorImagenes) {
          // Si falla la galería, se muestra al menos la principal.
          console.error("Error al cargar la galería:", errorImagenes);
        }

        if (!activo) return;

        setImagenes(lista);
      } catch (errorConsulta) {
        if (!activo) return;

        console.error("Error al cargar el producto:", errorConsulta);
        setError("No pudimos cargar el producto. Intenta nuevamente.");
      } finally {
        if (activo) setCargando(false);
      }
    }

    cargarProducto();

    return () => {
      activo = false;
    };
  }, [id]);

  // Limpia el temporizador del aviso al desmontar.
  useEffect(
    () => () => {
      window.clearTimeout(avisoTimer.current);
    },
    []
  );

  // Mantiene el índice de la galería dentro del rango válido.
  useEffect(() => {
    setIndice((actual) => Math.min(actual, Math.max(0, imagenes.length - 1)));
  }, [imagenes.length]);

  // disponible_origen lo mantiene el scraper y la reconciliación:
  // false solo cuando Thomann muestra el producto agotado. El stock
  // no se usa para decidir porque el scraper siempre guarda 0.
  const agotado = Boolean(producto) && producto.disponible_origen === false;

  const stockMayorQueCero =
    producto?.stock !== null &&
    producto?.stock !== undefined &&
    producto?.stock !== "" &&
    Number(producto.stock) > 0;

  const disponibilidad = agotado
    ? "Sin existencias"
    : "Stock disponible";

  // Quita de la galería una imagen cuya URL no cargó.
  const quitarImagen = (indiceInvalido) => {
    setImagenes((actuales) =>
      actuales.filter((_, posicion) => posicion !== indiceInvalido)
    );
  };

  const manejarAgregarCarrito = () => {
    if (!producto) return;

    agregarProducto(producto, 1);
    setAvisoCarrito("Producto agregado al carrito.");

    window.clearTimeout(avisoTimer.current);
    avisoTimer.current = window.setTimeout(
      () => setAvisoCarrito(""),
      4000
    );
  };

  const manejarComprarAhora = () => {
    if (!producto) return;

    agregarProducto(producto, 1);
    navigate("/carrito");
  };

  return (
    <>
      <Navbar />

      <main className="detalle-page">
        <div className="detalle-shell">
          <nav
            className="detalle-breadcrumb"
            aria-label="Ruta de navegación"
          >
            <Link to="/">Inicio</Link>
            <span aria-hidden="true">/</span>
            <span>Detalle del producto</span>
          </nav>

          {cargando ? (
            <div className="detalle-mensaje" role="status">
              Cargando producto...
            </div>
          ) : error ? (
            <div className="detalle-mensaje" role="alert">
              <h1>No pudimos mostrar el producto</h1>
              <p>{error}</p>
              <Link to="/">Volver al inicio</Link>
            </div>
          ) : producto ? (
            <article className="detalle-layout">
              {/* IZQUIERDA: GALERÍA */}
              <section
                className="detalle-galeria"
                aria-label="Imágenes del producto"
              >
                <div className="detalle-galeria-cabecera">
                  <span className="detalle-label">
                    Imágenes del producto
                  </span>

                  {imagenes.length > 0 && (
                    <span>
                      {imagenes.length}{" "}
                      {imagenes.length === 1 ? "imagen" : "imágenes"}
                    </span>
                  )}
                </div>

                {imagenes.length > 0 ? (
                  <>
                    <button
                      type="button"
                      className={`detalle-imagen-boton ${
                        ampliada ? "esta-ampliada" : ""
                      }`}
                      aria-label={
                        ampliada
                          ? "Reducir imagen del producto"
                          : "Ampliar imagen del producto"
                      }
                      aria-pressed={ampliada}
                      onClick={() => setAmpliada((actual) => !actual)}
                    >
                      <img
                        className="detalle-imagen"
                        src={imagenes[indice]}
                        alt={`${producto.nombre} — imagen ${indice + 1} de ${imagenes.length}`}
                        onError={() => quitarImagen(indice)}
                      />
                    </button>

                    {imagenes.length > 1 && (
                      <div
                        className="detalle-miniaturas"
                        aria-label="Miniaturas de la galería"
                      >
                        {imagenes.map((url, posicion) => (
                          <button
                            key={url}
                            type="button"
                            className={`detalle-miniatura ${
                              posicion === indice ? "activa" : ""
                            }`}
                            aria-label={`Ver imagen ${posicion + 1}`}
                            aria-current={posicion === indice}
                            onClick={() => setIndice(posicion)}
                          >
                            <img
                              src={url}
                              alt=""
                              loading="lazy"
                              onError={() => quitarImagen(posicion)}
                            />
                          </button>
                        ))}
                      </div>
                    )}

                    <p className="detalle-imagen-ayuda">
                      {ampliada
                        ? "Haz clic para reducir la imagen."
                        : "Haz clic en la imagen para ampliarla."}
                    </p>
                  </>
                ) : (
                  <div className="detalle-sin-imagen">
                    Imagen no disponible
                  </div>
                )}
              </section>

              {/* DERECHA: PRECIO Y CONDICIONES */}
              <aside
                className="detalle-resumen"
                aria-label="Precio y condiciones del producto"
              >
                <span className="detalle-label">Importa-Ya</span>

                <h1 className="detalle-titulo">
                  {producto.nombre}
                </h1>

                {producto.sku && (
                  <p className="detalle-sku">
                    SKU: {producto.sku}
                  </p>
                )}

                <div className="detalle-precio-bloque">
                  <p className="detalle-precio">
                    {formatearPrecioCOP(producto.precio)}
                  </p>
                </div>

                <div className="detalle-disponibilidad">
                  <p
                    className={`detalle-stock ${
                      agotado ? "" : "con-stock"
                    }`}
                  >
                    <span aria-hidden="true" />
                    {disponibilidad}
                  </p>

                  {stockMayorQueCero && (
                    <p className="detalle-stock-cantidad">
                      {producto.stock}{" "}
                      {Number(producto.stock) === 1
                        ? "unidad disponible"
                        : "unidades disponibles"}
                    </p>
                  )}
                </div>

                {agotado ? (
                  <div className="detalle-acciones">
                    <button
                      type="button"
                      className="detalle-boton detalle-boton-agotado"
                      disabled
                    >
                      Producto agotado
                    </button>
                  </div>
                ) : (
                  <div className="detalle-acciones">
                    <button
                      type="button"
                      className="detalle-boton detalle-boton-primario"
                      onClick={manejarComprarAhora}
                    >
                      Comprar ahora
                    </button>

                    <button
                      type="button"
                      className="detalle-boton detalle-boton-secundario"
                      onClick={manejarAgregarCarrito}
                    >
                      Agregar al carrito
                    </button>
                  </div>
                )}

                {avisoCarrito && (
                  <p className="detalle-aviso-carrito" role="status">
                    {avisoCarrito}
                  </p>
                )}

                <a
                  href="#detalle-caracteristicas"
                  className="detalle-enlace"
                >
                  Ver características del producto
                  <span aria-hidden="true"> ↓</span>
                </a>

                <section className="detalle-condiciones">
                  <h2>Condiciones de compra</h2>

                  <dl className="detalle-condiciones-lista">
                    <div>
                      <dt>Condición del producto</dt>
                      <dd>Producto nuevo</dd>
                    </div>

                    <div>
                      <dt>Envío y entrega</dt>
                      <dd>De 30 a 40 días hábiles</dd>
                    </div>
                  </dl>
                </section>

                <section className="detalle-incluye">
                  <h2>¿Qué incluye?</h2>
                  <p>
                    El contenido del paquete y los accesorios incluidos
                    aún no están especificados.
                  </p>
                </section>
              </aside>

              {/* DEBAJO: CARACTERÍSTICAS */}
              <section
                id="detalle-caracteristicas"
                className="detalle-caracteristicas"
              >
                <span className="detalle-label">
                  Información del producto
                </span>

                <h2>Características principales</h2>

                <dl className="detalle-ficha">
                  <div>
                    <dt>Nombre</dt>
                    <dd>{producto.nombre}</dd>
                  </div>

                  {producto.sku && (
                    <div>
                      <dt>SKU</dt>
                      <dd>{producto.sku}</dd>
                    </div>
                  )}

                  <div>
                    <dt>Disponibilidad</dt>
                    <dd>{disponibilidad}</dd>
                  </div>

                  
                </dl>
              </section>

              {/* DEBAJO: DESCRIPCIÓN */}
              <section className="detalle-descripcion">
                <h2>Descripción</h2>

                <p>
                  {producto.descripcion?.trim() ||
                    "Este producto todavía no tiene una descripción."}
                </p>
              </section>
            </article>
          ) : null}
        </div>
      </main>
      <Footer />
    </>
  );
}

export default ProductDetails;