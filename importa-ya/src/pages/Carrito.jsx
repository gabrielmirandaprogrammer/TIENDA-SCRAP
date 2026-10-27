import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { supabase } from "../services/supabase";
import {
  cambiarCantidad,
  contarArticulos,
  guardarCarrito,
  leerCarrito,
  quitarProducto,
  suscribirseCarrito,
  vaciarCarrito,
} from "../services/carrito";
import "./css/Carrito.css";

function formatearPrecioCOP(precio) {
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

function Carrito() {
  const [items, setItems] = useState(leerCarrito);
  const [sincronizando, setSincronizando] = useState(false);
  const [avisoPago, setAvisoPago] = useState("");

  // Cualquier cambio del carrito (desde el detalle u otra pestaña)
  // actualiza esta página al instante.
  useEffect(() => suscribirseCarrito(setItems), []);

  // Al abrir el carrito, revalida cada ítem contra la base: el scraper
  // actualiza precios y la reconciliación puede agotar productos
  // después de que se agregaron al carrito.
  useEffect(() => {
    let activo = true;

    async function sincronizar() {
      const actuales = leerCarrito();

      if (!actuales.length) {
        return;
      }

      setSincronizando(true);

      try {
        const { data, error: errorConsulta } = await supabase
          .from("productos")
          .select("id, nombre, precio, imagen_principal, disponible_origen")
          .in("id", actuales.map((item) => item.id));

        if (!activo) return;
        if (errorConsulta) throw errorConsulta;

        const filas = new Map(
          (data ?? []).map((fila) => [fila.id, fila])
        );
        let cambio = false;

        const sincronizado = actuales.map((item) => {
          const fila = filas.get(item.id);

          // El producto ya no existe en la base (lo borró la
          // reconciliación): se marca para que el usuario lo quite.
          if (!fila) {
            if (!item.fuera_catalogo) cambio = true;
            return { ...item, fuera_catalogo: true, agotado: false };
          }

          const agotado = fila.disponible_origen === false;
          const imagen =
            typeof fila.imagen_principal === "string"
              ? fila.imagen_principal
              : "";
          const precio = Number(fila.precio);

          if (
            fila.nombre !== item.nombre ||
            precio !== item.precio ||
            imagen !== item.imagen ||
            agotado !== item.agotado ||
            item.fuera_catalogo !== false
          ) {
            cambio = true;
          }

          return {
            ...item,
            nombre: fila.nombre,
            precio,
            imagen,
            agotado,
            fuera_catalogo: false,
          };
        });

        setItems(sincronizado);

        if (cambio) {
          guardarCarrito(sincronizado);
        }
      } catch (errorConsulta) {
        console.error("Error al sincronizar el carrito:", errorConsulta);
      } finally {
        if (activo) setSincronizando(false);
      }
    }

    sincronizar();

    return () => {
      activo = false;
    };
  }, []);

  const disponibles = items.filter(
    (item) => !item.agotado && !item.fuera_catalogo
  );
  const hayBloqueos = disponibles.length !== items.length;
  const total = disponibles.reduce(
    (suma, item) => suma + item.precio * item.cantidad,
    0
  );
  const articulos = contarArticulos(items);

  const manejarPago = () => {
    if (hayBloqueos) {
      setAvisoPago(
        "Quita los productos agotados o no disponibles para continuar."
      );
      return;
    }

    setAvisoPago("El proceso de pago todavía no está configurado.");
  };

  return (
    <>
      <Navbar />

      <main className="carrito-page">
        <div className="carrito-shell">
          <nav className="carrito-breadcrumb" aria-label="Ruta de navegación">
            <Link to="/">Inicio</Link>
            <span aria-hidden="true">/</span>
            <span>Carrito</span>
          </nav>

          {items.length === 0 ? (
            <div className="carrito-vacio">
              <h1>Tu carrito está vacío</h1>
              <p>
                Cuando agregues productos aparecerán aquí.
              </p>
              <Link to="/" className="carrito-boton carrito-boton-primario">
                Ver productos
              </Link>
            </div>
          ) : (
            <div className="carrito-layout">
              <section
                className="carrito-lista"
                aria-label="Productos en el carrito"
              >
                <div className="carrito-cabecera">
                  <h1>Tu carrito</h1>

                  <div className="carrito-cabecera-datos">
                    <span>
                      {articulos}{" "}
                      {articulos === 1 ? "artículo" : "artículos"}
                    </span>

                    {sincronizando && (
                      <span className="carrito-sincronizando">
                        Actualizando precios...
                      </span>
                    )}

                    <button
                      type="button"
                      className="carrito-vaciar"
                      onClick={() => vaciarCarrito()}
                    >
                      Vaciar carrito
                    </button>
                  </div>
                </div>

                <ul className="carrito-items">
                  {items.map((item) => {
                    const bloqueado =
                      item.agotado || item.fuera_catalogo;

                    return (
                      <li
                        key={item.id}
                        className={`carrito-item ${
                          bloqueado ? "esta-bloqueado" : ""
                        }`}
                      >
                        <div className="carrito-item-imagen">
                          {item.imagen ? (
                            <img
                              src={item.imagen}
                              alt={item.nombre}
                              loading="lazy"
                            />
                          ) : (
                            <span>Sin imagen</span>
                          )}
                        </div>

                        <div className="carrito-item-info">
                          <p className="carrito-item-nombre">
                            {item.nombre}
                          </p>

                          <p className="carrito-item-precio">
                            {formatearPrecioCOP(item.precio)} c/u
                          </p>

                          {item.fuera_catalogo && (
                            <p className="carrito-item-alerta">
                              Este producto ya no está en el catálogo.
                            </p>
                          )}

                          {item.agotado && (
                            <p className="carrito-item-alerta">
                              Este producto se agotó en el origen.
                            </p>
                          )}

                          <div className="carrito-item-controles">
                            <button
                              type="button"
                              aria-label="Quitar una unidad"
                              disabled={item.cantidad <= 1}
                              onClick={() =>
                                cambiarCantidad(
                                  item.id,
                                  item.cantidad - 1
                                )
                              }
                            >
                              −
                            </button>

                            <span className="carrito-item-cantidad">
                              {item.cantidad}
                            </span>

                            <button
                              type="button"
                              aria-label="Agregar una unidad"
                              disabled={bloqueado}
                              onClick={() =>
                                cambiarCantidad(
                                  item.id,
                                  item.cantidad + 1
                                )
                              }
                            >
                              +
                            </button>

                            <button
                              type="button"
                              className="carrito-item-quitar"
                              onClick={() => quitarProducto(item.id)}
                            >
                              Quitar
                            </button>
                          </div>
                        </div>

                        <p className="carrito-item-subtotal">
                          {formatearPrecioCOP(item.precio * item.cantidad)}
                        </p>
                      </li>
                    );
                  })}
                </ul>
              </section>

              <aside
                className="carrito-resumen"
                aria-label="Resumen de la compra"
              >
                <h2>Resumen</h2>

                <div className="carrito-resumen-fila">
                  <span>Artículos</span>
                  <span>{articulos}</span>
                </div>

                <div className="carrito-resumen-fila carrito-resumen-total">
                  <span>Total</span>
                  <span>{formatearPrecioCOP(total)}</span>
                </div>

                <p className="carrito-resumen-envio">
                  Envío y entrega: de 30 a 40 días hábiles.
                </p>

                <button
                  type="button"
                  className="carrito-boton carrito-boton-primario"
                  onClick={manejarPago}
                >
                  Finalizar compra
                </button>

                {avisoPago && (
                  <p className="carrito-aviso" role="status">
                    {avisoPago}
                  </p>
                )}
              </aside>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </>
  );
}

export default Carrito;