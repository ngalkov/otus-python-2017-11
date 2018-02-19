##############
# Unit tests #
##############

import time
import unittest
from unittest.mock import patch
import functools

from api import *
from mock_redis import MockRedis
from store import Store


def cases(cases):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args):
            for case in cases:
                new_args = args + (case if isinstance(case, tuple) else (case,))
                func(*new_args)
        return wrapper
    return decorator


class TestStore(unittest.TestCase):
    def test_db_initialization_error(self):
        store = Store(None, None)
        self.assertRaises(OSError, store.set, "ключ", "значение")
        self.assertRaises(OSError, store.get, "ключ")

    def test_db_ok(self):
        mock_db = MockRedis()
        store = Store(mock_db, mock_db)
        store.set("ключ", "значение")
        self.assertEqual(store.get("ключ"), "значение")
        self.assertIsNone(store.get("неверный ключ"))

    def test_db_error(self):
        mock_db = MockRedis(error=True)
        store = Store(mock_db, mock_db)
        self.assertRaises(OSError, store.set, "ключ", "значение")
        self.assertRaises(OSError, store.get, "ключ")

    def test_db__cache_initialization_error(self):
        store = Store(None, None)
        self.assertIsNone(store.cache_set("ключ", "значение", 1))
        self.assertIsNone(store.cache_get("ключ"))

    def test_db_cache_ok(self):
        mock_db = MockRedis()
        store = Store(mock_db, mock_db)
        store.cache_set("ключ", "значение", 1)
        self.assertEqual(store.cache_get("ключ"), "значение")
        time.sleep(1)
        self.assertIsNone(store.get("ключ"))
        self.assertIsNone(store.get("неверный ключ"))

    def test_db_cache_error(self):
        mock_db = MockRedis(error=True)
        store = Store(mock_db, mock_db)
        self.assertIsNone(store.cache_set("ключ", "значение", 1))
        self.assertIsNone(store.cache_get("ключ"))


class TestFieldObjects(unittest.TestCase):
    def test_Field_required(self):
        not_req = Field(required=False)
        self.assertEqual(not_req.validate(None), "")
        req = Field(required=True)
        self.assertEqual(req.validate("something"), "")
        self.assertEqual(req.validate(None), "Field is required")

    def test_Field_nullable(self):
        notnull = Field(nullable=False)
        self.assertEqual(notnull.validate("something"), "")
        self.assertEqual(notnull.validate(""), "Field can't be empty")
        null = Field(nullable=True)
        self.assertEqual(null.validate(""), "")

    def test_CharField_validation_super_called(self):
        self.assertEqual(CharField(required=True).validate(None), "Field is required")

    @cases([
        ["some string", ""],
        [0, "Field must be a string"],
    ])
    def test_CharField_validation(self, case):
        self.assertEqual(CharField().validate(case[0]), case[1])

    def test_ArgumentsField_validation_super_called(self):
        self.assertEqual(ArgumentsField(required=True).validate(None), "Field is required")

    @cases([
        [{"A": 1, "B": 2}, ""],
        [0, "Field must be a dict"],
    ])
    def test_ArgumentsField_validation(self, case):
        self.assertEqual(ArgumentsField().validate(case[0]), case[1])

    def test_PhoneField_validation_super_called(self):
        self.assertEqual(PhoneField(required=True).validate(None), "Field is required")

    @cases([
        [72345678901, ""],
        ["72345678901", ""],
        [7234567890, "Field must be a valid phone"],  # < 11 digits
        [723456789012, "Field must be a valid phone"],  # > 11 digits
        [12345678901, "Field must be a valid phone"],  # not starting with 7
        ["7a345678901", "Field must be a valid phone"]  # has non-digit
    ])
    def test_PhoneField_validation(self, case):
        self.assertEqual(PhoneField().validate(case[0]), case[1])

    def test_EmailFieldClass_validation_super_called(self):
        self.assertEqual(EmailField().validate(123), "Field must be a string")

    @cases([
        ["mail@mail.com", ""],
        ["bad_email", "Field must be a valid email"],
    ])
    def test_EmailFieldClass_validation(self, case):
        self.assertEqual(EmailField().validate(case[0]), case[1])

    def test_DateFieldClass_validation_super_called(self):
        self.assertEqual(DateField().validate(123), "Field must be a string")

    @cases([
        ["31.12.2000", ""],
        ["32.12.2000", "Date must have format: DD.MM.YYYY"],
        ["31.13.2000", "Date must have format: DD.MM.YYYY"],
        ["31.12.00", "Date must have format: DD.MM.YYYY"],
        ["", "Date must have format: DD.MM.YYYY"],
    ])
    def test_DateFieldClass_validation(self, case):
        self.assertEqual(DateField().validate(case[0]), case[1])

    def test_BirthDayFieldClass_validation_super_called(self):
        self.assertEqual(BirthDayField().validate(""), "Date must have format: DD.MM.YYYY")

    @cases([
        ["31.12.2000", ""],
        ["01.01.1900", "Birthday must be not more than 70 years from now"],
    ])
    def test_BirthDayFieldClass_validation(self, case):
        self.assertEqual(BirthDayField().validate(case[0]), case[1])

    def test_GenderFieldClass_validation_super_called(self):
        self.assertEqual(GenderField(required=True).validate(None), "Field is required")

    @cases([
        ["0", ""], ["1", ""], ["2", ""],
        ["", "Gender must be a number 0, 1, 2"],
        ["A", "Gender must be a number 0, 1, 2"],
        ["3", "Gender must be a number 0, 1, 2"],
    ])
    def test_GenderFieldClass_validation(self, case):
        self.assertEqual(GenderField().validate(case[0]), case[1])

    def test_ClientIDsFieldClass_validation_super_called(self):
        self.assertEqual(ClientIDsField(required=True).validate(None), "Field is required")

    @cases([
        [[1, 2, 3], ""],
        [1, "Field must be a list of integer"],
        [[1, 2, "A"], "Field must be a list of integer"],
    ])
    def test_ClientIDsFieldClass_validation(self, case):
        self.assertEqual(ClientIDsField().validate(case[0]), case[1])


