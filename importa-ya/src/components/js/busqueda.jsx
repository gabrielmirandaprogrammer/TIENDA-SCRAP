import { useState } from "react";
import { useNavigate } from "react-router-dom";
import searchIcon from "../../assets/find.svg";

const Buscador = () => {
  const [texto, setTexto] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => {
    setTexto(e.target.value);
  };

  // Al dar Enter o clic en la lupa se navega al home con el término de
  // búsqueda en la URL; es Home quien filtra la grilla con ese valor.
  const hacerBusqueda = (e) => {
    e.preventDefault();

    const termino = texto.trim();
    if (!termino) return;

    navigate(`/?busqueda=${encodeURIComponent(termino)}`);
  };

  return (
    <div className="buscador">
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
          disabled={!texto.trim()}
          aria-label="Buscar"
        >
          <img src={searchIcon} alt="" width="20" height="20" />
        </button>
      </form>
    </div>
  );
};

export default Buscador;