import unittest
import functools
import socket
import io
import os.path

import httpd


def cases(cases):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args):
            for case in cases:
                new_args = args + (case if isinstance(case, tuple) else (case,))
                func(*new_args)
        return wrapper
    return decorator


class TestHTTPRequest(unittest.TestCase):
    def test_request_ok(self):
        test_request = b"GET /path HTTP/1.0\r\nHost: www.host.com\r\nManyColons: 00:00:00\r\n"
        rfile = io.BytesIO(test_request)
        request = httpd.HTTPRequest(httpd.IMPLEMENTED_METHODS, rfile)
        request.parse()
        self.assertEqual(request.request_line, "GET /path HTTP/1.0")
        self.assertEqual(request.get_header("Host"), "www.host.com")
        self.assertEqual(request.get_header("ManyColons"), "00:00:00")


    def test_request_start_line_empty(self):
        test_request = b""
        rfile = io.BytesIO(test_request)
        request = httpd.HTTPRequest(httpd.IMPLEMENTED_METHODS, rfile)
        self.assertRaises(EOFError, request.parse)

    @cases([
        (b"GET / \r\n", (httpd.BAD_REQUEST, "Invalid starting line")),
        (b"Bad_Method / HTTP/1.1\r\n", (httpd.METHOD_NOT_ALLOWED, 'Method Not Allowed')),
        (b"GET / BAD_PROTOCOL\r\n", (httpd.BAD_REQUEST, "Invalid HTTP version"))
    ])
    def test_request_bad_start_line(self, line, answer):
        rfile = io.BytesIO(line)
        request = httpd.HTTPRequest(httpd.IMPLEMENTED_METHODS, rfile)
        with self.assertRaises(ValueError) as cm:
            request.parse()
        self.assertTupleEqual(cm.exception.args, answer)


    @cases([
        (b"GET / HTTP/1.0\r\n  \r\n", ""),
        (b"GET / HTTP/1.0\r\nname\r\n", "name"),
        (b"GET / HTTP/1.0\r\n :value1\r\n", " :value1"),
        (b"GET / HTTP/1.0\r\n:\r\n", ":")
    ])
    def test_parse_headers_bad(self, header, answer):
        rfile = io.BytesIO(header)
        request = httpd.HTTPRequest(httpd.IMPLEMENTED_METHODS, rfile)
        with self.assertRaises(ValueError) as cm:
            request.parse()
        self.assertTupleEqual(cm.exception.args, (httpd.BAD_REQUEST, "Invalid header: %s" % answer))


class TestHTTPResponse(unittest.TestCase):
    def test_response_ok(self):
        response_file = open("tests/responce", "wb")
        self.response = httpd.HTTPresponse(response_file)
        self.response.http_version = "HTTP/1.1"
        self.response.status = 200
        self.response.add_header("Header", "Good")
        self.response.body_path = "./tests/index.html"
        self.response.send()
        response_file.close()

        self.assertEqual(self.response.status_line, "HTTP/1.1 200 OK")
        self.assertEqual(self.response.get_header("Header"), "Good")
        self.assertEqual(self.response.get_header("Content-Length"), 19)
        self.assertEqual(self.response.get_header("Content-Type"), "text/html")
        self.assertEqual(self.response.get_header("Server"), httpd.SERVER_NAME)

    def test_response_empty(self):
        self.wfile = io.BytesIO(b" ")
        self.response = httpd.HTTPresponse(self.wfile)
        self.assertFalse(self.response.send())


class TestHTTPHandler(unittest.TestCase):
    def setUp(self):
        self.address = ("", 8080)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handler = httpd.HTTPHandler(self.socket, self.address, "/tests")

    def tearDown(self):
        self.handler.close()
        self.socket.close()

    def test_parse_url_ok(self):
        path, query = self.handler.parse_url("/test/path?n1=v1&n2=v2&n1=v3")
        self.assertEqual(path, "/test/path")
        self.assertDictEqual(query, {"n1": ["v1", "v3"], "n2": ["v2"]})


class TestFunctions(unittest.TestCase):
    @cases([
        (r"/root", r"dir/file.txt"),
        (r"/root/", r"/dir/file.txt"),
        (r"/root", r"///dir///file.txt"),
        (r"/root", r"\\\dir\\\file.txt"),
        (r"/root", r"\/\dir\/\file.txt")
    ])
    def test_get_real_path(self, root, rel_path):
        correct = os.sep + "root" + os.sep + "dir" + os.sep + "file.txt"
        self.assertEqual(httpd.get_real_path(root, rel_path), correct)

    @cases([
        ("/path.txt", "text/plain"),
        ("/path.ext", "application/octet-stream"),
        ("/path", "application/octet-stream")
    ])
    def test_get_mime_type(self, ext, answer):
        self.assertEqual(httpd.get_mime_type(ext), answer)


if __name__ == "__main__":
    unittest.main()