import { useState } from "react";
import { Link } from "react-router-dom";
import "./css/Footer.css";

const COLUMNAS = [
  {
    titulo: "Categorías",
    enlaces: [
      { texto: "Guitarras", to: "/?cat=guitarras" },
      { texto: "Bajos", to: "/?cat=bajos" },
      { texto: "Todo el catálogo", to: "/" },
    ],
  },
  {
    titulo: "Ayuda",
    enlaces: [
      { texto: "Envíos y entregas", to: "/ayuda/envios" },
      { texto: "Cambios y devoluciones", to: "/ayuda/devoluciones" },
      { texto: "Garantía", to: "/ayuda/garantia" },
      { texto: "Preguntas frecuentes", to: "/ayuda" },
    ],
  },
];

const REDES = [
  {
    nombre: "Instagram",
    url: "https://instagram.com/",
    icono: (
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <rect
          x="3"
          y="3"
          width="18"
          height="18"
          rx="5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        />
        <circle
          cx="12"
          cy="12"
          r="4.2"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        />
        <circle cx="17.2" cy="6.8" r="1.2" fill="currentColor" />
      </svg>
    ),
  },
  {
    nombre: "Facebook",
    url: "https://facebook.com/",
    icono: (
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path
          d="M13.5 21v-7.2h2.6l.4-3h-3V8.9c0-.9.3-1.5 1.6-1.5h1.5V4.7c-.3 0-1.3-.1-2.4-.1-2.4 0-4 1.4-4 4v2.2H7.5v3h2.7V21h3.3z"
          fill="currentColor"
        />
      </svg>
    ),
  },
  {
    nombre: "WhatsApp",
    url: "https://wa.me/573000000000",
    icono: (
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path
          d="M12 3a9 9 0 0 0-7.7 13.6L3 21l4.5-1.2A9 9 0 1 0 12 3z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinejoin="round"
        />
        <path
          d="M9.2 8.4c.3-.1.6 0 .8.3l.7 1.2c.1.3.1.5-.1.7l-.5.5c.5 1 1.3 1.8 2.3 2.3l.5-.5c.2-.2.4-.2.7-.1l1.2.7c.3.2.4.5.3.8-.3.9-1.2 1.5-2.1 1.4-2.6-.3-4.7-2.4-5-5-.1-.9.5-1.8 1.4-2.1z"
          fill="currentColor"
        />
      </svg>
    ),
  },
];

function Footer() {
  const [correo, setCorreo] = useState("");
  const [error, setError] = useState("");
  const [confirmacion, setConfirmacion] = useState("");

  const suscribir = (evento) => {
    evento.preventDefault();
    const limpio = correo.trim();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(limpio)) {
      setError("Escribe un correo válido.");
      setConfirmacion("");
      return;
    }

    setError("");
    setConfirmacion(`Listo, ${limpio} quedó registrado. Te avisamos de cada oferta.`);
    setCorreo("");
  };

  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-grid">
          {/* Marca y contacto */}
          <div className="footer-brand">
            <Link to="/" className="footer-logo">
              Importa<span>-Ya</span>
            </Link>
            <p className="footer-tagline">
              Instrumentos importados con garantía, factura y envío a todo
              Colombia. Guitarras y bajos seleccionados uno por uno.
            </p>

            <ul className="footer-contacto">
              <li>
                <a href="https://wa.me/573000000000" target="_blank" rel="noreferrer">
                  WhatsApp: +57 300 000 0000
                </a>
              </li>
              <li>
                <a href="mailto:hola@importaya.co">hola@importaya.co</a>
              </li>
              <li>Lunes a sábado, 9:00 a 18:00</li>
            </ul>
          </div>

          {/* Columnas de enlaces */}
          {COLUMNAS.map((columna) => (
            <nav className="footer-columna" key={columna.titulo}>
              <h3>{columna.titulo}</h3>
              <ul>
                {columna.enlaces.map((enlace) => (
                  <li key={enlace.texto}>
                    <Link to={enlace.to}>{enlace.texto}</Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}

          {/* Boletín */}
          <div className="footer-boletin">
            <h3>Ofertas antes que nadie</h3>
            <p>
              Un correo al mes con las entradas nuevas y los descuentos que no
              publicamos en la tienda.
            </p>

            <form onSubmit={suscribir} noValidate>
              <label className="footer-boletin-label" htmlFor="footer-correo">
                Tu correo electrónico
              </label>
              <div className="footer-boletin-fila">
                <input
                  id="footer-correo"
                  type="email"
                  placeholder="tucorreo@ejemplo.com"
                  value={correo}
                  onChange={(evento) => {
                    setCorreo(evento.target.value);
                    setError("");
                    setConfirmacion("");
                  }}
                  aria-invalid={Boolean(error)}
                />
                <button type="submit">Suscribirme</button>
              </div>
              {error && <span className="footer-boletin-error">{error}</span>}
              {confirmacion && (
                <span className="footer-boletin-ok">{confirmacion}</span>
              )}
            </form>
          </div>
        </div>

        <div className="footer-pagos">
          <span>Pago contra entrega, transferencia y tarjetas</span>
          <span>Envíos a todo el país en 3 a 7 días hábiles</span>
        </div>

        <div className="footer-bottom">
          <p>© {new Date().getFullYear()} Importa-Ya. Todos los derechos reservados.</p>

          <div className="footer-legal">
            <Link to="/terminos">Términos</Link>
            <Link to="/privacidad">Privacidad</Link>
          </div>

          <div className="footer-redes">
            {REDES.map((red) => (
              <a
                key={red.nombre}
                href={red.url}
                target="_blank"
                rel="noreferrer"
                aria-label={red.nombre}
                title={red.nombre}
              >
                {red.icono}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;