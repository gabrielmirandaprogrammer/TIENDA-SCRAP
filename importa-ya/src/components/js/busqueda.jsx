import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import searchIcon from "../../assets/find.svg";
import { supabase } from "../../services/supabase";

const Buscador = () => {
  const [texto, setTexto] = useState("");
  const [resultados, setResultados] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [buscado, setBuscado] = useState(false);

  // Evita mostrar respuestas de búsquedas anteriores.
  const ultimaBusqueda = useRef(0);

  const handleChange = (e) => {
    ultimaBusqueda.current += 1;
    setTexto(e.target.value);
    setResultados([]);
    setError("");
    setBuscado(false);
    setCargando(false);
  };

  const hacerBusqueda = async (e) => {
    e.preventDefault();

    const termino = texto.trim();
    const solicitud = ++ultimaBusqueda.current;

    setResultados([]);
    setError("");
    setBuscado(false);

    if (!termino) {
      setCargando(false);
      return;
    }

    setCargando(true);

    try {
      // Trata % y _ como texto, no como comodines de búsqueda.
      const terminoEscapado = termino.replace(/[\\%_]/g, "\\$&");

      const { data, error: errorConsulta } = await supabase
        .from("productos")
        .select("id, nombre")
        .ilike("nombre", `%${terminoEscapado}%`)
        .order("nombre")
        .limit(20);

      if (solicitud !== ultimaBusqueda.current) return;

      if (errorConsulta) throw errorConsulta;

      setResultados(data ?? []);
      setBuscado(true);
    } catch (errorConsulta) {
      if (solicitud !== ultimaBusqueda.current) return;

      console.error("Error al buscar productos:", errorConsulta);
      setError("No pudimos buscar los productos. Intenta nuevamente.");
    } finally {
      if (solicitud === ultimaBusqueda.current) {
        setCargando(false);
      }
    }
  };

  const cerrarResultados = () => {
    ultimaBusqueda.current += 1;
    setResultados([]);
    setBuscado(false);
    setError("");
    setCargando(false);
  };

  return (
    <div
      className="buscador"
      onKeyDown={(e) => {
        if (e.key === "Escape") cerrarResultados();
      }}
    >
      <form
        className="buscador-form"
        onSubmit={hacerBusqueda}
        role="search"
      >
        <input
          type="search"
          value={texto}
          onChange={handleChange}
          placeholder="Buscar producto..."
          aria-label="Buscar productos"
          autoComplete="off"
        />

        <button
          type="submit"
          disabled={cargando || !texto.trim()}
          aria-label="Buscar"
        >
          <img src={searchIcon} alt="" width="20" height="20" />
        </button>
      </form>

      {(cargando || error || buscado) && (
        <div className="buscador-resultados">
          {cargando && <p role="status">Buscando...</p>}

          {error && <p role="alert">{error}</p>}

          {buscado && resultados.length === 0 && (
            <p role="status">No encontramos productos con ese nombre.</p>
          )}

          {buscado && resultados.length > 0 && (
            <>
              <p role="status">
                {resultados.length} resultado(s)
                {resultados.length === 20 ? " · Mostrando hasta 20" : ""}
              </p>

              <ul>
                {resultados.map((producto) => (
                  <li key={producto.id}>
                    <Link
                      to={`/ProductDetails/${encodeURIComponent(producto.id)}`}
                      onClick={cerrarResultados}
                    >
                      {producto.nombre}
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default Buscador;