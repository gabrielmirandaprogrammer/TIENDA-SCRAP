import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import { supabase } from "../services/supabase";
import "./css/ProductDetails.css";

function formatearPrecio(precio, moneda) {
  if (precio === null || precio === undefined || precio === "") {
    return "Precio no disponible";
  }

  const valor = Number(precio);

  if (!Number.isFinite(valor)) {
    return "Precio no disponible";
  }

  const codigoMoneda = moneda?.trim().toUpperCase();

  if (!codigoMoneda) {
    return new Intl.NumberFormat("es-CO").format(valor);
  }

  try {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: codigoMoneda,
    }).format(valor);
  } catch {
    return `${new Intl.NumberFormat("es-CO").format(valor)} ${codigoMoneda}`;
  }
}

function ProductDetails() {
  const { id } = useParams();

  const [producto, setProducto] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [imagenFallida, setImagenFallida] = useState(false);
  const [ampliada, setAmpliada] = useState(false);

  useEffect(() => {
    let activo = true;

    async function cargarProducto() {
      setCargando(true);
      setProducto(null);
      setError("");
      setImagenFallida(false);
      setAmpliada(false);

      try {
        const { data, error: errorConsulta } = await supabase
          .from("productos")
          .select(
            "id, nombre, descripcion, precio, moneda, stock, imagen_principal, sku"
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

  const stockConocido =
    producto?.stock !== null &&
    producto?.stock !== undefined &&
    producto?.stock !== "" &&
    Number.isFinite(Number(producto?.stock));

  const disponible = stockConocido && Number(producto.stock) > 0;

  const disponibilidad = !stockConocido
    ? "Disponibilidad por confirmar"
    : disponible
      ? "Stock disponible"
      : "Sin existencias";

  const tieneImagen = Boolean(
    producto?.imagen_principal && !imagenFallida
  );

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
              {/* IZQUIERDA: IMAGEN */}
              <section
                className="detalle-galeria"
                aria-label="Imagen del producto"
              >
                <div className="detalle-galeria-cabecera">
                  <span className="detalle-label">
                    Imagen del producto
                  </span>

                  {tieneImagen && <span>1 imagen</span>}
                </div>

                {tieneImagen ? (
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
                        src={producto.imagen_principal}
                        alt={producto.nombre}
                        onError={() => setImagenFallida(true)}
                      />
                    </button>

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
                    {formatearPrecio(producto.precio, producto.moneda)}
                  </p>

                  {producto.moneda && (
                    <p className="detalle-moneda">
                      Precio expresado en {producto.moneda}
                    </p>
                  )}
                </div>

                <div className="detalle-disponibilidad">
                  <p
                    className={`detalle-stock ${
                      disponible ? "con-stock" : ""
                    }`}
                  >
                    <span aria-hidden="true" />
                    {disponibilidad}
                  </p>

                  {disponible && (
                    <p className="detalle-stock-cantidad">
                      {producto.stock}{" "}
                      {Number(producto.stock) === 1
                        ? "unidad disponible"
                        : "unidades disponibles"}
                    </p>
                  )}
                </div>

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
                      <dd>Por confirmar</dd>
                    </div>

                    <div>
                      <dt>Envío y entrega</dt>
                      <dd>Por confirmar</dd>
                    </div>

                    <div>
                      <dt>Garantía</dt>
                      <dd>No especificada</dd>
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

                  {producto.moneda && (
                    <div>
                      <dt>Moneda</dt>
                      <dd>{producto.moneda}</dd>
                    </div>
                  )}
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
    </>
  );
}

export default ProductDetails;