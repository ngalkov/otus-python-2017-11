import unittest
from unittest.mock import patch

from api import *


class TestFieldObjects(unittest.TestCase):
    def test_FieldClass(self):
        req = Field(required=True)
        self.assertEqual(req.validate("something"), "")
        self.assertEqual(req.validate(None), "Field is required")

        notnull = Field(nullable=False)
        self.assertEqual(notnull.validate("something"), "")
        self.assertEqual(notnull.validate(""), "Field can't be empty")

    def test_CharFieldClass(self):
        # test if super().validate() called
        self.assertEqual(CharField(required=True).validate(None),"Field is required")
        # test string validation
        self.assertEqual(CharField().validate("some string"), "")
        self.assertEqual(CharField().validate(0), "Field must be a string")

    def test_ArgumentsFieldClass(self):
        # test if super().validate() called
        self.assertEqual(ArgumentsField(required=True).validate(None), "Field is required")
        # test dict validation
        self.assertEqual(ArgumentsField().validate({"A": 1, "B": 2}), "")
        self.assertEqual(ArgumentsField().validate(0), "Field must be a dict")

    def test_PhoneFieldClass(self):
        # test if super().validate() called
        self.assertEqual(PhoneField(required=True).validate(None), "Field is required")
        # test phone number validation
        self.assertEqual(PhoneField().validate(72345678901), "")
        self.assertEqual(PhoneField().validate("72345678901"), "")
        for f in [7234567890,       # < 11 digits
                  723456789012,     # > 11 digits
                  12345678901,      # not starting with 7
                  "7a345678901"     # has non-digit
                  ]:
            self.assertEqual(PhoneField().validate(f), "Field must be a valid phone")

    def test_EmailFieldClass(self):
        # test if super().validate() called
        self.assertEqual(EmailField().validate(123), "Field must be a string")
        # test email validation
        self.assertEqual(EmailField().validate("mail@mail.com"), "")
        self.assertEqual(EmailField().validate("bad_email"), "Field must be a valid email")

    def test_DateFieldClass(self):
        # test if super().validate() called
        self.assertEqual(DateField().validate(123), "Field must be a string")
        # test date validation
        self.assertEqual(DateField().validate("31.12.2000"), "")
        for d in ["32.12.2000", "31.13.2000", "31.12.00", ""]:
            self.assertEqual(DateField().validate(d), "Date must have format: DD.MM.YYYY")

    def test_BirthDayFieldClass(self):
        # test if super().validate() called
        self.assertEqual(BirthDayField().validate(""), "Date must have format: DD.MM.YYYY")
        # test birthday validation
        self.assertEqual(BirthDayField().validate("31.12.2000"), "")
        self.assertEqual(BirthDayField().validate("01.01.1900"), "Birthday must be not more than 70 years from now")

    def test_GenderFieldClass(self):
        # test if super().validate() called
        self.assertEqual(GenderField(required=True).validate(None), "Field is required")
        # test gender validation
        for g in GENDERS:
            self.assertEqual(GenderField().validate(g), "")
        self.assertEqual(GenderField().validate(""), "Gender must be a number %s, %s, %s" % (UNKNOWN, MALE, FEMALE))

    def test_ClientIDsFieldClass(self):
        # test if super().validate() called
        self.assertEqual(ClientIDsField(required=True).validate(None), "Field is required")
        # test client_ids validation
        self.assertEqual(ClientIDsField().validate([1,2,3]), "")
        for client_id in [1, [1, 2, "A"]]:
            self.assertEqual(ClientIDsField().validate(client_id), "Field must be a list of integer")


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
        # valid request
        self.assertDictEqual(MethodRequest({"login": "", "method": "", "token": "", "arguments": {}}).validate(),
                             {"method": "Field can't be empty"})
        # invalid request - has invalid field
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
        online_score_request = OnlineScoreRequest({"first_name": "Fname", "last_name": "Lname", "birthday": "01.01.1900"})
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
        self.ctx = {}
        self.store = None
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
        self.ctx = {}
        self.store = None
        self.request = {"login": "",
                        "method": "",
                        "token": "",
                        "arguments": {"client_ids": [1,2,3,4], "date": "01.01.2000"}
                        }

    def test_valid(self):
        method_request = MethodRequest(self.request)
        response, code = ClientsInterestsRequest(method_request.arguments).handle(self.ctx, self.store)
        self.assertEqual(code, OK)
        self.assertEqual(self.ctx["nclients"], 4)
        for cid, interests in response.items():
            self.assertIsInstance(interests, list)
            self.assertEqual(len(interests), 2)

    def test_validation_error(self):
        self.request["arguments"] = {"client_ids": [1,2,3,4], "date": "99.99.1900"}
        method_request = MethodRequest(self.request)
        response = ClientsInterestsRequest(method_request.arguments).handle(self.ctx, self.store)
        self.assertTupleEqual(response, ({"date": "Date must have format: DD.MM.YYYY"}, INVALID_REQUEST))


class TestMethodHandler(unittest.TestCase):
    def setUp(self):
        self.ctx = {}
        self.store = None
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