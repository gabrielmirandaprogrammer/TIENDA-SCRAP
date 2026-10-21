import Carousel from "react-bootstrap/Carousel";
import "./css/CarouselDetail.css";

function CarouselDetail({ gallery }) {

  if (!gallery || gallery.length === 0) {
    return <div>No hay imágenes</div>;
  }

  return (
    <div className="product-gallery">
      <Carousel
        indicators={true}
        interval={4000}
        pause="hover"
      >
        {gallery.map((img, index) => (
          <Carousel.Item key={index}>
            <div className="product-image-container">
              <img
                src={img}
                alt={`imagen-${index}`}
                className="product-image"
              />
            </div>
          </Carousel.Item>
        ))}
      </Carousel>
    </div>
  );
}

export default CarouselDetail;