class TestRequestObjects(unittest.TestCase):
    def test_request_creation(self):
        # test whether MetaRequest gather all Field attributes declared in class definition into new "schema" attribute
        class TestRequest(Request):
            f1 = CharField(required=False, nullable=True)
            f2 = DateField(required=False, nullable=True)
        test_request = TestRequest({"f1": "test_f1"})
        self.assertIsInstance(test_request.schema["f1"], CharField)
        self.assertIsInstance(test_request.schema["f2"], DateField)
        self.assertEqual(test_request.f1, "test_f1")
        self.assertIsNone(test_request.f2)

    def test_request_validation(self):
        # make testing classes
        class ValidRequestTest(Request):
            req = CharField(required=True, nullable=True)
            not_req = CharField(required=False, nullable=True)
            nullable = CharField(required=False, nullable=True)
            not_nullable = CharField(required=False, nullable=False)

        class BadRequestTest(Request):
            req_err = CharField(required=True, nullable=True)
            nullable_err = CharField(required=True, nullable=False)
            field_err = DateField(required=True, nullable=False)

        self.assertDictEqual(ValidRequestTest({"req": "ABC", "nullable": "", "not_nullable": "ABC"}).validate(),
                             {})
        self.assertDictEqual(BadRequestTest({"nullable_err": "", "field_err": "99.99.9999"}).validate(),
                             {"req_err": "Field is required",
                              "nullable_err": "Field can't be empty",
                              "field_err": "Date must have format: DD.MM.YYYY"})

    def test_MethodRequestClass(self):
        # invalid request - has invalid field
        self.assertDictEqual(MethodRequest({"login": "", "method": "", "token": "", "arguments": {}}).validate(),
                             {"method": "Field can't be empty"})
        # valid request
        self.assertDictEqual(MethodRequest({"login": "", "method": "method", "token": "", "arguments": {}}).validate(),
                             {})
        # test is_admin
        self.assertTrue(MethodRequest({"login": ADMIN_LOGIN}).is_admin)
        self.assertFalse(MethodRequest({"login": "other user"}).is_admin)

    def test_OnlineScoreRequestClass(self):
        # valid request
        online_score_request = OnlineScoreRequest({"first_name": "Fname", "last_name": "Lname", "email": ""})
        self.assertListEqual(sorted(online_score_request.non_empty_field()), ["first_name", "last_name"])
        self.assertFalse("online_score" in online_score_request.validate())

        # invalid request - has invalid field
        online_score_request = OnlineScoreRequest(
            {"first_name": "Fname", "last_name": "Lname", "birthday": "01.01.1900"})
        self.assertTrue(online_score_request.validate()["birthday"],
                        "Birthday must be not more than 70 years from now")

        # invalid request - all non-empty pairs are empty
        online_score_request = OnlineScoreRequest({"phone": "", "email":  "",
                                                   "first name": "", "last name": "",
                                                   "gender": "", "birthday": ""})
        self.assertTrue(online_score_request.validate()["online_score"],
                        "At least one pair phone‑email, first name‑last name, gender‑birthday must not be empty")


