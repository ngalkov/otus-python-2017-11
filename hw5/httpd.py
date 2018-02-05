#!/usr/bin/env python
# -*- coding: utf-8 -*-


import socket
import sys
import os.path
import argparse
import logging
import re
import datetime
import urllib.parse
import shutil
from threading import Thread
from queue import Queue

from http_status_code import *
from mime_type import *

SERVER_NAME = "VS_Server/0.1"
IMPLEMENTED_METHODS = ["GET", "HEAD"]
# HOST = ""
# PORT = 8080
TIMEOUT = 100

LOGGING = None  # path to log file


class HTTPRequest(object):
    """Parse HTTP request from file-like object"""
    def __init__(self, implemented_methods, rfile):
        self.rfile = rfile
        self.implemented_methods = implemented_methods
        self.method = ""
        self.url = ""
        self.http_version = ""
        self.headers = {}
        self.body = None

    def parse(self):
        # parse starting line
        request_line = str(self.rfile.readline(), "ascii")
        if not request_line:  # client has closed the connection (0 bytes received)
            raise EOFError
        words = request_line.split()
        if len(words) != 3:
            raise ValueError(BAD_REQUEST, "Invalid starting line")
        method, url, http_version = words
        if method not in self.implemented_methods:
            raise ValueError(METHOD_NOT_ALLOWED, ERRORS[METHOD_NOT_ALLOWED])
        if not re.search(r"^HTTP/1\.\d+$", http_version):
            raise ValueError(BAD_REQUEST, "Invalid HTTP version")
        self.method, self.url, self.http_version = words

        # parse headers
        while True:
            line = str(self.rfile.readline(), "iso-8859-1")
            if line in ("\r\n", "\n", ""):
                break
            name = value = ""
            if ":" in line:
                name, value = map(str.strip, line.split(sep=":", maxsplit=1))
            if not name:
                raise ValueError(BAD_REQUEST, "Invalid header: %s" % line.rstrip())
            self.headers[name] = value

    def get_header(self, name):
        return self.headers.get(name, None)

    @property
    def request_line(self):
        return "%s %s %s" % (self.method, self.url, self.http_version)


