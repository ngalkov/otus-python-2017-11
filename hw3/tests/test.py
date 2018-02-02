####################
# Functional tests #
####################

import unittest
from unittest.mock import patch
import functools
import datetime
import hashlib

import api
import store
import mock_redis


def cases(cases):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args):
            for case in cases:
                new_args = args + (case if isinstance(case, tuple) else (case,))
                func(*new_args)
        return wrapper
    return decorator


class TestSuite(unittest.TestCase):
    def setUp(self):
        self.context = {}
        self.headers = {}
        mock_db = mock_redis.MockRedis()
        self.store = store.Store(mock_db, mock_db)

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    def test_empty_request(self):
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)

    def test_auth_ok(self):
        request = {"login": "", "method": "online_score", "token": "", "arguments": {}}
        # test admin login
        admin_msg = (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode()
        admin_digest = hashlib.sha512(admin_msg).hexdigest()
        request["login"] = "admin"
        request["token"] = admin_digest
        _, code = self.get_response(request)
        self.assertNotEqual(api.FORBIDDEN, code)
        # test user login
        user_msg = ("user1" + api.SALT).encode()
        user_digest = hashlib.sha512(user_msg).hexdigest()
        request["login"] = "user1"
        request["token"] = user_digest
        _, code = self.get_response(request)
        self.assertNotEqual(api.FORBIDDEN, code)

    # test authentication failed
    @cases([
        {"login": "", "method": "online_score", "token": "bad token", "arguments": {}},
        {"login": "user1", "method": "online_score", "token": "bad token", "arguments": {}},
        {"login": "admin", "method": "online_score", "token": "bad token", "arguments": {}}
    ])
    def test_auth_fail(self, request):
        _, code = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, code)

    # test whether valid request accepted
    @patch("api.check_auth", return_value=True)
    def test_request_validation_ok(self, mock_auth):
        request = {"account": "", "login": "", "method": "clients_interests", "token": "",
                   "arguments": {"client_ids": [1, 2, 3]}}
        _, code = self.get_response(request)
        self.assertEqual(api.OK, code)

    # test whether invalid request rejected
    @patch("api.check_auth", return_value=True)
    @cases([
        {"account": "", "login": "", "method": "", "token": "", "arguments": {"client_ids": [1, 2, 3]}},  # empty method
        {"account": "", "method": "online_score", "token": "", "arguments": {"client_ids": [1, 2, 3]}},  # no login
        {"account": "", "login": "", "method": "online_score", "arguments": {"client_ids": [1, 2, 3]}},  # no token
        {"account": "", "login": "", "method": "online_score", "token": "", },  # no arguments
        {"account": "", "login": "", "token": "", "arguments": {"client_ids": [1, 2, 3]}}  # no method
    ])
    def test_request_validation_error(self, mock_auth, request):
        _, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)

    # test whether valid arguments accepted
    @patch("api.check_auth", return_value=True)
    @cases([
        {"login": "", "method": "online_score", "token": "",
                "arguments": {"phone": 72345678901, "email": "mail@mail.com"}},
        {"login": "", "method": "online_score", "token": "",
                "arguments": {"first_name": "Fname", "last_name": "Lname"}},
        {"login": "", "method": "online_score", "token": "",
                "arguments": {"gender": 1, "birthday": "31.12.2000"}},
        {"login": "", "method": "clients_interests", "token": "",
                "arguments": {"client_ids": [1, 2, 3], "date": "31.12.2000"}}
    ])
    def test_arguments_ok(self, mock_auth, request):
        _, code = self.get_response(request)
        self.assertEqual(api.OK, code)

    # test whether invalid arguments rejected
    @patch("api.check_auth", return_value=True)
    @cases([
        {"login": "", "method": "online_score", "token": "", "arguments": {}},  # empty arguments
        {"login": "", "method": "online_score", "token": "",
            "arguments": {"phone": 72345678901, "first_name": "Fname", "gender": 1}},  # no valid pair
        {"login": "", "method": "clients_interests", "token": "",
         "arguments": {"client_ids": "bad_client_ids"}}  #  bad client_ids
    ])
    def test_argument_fail(self, mock_auth, request):
        _, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)

    # test whether return values correct
    @patch("api.check_auth", return_value=True)
    def test_return_value(self, mock_auth):
        request = {"login": "", "method": "online_score", "token": "",
                "arguments": {"phone": 72345678901, "email": "mail@mail.com"}}
        response, code = self.get_response(request)
        self.assertEqual(response["score"], 3,0)
        request = {"login": "", "method": "clients_interests", "token": "",
                "arguments": {"client_ids": [1, 2, 3]}}
        response, code = self.get_response(request)
        self.assertDictEqual(response, {"1": [], "2": [], "3": []})


if __name__ == "__main__":
    unittest.main()
