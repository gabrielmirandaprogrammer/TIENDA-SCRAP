import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import ProductDetails from "./pages/productDetails";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Terminos from "./pages/Terminos";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/Login" element={<Login />} />
        <Route path="/Register" element={<Register />} />
        
        <Route
          path="/ProductDetails/:id"
          element={<ProductDetails />}
        />
        <Route path="/terminos" element={<Terminos />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;