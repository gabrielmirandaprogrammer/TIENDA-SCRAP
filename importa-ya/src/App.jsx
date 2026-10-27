import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import ProductDetails from "./pages/productDetails";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Terminos from "./pages/Terminos";
import Carrito from "./pages/Carrito";

function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "")}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/Login" element={<Login />} />
        <Route path="/Register" element={<Register />} />

        <Route
          path="/ProductDetails/:id"
          element={<ProductDetails />}
        />
        <Route path="/terminos" element={<Terminos />} />
        <Route path="/carrito" element={<Carrito />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;