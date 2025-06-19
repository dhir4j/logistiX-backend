from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Shipment
from app.extensions import db
from sqlalchemy import or_, and_
from datetime import datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

def admin_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if not identity.get("is_admin"):
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@admin_bp.route("/shipments", methods=["GET"])
@admin_required
def get_all_shipments():
    # Pagination, search, filtering
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    status = request.args.get("status")
    q = request.args.get("q")
    query = Shipment.query

    if status:
        query = query.filter_by(status=status)
    if q:
        like_q = f"%{q}%"
        query = query.filter(
            or_(
                Shipment.shipment_id_str.ilike(like_q),
                Shipment.sender_name.ilike(like_q),
                Shipment.receiver_name.ilike(like_q)
            )
        )
    total_count = query.count()
    shipments = query.order_by(Shipment.booking_date.desc()).paginate(page, limit, False).items
    total_pages = (total_count + limit - 1) // limit

    result = [
        {
            "shipmentIdStr": s.shipment_id_str,
            "status": s.status,
            "booking_date": s.booking_date.isoformat(),
            "sender_name": s.sender_name,
            "receiver_name": s.receiver_name,
            "tracking_history": s.tracking_history,
            "total_with_tax_18_percent": float(s.total_with_tax_18_percent),
        } for s in shipments
    ]
    return jsonify({
        "shipments": result,
        "totalPages": total_pages,
        "currentPage": page,
        "totalCount": total_count
    }), 200

@admin_bp.route("/shipments/<shipment_id_str>/status", methods=["PUT"])
@admin_required
def update_shipment_status(shipment_id_str):
    data = request.get_json()
    new_status = data.get("status")
    location = data.get("location")
    activity = data.get("activity")

    valid_statuses = ['Booked', 'In Transit', 'Out for Delivery', 'Delivered', 'Cancelled']
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400

    shipment = Shipment.query.filter_by(shipment_id_str=shipment_id_str).first()
    if not shipment:
        return jsonify({"error": "Shipment not found"}), 404

    shipment.status = new_status
    entry = {
        "stage": new_status,
        "date": datetime.utcnow().isoformat(),
        "location": location or "",
        "activity": activity or f"Status updated to {new_status}",
    }
    history = shipment.tracking_history or []
    history.append(entry)
    shipment.tracking_history = history
    db.session.commit()

    return jsonify({
        "message": "Shipment status updated",
        "updatedShipment": {
            "shipmentIdStr": shipment.shipment_id_str,
            "status": shipment.status,
            "tracking_history": shipment.tracking_history,
        }
    }), 200
