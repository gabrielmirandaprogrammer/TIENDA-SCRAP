from firebase_config import db

producto = {
    "id": "MARCUS MILLER M2 TBL 2ND GEN",
    "nombre": "Marcus Miller M2 TBL 2nd Gen",
    "precio": 315.89,
    "url": "https://www.thomann.de/intl/marcus_miller_m2_tbl_2nd_gen_b_stock.htm?type=advancedSearch"
}

db.collection("products") \
  .document(producto["id"]) \
  .set(producto)

print("Producto enviado a Firestore")