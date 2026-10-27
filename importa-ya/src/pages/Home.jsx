import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
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

// Categorías destacadas del navbar: valor de ?cat= → título y filtro por nombre.
const CATEGORIAS_NAV = {
  guitarras: { titulo: "Guitarras", filtro: "guitarra" },
  bajos: { titulo: "Bajos", filtro: "bajo" },
};

// Cantidad de productos por página ("Mostrar más").
const TAMANO_PAGINA = 18;

// Escape % y _ para que se traten como texto, no como comodines.
const escaparIlike = (palabra) => palabra.replace(/[\\%_]/g, "\\$&");

// Minúsculas y sin tildes: mismo criterio que las columnas generadas
// (f_sin_acentos) de la base.
const normalizarTexto = (texto) =>
  texto
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

// Palabras normalizadas del término de búsqueda (máx. 5).
const palabrasDe = (busqueda) =>
  busqueda
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 5)
    .map((palabra) => escaparIlike(normalizarTexto(palabra)));

function Home() {
  const [productos, setProductos] = useState([]);
  const [idsPorNombre, setIdsPorNombre] = useState(() => new Set());
  const [visibles, setVisibles] = useState(TAMANO_PAGINA);
  const [cargando, setCargando] = useState(true);
  const [ordenPrecio, setOrdenPrecio] = useState("original");
  const [soloNombre, setSoloNombre] = useState(false);

  const [searchParams] = useSearchParams();
  const categoria =
    CATEGORIAS_NAV[(searchParams.get("cat") ?? "").toLowerCase()] ?? null;
  const busqueda = (searchParams.get("busqueda") ?? "").trim();

  const conFiltros = Boolean(categoria || busqueda);

  // El orden de llegada ya es por relevancia (nombre primero); el orden por
  // precio, cuando se pide, manda sobre esa relevancia.
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

  const productosVisibles = productosOrdenados.slice(0, visibles);

  const soloDescripcion = productos.filter(
    (producto) => !idsPorNombre.has(producto.id)
  ).length;

  useEffect(() => {
    async function cargarProductos() {
      setCargando(true);

      let consulta = supabase
        .from("productos")
        .select(`
          *,
          producto_imagenes (
            url
          )
        `);

      if (busqueda) {
        // Con "solo nombre" se busca en nombre_busqueda; si no, en
        // texto_busqueda (nombre + descripción). Cada palabra debe
        // aparecer, en cualquier orden.
        const palabras = palabrasDe(busqueda);
        const columna = soloNombre ? "nombre_busqueda" : "texto_busqueda";

        for (const palabra of palabras) {
          consulta = consulta.ilike(columna, `%${palabra}%`);
        }
      } else if (categoria) {
        const { data: categorias, error: errorCategorias } = await supabase
          .from("categorias")
          .select("id")
          .ilike("nombre", `%${categoria.filtro}%`);

        if (errorCategorias) {
          console.error("Error cargando categorías:", errorCategorias);
          setProductos([]);
          setCargando(false);
          return;
        }

        const idsCategorias = (categorias ?? []).map((fila) => fila.id);

        if (idsCategorias.length === 0) {
          setProductos([]);
          setVisibles(TAMANO_PAGINA);
          setCargando(false);
          return;
        }

        consulta = consulta.in("categoria_id", idsCategorias);
      }

      const { data, error } = await consulta;

      if (error) {
        console.error("Error cargando productos:", error);
        setProductos([]);
        setIdsPorNombre(new Set());
      } else {
        let lista = data ?? [];

        if (busqueda) {
          // Relevancia: los que coinciden por nombre van primero; los que
          // solo coinciden por descripción, después.
          const palabras = palabrasDe(busqueda);
          const coincideNombre = (producto) => {
            const nombre = producto.nombre_busqueda ?? "";
            return palabras.every((palabra) => nombre.includes(palabra));
          };

          const porNombre = lista.filter(coincideNombre);
          const porDescripcion = lista.filter((producto) => !coincideNombre(producto));

          setIdsPorNombre(new Set(porNombre.map((producto) => producto.id)));
          lista = [...porNombre, ...porDescripcion];
        } else {
          setIdsPorNombre(new Set());

          // En el home sin filtros se mezclan los productos al azar;
          // en categorías se respeta el orden de la base.
          if (!categoria) {
            lista.sort(() => Math.random() - 0.5);
          }
        }

        setProductos(lista);
      }

      setVisibles(TAMANO_PAGINA);
      setCargando(false);
    }

    cargarProductos();
  }, [categoria, busqueda, soloNombre]);

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

  const titulo = busqueda
    ? `Resultados para "${busqueda}"`
    : categoria
      ? categoria.titulo
      : "Descubre nuestros productos";

  const opcionesOrden = [
    { valor: "original", texto: "Orden original" },
    { valor: "asc", texto: "Precio: de menor a mayor" },
    { valor: "desc", texto: "Precio: de mayor a menor" },
  ];

  return (
    <>
      <Navbar productos={productosVisibles} />

      <main className="home-page">
        {!conFiltros && (
          <>
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
          </>
        )}

        <div className="home-content">
          {conFiltros && (
            <nav className="home-breadcrumb" aria-label="Ruta de navegación">
              <Link to="/">Inicio</Link>
              <span className="home-breadcrumb-separador">/</span>
              <span className="home-breadcrumb-actual">
                {busqueda ? `Búsqueda: ${busqueda}` : categoria.titulo}
              </span>
            </nav>
          )}

          <section className="home-intro">
            <div>
              <h1>{titulo}</h1>
              <p>
                Encuentra lo que buscas y disfruta comprando en Importa-Ya.
              </p>
            </div>

            <div className="home-intro-derecha">
              <span className="home-product-count">
                {cargando
                  ? "…"
                  : `${productosOrdenados.length} productos${
                      busqueda && !soloNombre && soloDescripcion > 0
                        ? ` (${soloDescripcion} solo por descripción)`
                        : ""
                    }`}
              </span>

              {conFiltros && (
                <Link to="/" className="home-ver-todo">
                  Ver todo
                </Link>
              )}
            </div>
          </section>

          {busqueda && (
            <label className="home-solo-nombre">
              <input
                type="checkbox"
                checked={soloNombre}
                onChange={(e) => setSoloNombre(e.target.checked)}
              />
              Buscar solo en el nombre del producto
            </label>
          )}

          <div
            className="home-sort-controls"
            role="group"
            aria-label="Ordenar productos por precio"
          >
            <span>Ordenar por:</span>

            {opcionesOrden.map((opcion) => (
              <button
                key={opcion.valor}
                type="button"
                className={`sort-btn${ordenPrecio === opcion.valor ? " activo" : ""}`}
                aria-pressed={ordenPrecio === opcion.valor}
                onClick={() => setOrdenPrecio(opcion.valor)}
              >
                {opcion.texto}
              </button>
            ))}
          </div>

          <section className="products-section">
            <div className="products-grid">
              {cargando ? (
                <p className="products-message">Cargando productos...</p>
              ) : productosVisibles.length === 0 ? (
                <p className="products-message">
                  {busqueda
                    ? `No encontramos productos que coincidan con "${busqueda}".`
                    : "No hay productos disponibles por el momento."}
                </p>
              ) : (
                productosVisibles.map((producto) => {
                  const imagen =
                    producto.imagen_principal ||
                    producto.producto_imagenes?.find((item) => item.url)?.url;

                  const porDescripcion =
                    busqueda && !soloNombre && !idsPorNombre.has(producto.id);

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

                        {porDescripcion && (
                          <p className="product-match-nota">
                            Coincide en la descripción
                          </p>
                        )}

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

          {!cargando && productosOrdenados.length > visibles && (
            <div className="home-mostrar-mas">
              <button
                type="button"
                onClick={() => setVisibles((cantidad) => cantidad + TAMANO_PAGINA)}
              >
                Mostrar más ({productosOrdenados.length - visibles} restantes)
              </button>
            </div>
          )}
        </div>
      </main>
    </>
  );
}

export default Home;