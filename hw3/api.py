#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
import json
import datetime
import logging
import hashlib
import uuid
import re
import scoring
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


def is_empty(value):
    """Return True if value is value is set, but empty"""
    return value in ["", (), [], {}, set()]


class BaseField(ABC):
    @abstractmethod
    def validate(self, value):
        pass


class Field(BaseField):
    def __init__(self, required=False, nullable=True):
        self.required = required
        self.nullable = nullable

    def validate(self, value):
        """Return string with error description, empty string if no errors or None if value can't be validated"""
        if value is None:
            if self.required:
                return "Field is required"
        elif is_empty(value):
            if not self.nullable:
                return "Field can't be empty"
        else:
            return ""


class CharField(Field):
    def validate(self, value):
        error = super().validate(value)
        if error:
            return error
        # can't validate None
        if value is None:
            return None
        if not isinstance(value, str):
            return "Field must be a string"
        return ""


class ArgumentsField(Field):
    def validate(self, value):
        error = super().validate(value)
        if error:
            return error
        # can't validate None
        if value is None:
            return None
        if not isinstance(value, dict):
            return "Field must be a dict"
        return ""


class EmailField(CharField):
    def validate(self, value):
        error = super().validate(value)
        if error:
            return error
        # can't validate None
        if value is None:
            return None
        if "@" not in value:
            return "Field must be a valid email"
        return ""


class PhoneField(Field):
    def validate(self, value):
        error = super().validate(value)
        if error:
            return error
        # can't validate None
        if value is None:
            return None
        if not re.search(r"^7\d{10}$", str(value)):
            return "Field must be a valid phone"
        return ""


class DateField(CharField):
    def validate(self, value):
        error = super().validate(value)
        if error:
            return error
        # can't validate None
        if value is None:
            return None
        try:
            datetime.datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            return "Date must have format: DD.MM.YYYY"
        return ""


class BirthDayField(DateField):
    def validate(self, value):
        error = super().validate(value)
        if error:
            return error
        # can't validate None
        if value is None:
            return None
        birthday = datetime.datetime.strptime(value, "%d.%m.%Y").date()
        today = datetime.date.today()
        age = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            age -= 1
        if age > 70:
            return "Birthday must be not more than 70 years from now"
        return ""


class GenderField(Field):
    def validate(self, value):
        error = super().validate(value)
        if error:
            return error
        # can't validate None
        if value is None:
            return None
        if value not in GENDERS:
            return "Gender must be a number %s, %s, %s" % (UNKNOWN, MALE, FEMALE)
        return ""


class ClientIDsField(Field):
    def validate(self, value):
        error = super().validate(value)
        if error:
            return error
        # can't validate None
        if value is None:
            return None
        if not isinstance(value, list):
            return "Field must be a list of integer"
        for client_id in value:
            if not isinstance(client_id, int):
                return "Field must be a list of integer"
        return ""


class MetaRequest(type):
    """Metaclass. Gather all Field attributes declared in class definition into new "schema" attribute"""
    def __new__(mcs, name, bases, attrs):
        schema = {}
        for attr, value in attrs.items():
            if isinstance(value, Field):
                schema[attr] = value
        attrs["schema"] = schema
        for attr in schema:
            del attrs[attr]
        return super(MetaRequest, mcs).__new__(mcs, name, bases, attrs)


class Request(metaclass=MetaRequest):
    def __init__(self, request):
        self.request = request
        for name in self.schema:
            value = self.request.get(name, None)
            setattr(self, name, value)

    def validate(self):
        """Return dict with erroneous fields and their description or empty dict if no errors"""
        errors = {}
        for name, field in self.schema.items():
            value = getattr(self, name)
            field_error = field.validate(value)
            if field_error:
                errors[name] = field_error
        return errors


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def handle(self, ctx, store):
        errors = self.validate()
        if errors:
            return errors, INVALID_REQUEST

        ctx.update({"nclients": len(self.client_ids)})

        interests = {str(cid): scoring.get_interests(store, cid) for cid in self.client_ids}
        return interests, OK


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def validate(self):
        errors = super().validate()
        non_empty_pairs = [["phone", "email"],
                           ["first_name", "last_name"],
                           ["gender", "birthday"]]
        all_pairs_empty = True
        for pair in non_empty_pairs:
            if pair[0] in self.non_empty_field() and pair[1] in self.non_empty_field():
                all_pairs_empty = False
                break
        if all_pairs_empty:
            errors["online_score"] = " At least one pair phone‑email, first name‑last name, gender‑birthday" + \
                                     " must not be empty"
        return errors

    def non_empty_field(self):
        not_empty = []
        for field in self.schema:
            value = getattr(self, field)
            if value is not None and not is_empty(value):
                not_empty.append(field)
        return not_empty

    def handle(self, ctx, store, is_admin):
        errors = self.validate()
        if errors:
            return errors, INVALID_REQUEST
        ctx.update({"has": self.non_empty_field()})
        if is_admin:
            return {"score": 42}, OK
        score = scoring.get_score(store,
                                  phone=self.phone,
                                  email=self.email,
                                  birthday=self.birthday,
                                  gender=self.gender,
                                  first_name=self.first_name,
                                  last_name=self.last_name)
        return {"score": score}, OK


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        msg = (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode()
    else:
        if request.account is None:
            account = ""  # TODO: is it secure?
        else:
            account = request.account
        msg = (account + request.login + SALT).encode()
    digest = hashlib.sha512(msg).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    method_request = MethodRequest(request["body"])
    errors = method_request.validate()
    if errors:
        return errors, INVALID_REQUEST
    if not check_auth(method_request):
        return ERRORS[FORBIDDEN], FORBIDDEN
    if method_request.method == "online_score":
        return OnlineScoreRequest(method_request.arguments).handle(ctx, store, method_request.is_admin)
    elif method_request.method == "clients_interests":
        return ClientsInterestsRequest(method_request.arguments).handle(ctx, store)
    else:
        return ERRORS[NOT_FOUND], NOT_FOUND


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return

if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
