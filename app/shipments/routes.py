from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Shipment, User
from app.extensions import db
from app.schemas import ShipmentCreateSchema
from app.utils import generate_shipment_id_str, calculate_shipment_cost
from datetime import datetime

shipments_bp = Blueprint("shipments", __name__, url_prefix="/api/shipments")

@shipments_bp.route("", methods=["POST"])
@jwt_required()
def create_shipment():
    schema = ShipmentCreateSchema()
    data = request.get_json()
    try:
        shipment_data = schema.load(data)
    except Exception:
        return jsonify({"error": "Invalid shipment details"}), 400

    user_claim = get_jwt_identity()
    user_id = user_claim["user_id"]
    shipment_id_str = generate_shipment_id_str()

    price, tax, total = calculate_shipment_cost(
        shipment_data["package_weight_kg"], shipment_data["service_type"]
    )

    now_iso = datetime.utcnow().isoformat()
    tracking_history = [{
        "stage": "Booked",
        "date": now_iso,
        "location": shipment_data["sender_address_city"],
        "activity": "Shipment booked and confirmed"
    }]

    new_shipment = Shipment(
        user_id=user_id,
        shipment_id_str=shipment_id_str,
        **shipment_data,
        price_without_tax=price,
        tax_amount_18_percent=tax,
        total_with_tax_18_percent=total,
        status="Booked",
        tracking_history=tracking_history
    )
    db.session.add(new_shipment)
    db.session.commit()
    return jsonify({
        "shipmentIdStr": shipment_id_str,
        "message": "Shipment booked successfully",
        "data": {
            "id": new_shipment.id,
            "shipmentIdStr": shipment_id_str,
            **shipment_data,
            "price_without_tax": float(price),
            "tax_amount_18_percent": float(tax),
            "total_with_tax_18_percent": float(total),
            "status": "Booked",
            "tracking_history": tracking_history
        }
    }), 201

@shipments_bp.route("", methods=["GET"])
@jwt_required()
def get_user_shipments():
    user_claim = get_jwt_identity()
    user_id = user_claim["user_id"]
    shipments = Shipment.query.filter_by(user_id=user_id).order_by(Shipment.booking_date.desc()).all()
    result = []
    for s in shipments:
        result.append({
            "id": s.id,
            "shipmentIdStr": s.shipment_id_str,
            "status": s.status,
            "booking_date": s.booking_date.isoformat(),
            "sender_name": s.sender_name,
            "receiver_name": s.receiver_name,
            "tracking_history": s.tracking_history,
            "total_with_tax_18_percent": float(s.total_with_tax_18_percent),
        })
    return jsonify(result), 200

@shipments_bp.route("/<shipment_id_str>", methods=["GET"])
@jwt_required()
def get_shipment_detail(shipment_id_str):
    user_claim = get_jwt_identity()
    shipment = Shipment.query.filter_by(shipment_id_str=shipment_id_str).first()
    if not shipment:
        return jsonify({"error": "Shipment not found"}), 404

    # Only owner or admin can view
    if shipment.user_id != user_claim["user_id"] and not user_claim["is_admin"]:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({
        "id": shipment.id,
        "shipmentIdStr": shipment.shipment_id_str,
        "status": shipment.status,
        "booking_date": shipment.booking_date.isoformat(),
        "sender_name": shipment.sender_name,
        "receiver_name": shipment.receiver_name,
        "tracking_history": shipment.tracking_history,
        "total_with_tax_18_percent": float(shipment.total_with_tax_18_percent),
        # ...add more fields as needed
    }), 200
