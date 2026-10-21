import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { supabase } from "../services/supabase";
import "./css/Home.css";
import banner from "../assets/banner.png";

const beneficios = [
  { icono: "🚚", titulo: "Envío gratis", texto: "En tu primera compra" },
  { icono: "🔒", titulo: "Pago seguro", texto: "Tus datos siempre protegidos" },
  { icono: "🎸", titulo: "Marcas originales", texto: "Fender, Yamaha, Ibanez y más" },
  { icono: "🏷️", titulo: "Hasta 60% OFF", texto: "En productos seleccionados" },
];

function Home() {
  const [productos, setProductos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [ordenPrecio, setOrdenPrecio] = useState("original");

  const productosOrdenados = [...productos];
  if (ordenPrecio !== "original") {
    productosOrdenados.sort((a, b) => {
      const precioA = a.precio == null || a.precio === "" ? NaN : Number(a.precio);
      const precioB = b.precio == null || b.precio === "" ? NaN : Number(b.precio);
      if (!Number.isFinite(precioA)) return Number.isFinite(precioB) ? 1 : 0;
      if (!Number.isFinite(precioB)) return -1;
      return ordenPrecio === "asc" ? precioA - precioB : precioB - precioA;
    });
  }

  useEffect(() => {
    async function cargarProductos() {
      const { data, error } = await supabase
        .from("productos")
        .select(`
          *,
          producto_imagenes (
            url
          )
        `);

      if (error) {
        console.error("Error cargando productos:", error);
        setProductos([]);
      } else if (data) {
        // Mezclar los productos aleatoriamente y mostrar 18
        const aleatorios = [...data]
          .sort(() => Math.random() - 0.5)
          .slice(0, 18);

        setProductos(aleatorios);
      }

      setCargando(false);
    }

    cargarProductos();
  }, []);

  const formatoPrecio = (precio) => {
    const valor = Number(precio);

    if (!Number.isFinite(valor)) {
      return "Precio no disponible";
    }

    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      maximumFractionDigits: 0,
    }).format(valor);
  };

  return (
    <>
      <Navbar productos={productos} />

      <main className="home-page">
        {/* Banner principal con fondo difuminado */}
        <section className="hero">
          <div
            className="hero-bg"
            style={{ backgroundImage: `url(${banner})` }}
            aria-hidden="true"
          />

          <div className="home-banner">
            <img
              src={banner}
              alt="Ofertas y promociones de Importa-Ya"
              className="home-banner-img"
            />
          </div>
        </section>

        {/* Tarjetas de beneficios */}
        <section className="home-benefits">
          {beneficios.map((beneficio) => (
            <div className="benefit-card" key={beneficio.titulo}>
              <span className="benefit-icon">{beneficio.icono}</span>
              <div>
                <strong>{beneficio.titulo}</strong>
                <p>{beneficio.texto}</p>
              </div>
            </div>
          ))}
        </section>

        {/* Contenido de la tienda */}
        <div className="home-content">
          <section className="home-intro">
            <div>
              <h1>Descubre nuestros productos</h1>
              <p>
                Encuentra lo que buscas y disfruta comprando en Importa-Ya.
              </p>
            </div>

            <span className="home-product-count">
              {productos.length} productos
            </span>
          </section>

          <div
            className="home-sort-controls"
            role="group"
            aria-label="Ordenar productos por precio"
            style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px", marginBottom: "24px" }}
          >
            <span>Ordenar por:</span>
            {[
              { valor: "original", texto: "Orden original" },
              { valor: "asc", texto: "Precio: de menor a mayor" },
              { valor: "desc", texto: "Precio: de mayor a menor" },
            ].map((opcion) => (
              <button
                key={opcion.valor}
                type="button"
                aria-pressed={ordenPrecio === opcion.valor}
                onClick={() => setOrdenPrecio(opcion.valor)}
                style={{
                  padding: "10px 14px",
                  border: "1px solid #222",
                  borderRadius: "2px",
                  backgroundColor: ordenPrecio === opcion.valor ? "#222" : "#fff",
                  color: ordenPrecio === opcion.valor ? "#fff" : "#222",
                  cursor: "pointer",
                  font: "inherit",
                }}
              >
                {opcion.texto}
              </button>
            ))}
          </div>

          {/* Grid de productos */}
          <section className="products-section">
            <div className="products-grid">
              {cargando ? (
                <p className="products-message">Cargando productos...</p>
              ) : productos.length === 0 ? (
                <p className="products-message">
                  No hay productos disponibles por el momento.
                </p>
              ) : (
                productosOrdenados.map((producto) => {
                  const imagen =
                    producto.imagen_principal ||
                    producto.producto_imagenes?.find((item) => item.url)?.url;

                  return (
                    <article className="product-card" key={producto.id}>
                      <a
                        className="product-image-container"
                        href={`/ProductDetails/${producto.id}`}
                        aria-label={`Ver ${producto.nombre}`}
                      >
                        {imagen ? (
                          <img
                            src={imagen}
                            alt={producto.nombre}
                            className="product-image"
                            loading="lazy"
                          />
                        ) : (
                          <div className="product-no-image">
                            Sin imagen disponible
                          </div>
                        )}
                      </a>

                      <div className="product-info">
                        <h2 className="product-name">{producto.nombre}</h2>

                        <p className="product-price">
                          {formatoPrecio(producto.precio)}
                        </p>

                        <p className="product-shipping">
                          Envío y gastos de impuestos incluidos
                        </p>

                        <a
                          href={`/ProductDetails/${producto.id}`}
                          className="product-button"
                        >
                          Ver producto
                        </a>
                      </div>
                    </article>
                  );
                })
              )}
            </div>
          </section>
        </div>
      </main>
    </>
  );
}

export default Home;