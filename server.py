from commons import me_get, me_post
from doctor.my_patients import my_patients_delete, my_patients_get, my_patients_post
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_claims
from flask_pymongo import PyMongo
from passlib.hash import pbkdf2_sha256 as sha256
from utils import error_message
from user.my_doctors import my_doctors_post, my_doctors_get, my_doctors_delete

app = Flask(__name__)
CORS(app)

# Initialize mongo client
with open("/root/oniro-server/mongourl.secret") as url_file:
    app.config["MONGO_URI"] = url_file.read()[:-1]
    mongo = PyMongo(app)

# Initialize JWT
with open("/root/oniro-server/jwt.secret") as key_file:
    app.config["JWT_SECRET_KEY"] = key_file.read()[:-1]
    jwt = JWTManager(app)


@jwt.user_claims_loader
def add_claims_to_access_token(data):
    return {
        "identity": data["username"],
        "type": data["type"]
    }


@app.route('/login/<string:user_type>', methods=['GET'])
def login(user_type):
    if user_type != "user" and user_type != "doctor":
        return make_response("error", 404)

    key = ""
    if user_type == "user":
        key = "cf"
    elif user_type == "doctor":
        key = "id"

    params = {
        key: request.args.get(key),
        "password": request.args.get("password")
    }

    if key not in params or "password" not in params:
        return error_message("id and password are mandatory fields!")

    try:
        user = mongo.db[user_type+"s"].find_one({"_id": params[key]})

        if user is None:
            return error_message("user does not exists!")

        pwd = user["password"]
        if not sha256.verify(params["password"], pwd):
            return error_message("password is not correct")

        access_token = create_access_token({"username": params[key], "type": "user"})

        return jsonify(status="ok", access_token=access_token)

    except Exception as e:
        return make_response(str(e), 500)


@app.route("/register/user", methods=['PUT'])
def register_user():
    json_data = request.get_json(silent=True, cache=False)
    if json_data is None:
        return error_message("mime type not accepted")

    fields = ["cf", "name", "surname", "age", "email", "password", "phone_number"]

    for field in fields:
        if field not in json_data:
            return error_message(field + " is a mandatory field")

    try:
        if mongo.db.users.find_one({'_id': json_data["cf"]}) is not None:
            return error_message("a user with this CF already exists!")

        mongo.db.users.insert_one(
            {
                "_id": json_data["cf"],
                "email": json_data["email"],
                "password": sha256.hash(json_data["password"]),
                "name": json_data["name"],
                "surname": json_data["surname"],
                "age": json_data["age"],
                "phone_server": json_data["phone_number"]
            }
        )

        access_token = create_access_token({"username": json_data["cf"], "type": "user"})
        return jsonify(status="ok", access_token=access_token)

    except Exception as e:
        return make_response(str(e), 500)


@app.route("/register/doctor", methods=['PUT'])
def register_doctor():
    json_data = request.get_json(silent=True, cache=False)
    if json_data is None:
        return error_message("mime type not accepted")

    fields = ["id", "email", "password", "name", "surname", "address", "phone"]

    for field in fields:
        if field not in json_data:
            return error_message(field + " is a mandatory field")

    try:
        if mongo.db.doctors.find_one({'_id': json_data["id"]}) is not None:
            return error_message("a user with this id already exists!")

        mongo.db.doctors.insert_one(
            {
                "_id": json_data["id"],
                "email": json_data["email"],
                "password": sha256.hash(json_data["password"]),
                "name": json_data["name"],
                "surname": json_data["surname"],
                "address": json_data["address"],
                "phone": json_data["phone"],
                "patients": [],
                "patient_requests": []
            }
        )

        access_token = create_access_token({"username": json_data["id"], "type": "doctor"})
        return jsonify(status="ok", access_token=access_token)

    except Exception as e:
        return make_response(str(e), 500)


@app.route("/me", methods=['GET', 'POST'])
@jwt_required
def me():
    params = request.get_json(silent=True, cache=False)
    claims = get_jwt_claims()

    if request.method == 'GET':
        return me_get(claims, mongo)

    if request.method == 'POST':
        return me_post(params, claims, mongo)


@app.route("/user/my_doctors", methods=['GET', 'DELETE', 'POST'])
@jwt_required
def my_doctors():
    params = request.get_json(silent=True, cache=False)
    claims = get_jwt_claims()

    if request.method == 'GET':
        return my_doctors_get(claims, mongo)

    if request.method == 'POST':
        return my_doctors_post(params, claims, mongo)

    if request.method == 'DELETE':
        return my_doctors_delete(request.args.get("doctor_id"), claims, mongo)


@app.route("/doctor/my_patients", methods=['GET', 'DELETE', 'POST'])
@jwt_required
def my_patients():
    params = request.get_json(silent=True, cache=False)
    claims = get_jwt_claims()

    if request.method == 'GET':
        return my_patients_get(claims, mongo)

    if request.method == 'POST':
        return my_patients_post(params, claims, mongo)

    if request.method == 'DELETE':
        return my_patients_delete(request.args.get("patient_cf"), claims, mongo)


if __name__ == "__main__":
    app.run('0.0.0.0', 8080)