class HTTPresponse(object):
    """Build HTTP response and send to file-like object"""
    def __init__(self, wfile):
        self.wfile = wfile
        self.http_version = ""
        self.status = 0
        self.reason = ""
        self.headers = {}
        self.body_path = None
        self.head_only = False

    def get_header(self, name):
        return self.headers.get(name, None)

    def add_header(self, name, value):
        self.headers[name] = value

    def send(self, closing=False):
        """Send response. Return True if the data was sent and False otherwise"""
        if not self.http_version and not self.status:
            return
        buffer = ""
        # send status_line
        if not self.reason:
            if self.status == OK:
                self.reason = "OK"
            elif self.status in ERRORS:
                self.reason = ERRORS[self.status]
        buffer += "%s %s %s\r\n" % (self.http_version, self.status, self.reason)

        # send headers
        self.add_header("Server", SERVER_NAME)
        self.add_header("Date", datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"))
        if self.body_path is not None:
            self.add_header("Content-Length", os.path.getsize(self.body_path))
            self.add_header("Content-Type", get_mime_type(self.body_path))
        else:
            self.add_header("Content-Length", "0")
        if closing:
            self.add_header("Connection", "close")
        else:
            self.add_header("Connection", "keep-alive")
        for key, value in self.headers.items():
            header = "%s: %s\r\n" % (key, value)
            buffer += header

        self.wfile.write(buffer.encode("iso-8859-1"))
        self.wfile.write(b"\r\n")

        # send body
        if not self.head_only:
            with open(self.body_path, "rb") as body_file:
                shutil.copyfileobj(body_file, self.wfile)

        self.wfile.flush()

    @property
    def status_line(self):
        return "%s %s %s" % (self.http_version, self.status, self.reason)


class HTTPHandler(object):
    """Receive and parse HTTP requests from client_socket, prepare and send response."""
    def __init__(self, client_socket, address, doc_root):
        self.client_socket = client_socket
        self.address = address
        client_socket.settimeout(TIMEOUT)
        self.doc_root = doc_root
        self.rfile = self.client_socket.makefile("rb")
        self.wfile = self.client_socket.makefile("wb")
        self.close_connection = False

    def handle(self):
        """Entry point. Start handling HTTP requests from client socket"""
        while not self.close_connection:
            try:
                self.handle_one_request()
            except:
                logging.exception("%s:%s - Unexpected exception: " % self.address)
                self.close_connection = True
        self.close()

    def handle_one_request(self):
        self.close_connection = True
        # parse request

        self.request = HTTPRequest(IMPLEMENTED_METHODS, self.rfile)
        if not self.parse_request():
            # If error happened, error code had been sent, just exit
            return

        # determine whether the connection should be closed or kept alive
        if self.request.http_version == "HTTP/1.1":
            self.close_connection = False
        conntype = self.request.headers.get("Connection", "")
        if conntype.lower() == "close":
            self.close_connection = True
        elif conntype.lower() == "keep-alive":
            self.close_connection = False

        # prepare response to send
        prepare_resp_method = getattr(self, "process_" + self.request.method)
        try:
            prepare_resp_method()
        except ValueError as e:
            self.send_error(e.args[0], e.args[1])
            return

        # actually send response
        self.send_response()

    def parse_request(self):
        try:
            self.request.parse()
            logging.debug("%s:%s - Received request: " % self.address + '"%s"' % self.request.request_line)
        except EOFError:
            logging.debug("%s:%s - Client has closed the connection" % self.address)
            return False
        except ValueError as e:
            self.send_error(e.args[0], e.args[1])
            return False
        except socket.timeout:
            logging.debug("%s:%s - Request timed out" % self.address)
            return False
        return True

    def process_GET(self):
        """Prepare a response to GET method"""
        # parse URI
        path, query = self.parse_url(self.request.url)
        path = get_real_path(self.doc_root, path)

        # test path
        if os.path.commonpath([self.doc_root, path]) != self.doc_root:
            raise ValueError(FORBIDDEN, ERRORS[FORBIDDEN])
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
            if not os.path.isfile(path):
                raise ValueError(FORBIDDEN, ERRORS[FORBIDDEN])
        elif not os.path.isfile(path):
            raise ValueError(NOT_FOUND, ERRORS[NOT_FOUND])
        elif not os.access(path, os.R_OK):
            raise ValueError(FORBIDDEN, ERRORS[FORBIDDEN])

        # create response
        self.response = HTTPresponse(self.wfile)
        self.response.http_version = self.request.http_version  or "HTTP/1.0"
        self.response.status = OK
        self.response.body_path = path
        self.response.head_only = False

    def process_HEAD(self):
        """Prepare a response to HEAD method"""
        self.process_GET()
        self.response.head_only = True

    def process_error(self, code, msg=None):
        """Prepare a response to an error"""
        self.response = HTTPresponse(self.wfile)
        self.response.http_version = self.request.http_version or "HTTP/1.0"
        self.response.status = code
        if msg:
            self.response.reason = msg
        self.response.head_only = True

    def send_response(self):
        """Send and log prepared response"""
        try:
            self.response.send()
            logging.debug("%s:%s - Send response: " % self.address + '"%s"' % self.response.status_line)
        except socket.timeout:
            logging.debug("%s:%s - Attempt to send response - timed out" % self.address)
            self.close_connection = True
            return
        except OSError:
            self.send_error(INTERNAL_ERROR, ERRORS[INTERNAL_ERROR])
            self.close_connection = True
            return

    def send_error(self, code, msg=None):
        """Send and log error"""
        self.process_error(code, msg)
        self.send_response()

    def parse_url(self, url):
        """Extract path and query from generic URI"""
        parsed_url = urllib.parse.urlparse(url)
        path = urllib.parse.unquote_plus(parsed_url.path)
        query = urllib.parse.parse_qs(parsed_url.query)
        return path, query

    def close(self):
        """Close handler"""
        if not self.wfile.closed:
            try:
                self.wfile.flush()
            except socket.timeout:
                pass
        self.wfile.close()
        self.rfile.close()


class Worker(object):
    """Processes TCP stream"""
    def __init__(self, clients):
        self.clients = clients

    def get_client_socket(self):
        self.client_socket, self.address, self.doc_root = self.clients.get()
        self.handler = HTTPHandler(self.client_socket, self.address, self.doc_root)

    def run(self):
        while True:
            self.get_client_socket()
            try:
                self.handler.handle()
            finally:
                self.close()

    def close(self):
        self.handler.close()
        if self.client_socket:
            self.client_socket.close()
        logging.debug("%s:%s - Close connection" % self.address)


class Server(object):
    def __init__(self, address, workers_count, doc_root):
        self.address = address
        self.workers_count = workers_count
        self.doc_root = doc_root
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = Queue()
        for n in range(self.workers_count):
            worker = Worker(self.clients)
            t = Thread(target=worker.run)
            t.daemon = True
            t.start()
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(self.address)
            self.socket.listen()
        except:
            self.close()
            raise

    def serve_forever(self):
        while True:
            try:
                client_socket, address = self.socket.accept()
                logging.debug("%s:%s - Accept connection" % address)
                self.clients.put((client_socket, address, self.doc_root))
            except OSError:
                logging.exception("Error accepting connection:")

    def close(self):
        self.socket.close()


def get_mime_type(path):
    ext = os.path.splitext(path)[1]
    return MIME_TYPE.get(ext, "application/octet-stream")


def get_real_path(root, relative_path):
    """Return normalized absolutized version of the path relative to the root"""
    no_leading_slashes = re.search(r"^[/\\]*(.*)$", relative_path)
    relative_path = no_leading_slashes.group(1)
    return os.path.normpath(os.path.join(root, relative_path))


if __name__ == "__main__":
    # Initialization
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", help="address", default="localhost", dest="address")
    parser.add_argument("-p", help="port", type=int, default=8080, dest="port")
    parser.add_argument("-w", help="number of workers", type=int, default=10, dest="workers_count")
    parser.add_argument("-r", help="path to document root directory", dest="doc_root")
    args = parser.parse_args()
    doc_root = os.path.realpath(args.doc_root)
    if not os.path.isdir(doc_root):
        print("Unable to find document root directory")
        sys.exit()
    logging.basicConfig(filename=LOGGING, level=logging.INFO,
                        format="[%(asctime)s] %(levelname).1s %(message)s", datefmt="%Y.%m.%d %H:%M:%S")
    server = Server((args.address, args.port), args.workers_count, doc_root)
    logging.info("Starting server at %s:%s" % (args.address, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.close()