class TestOnlineScoreHandler(unittest.TestCase):
    def setUp(self):
        mock_db = MockRedis()
        self.ctx = {}
        self.store = Store(mock_db, mock_db)
        self.request = {"login": "",
                        "method": "",
                        "token": "",
                        "arguments": {"first_name": "Fname", "last_name": "Lname"}
                        }

    def test_valid(self):
        method_request = MethodRequest(self.request)
        response = OnlineScoreRequest(method_request.arguments).handle(self.ctx, self.store, method_request.is_admin)
        self.assertTupleEqual(response, ({"score": 0.5}, OK))
        self.assertListEqual(sorted(self.ctx["has"]), ["first_name", "last_name"])

    def test_is_admin(self):
        self.request["login"] = ADMIN_LOGIN
        method_request = MethodRequest(self.request)
        response = OnlineScoreRequest(method_request.arguments).handle(self.ctx, self.store, method_request.is_admin)
        self.assertTupleEqual(response, ({"score": 42}, OK))

    def test_validation_error(self):
        self.request["arguments"] = {"first_name": 666, "last_name": "Lname"}
        method_request = MethodRequest(self.request)
        response = OnlineScoreRequest(method_request.arguments).handle(self.ctx, self.store, method_request.is_admin)
        self.assertTupleEqual(response, ({"first_name": "Field must be a string"}, INVALID_REQUEST))


class TestClientsInterestsHandler(unittest.TestCase):
    def setUp(self):
        mock_db = MockRedis()
        self.ctx = {}
        self.store = Store(mock_db, mock_db)
        self.request = {"login": "",
                        "method": "",
                        "token": "",
                        "arguments": {"client_ids": [1, 2, 3, 4], "date": "01.01.2000"}
                        }

    def test_valid(self):
        method_request = MethodRequest(self.request)
        response, code = ClientsInterestsRequest(method_request.arguments).handle(self.ctx, self.store)
        self.assertEqual(code, OK)
        self.assertEqual(self.ctx["nclients"], 4)
        for cid, interests in response.items():
            self.assertIsInstance(interests, list)

    def test_validation_error(self):
        self.request["arguments"] = {"client_ids": [1, 2, 3, 4], "date": "99.99.1900"}
        method_request = MethodRequest(self.request)
        response = ClientsInterestsRequest(method_request.arguments).handle(self.ctx, self.store)
        self.assertTupleEqual(response, ({"date": "Date must have format: DD.MM.YYYY"}, INVALID_REQUEST))


class TestMethodHandler(unittest.TestCase):
    def setUp(self):
        mock_db = MockRedis()
        self.ctx = {}
        self.store = Store(mock_db, mock_db)
        self.request = {"body":
                            {"login": "",
                             "method": "",
                             "token": "",
                             "arguments": {}
                             }
                        }

    def test_validation_error(self):
        response = method_handler(self.request, self.ctx, self.store)
        self.assertTupleEqual(response, ({"method": "Field can't be empty"}, INVALID_REQUEST))

    @patch("api.check_auth")
    def test_check_auth_called(self, mock_auth):
        self.request["body"]["method"] = "online_score"
        method_handler(self.request, self.ctx, self.store)
        assert mock_auth.called

    @patch("api.check_auth", return_value=True)
    @patch("api.OnlineScoreRequest.handle")
    def test_online_score_handler_called(self, mock_method, mock_auth):
        self.request["body"]["method"] = "online_score"
        method_handler(self.request, self.ctx, self.store)
        assert mock_method.called

    @patch("api.check_auth", return_value=True)
    @patch("api.ClientsInterestsRequest.handle")
    def test_clients_interests_handler_called(self, mock_method, mock_auth):
        self.request["body"]["method"] = "clients_interests"
        method_handler(self.request, self.ctx, self.store)
        assert mock_method.called


if __name__ == "__main__":
    unittest.main()